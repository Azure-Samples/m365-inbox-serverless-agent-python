"""Offline regression coverage for the client-side, read-only MCP path."""

import io
import json
import os
import sys
import unittest
from contextlib import redirect_stdout
from copy import deepcopy
from types import ModuleType, SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import chat


class ReadInboxLiveTests(unittest.TestCase):
    def setUp(self):
        self.tool = MagicMock(spec=["__aenter__", "__aexit__", "functions", "call_tool"])
        self.tool.__aenter__ = AsyncMock(return_value=self.tool)
        self.tool.__aexit__ = AsyncMock(return_value=False)
        self.tool.functions = [SimpleNamespace(name=chat.ALLOWED_READ_OP)]
        self.tool.call_tool = AsyncMock(return_value=[SimpleNamespace(text='{"value": []}')])
        self.build_tool = Mock(return_value=(self.tool, None))

        env_module = ModuleType("azure_functions_agents.config.env")
        self.resolve_config = Mock(side_effect=lambda data: data)
        env_module.resolve_env_vars_in_data = self.resolve_config
        mcp_module = ModuleType("azure_functions_agents.discovery.mcp")
        mcp_module._build_mcp_tool = self.build_tool
        self.enterContext(
            patch.dict(
                sys.modules,
                {
                    "azure_functions_agents.config.env": env_module,
                    "azure_functions_agents.discovery.mcp": mcp_module,
                },
            )
        )
        self.enterContext(patch.dict(os.environ, {}, clear=True))
        self.enterContext(patch.object(chat, "_read_local_settings", return_value={}))
        self.config = {
            "servers": {
                "outlook": {
                    "type": "http",
                    "url": "https://outlook.example.invalid/mcp",
                    "auth": {"scope": "https://apihub.azure.com/.default"},
                    "tools": ["*", "office365_SendEmailV2"],
                },
                "teams": {"type": "http", "url": "https://teams.example.invalid/mcp"},
            }
        }
        self.original_config = deepcopy(self.config)
        self.config_path = Mock()
        self.config_path.read_text.return_value = json.dumps(self.config)
        self.enterContext(patch.object(chat, "MCP_JSON_PATH", self.config_path))
        self.network_calls = [
            self.enterContext(patch(target, side_effect=AssertionError("unexpected network call")))
            for target in ("socket.socket.connect", "socket.create_connection", "urllib.request.urlopen")
        ]

    def tearDown(self):
        for network_call in self.network_calls:
            network_call.assert_not_called()

    def test_tuple_success_reads_only_allowlisted_operation(self):
        self.tool.call_tool.return_value = [
            SimpleNamespace(
                text=json.dumps(
                    {
                        "value": [
                            {
                                "subject": "Example subject",
                                "from": {"emailAddress": {"address": "sender@example.invalid"}},
                                "receivedDateTime": "2026-01-01T00:00:00Z",
                                "bodyPreview": "  Example\npreview  ",
                                "body": {"content": "Full body must not enter the snapshot"},
                                "isRead": False,
                            }
                        ]
                    }
                )
            )
        ]

        emails, error = chat._read_inbox_live(top=3)

        self.assertIsNone(error)
        self.assertEqual(
            emails,
            [
                {
                    "#": 1,
                    "Subject": "Example subject",
                    "From": "sender@example.invalid",
                    "Received": "2026-01-01T00:00:00Z",
                    "Preview": "Example preview",
                    "Unread": True,
                }
            ],
        )
        server = {**self.config["servers"]["outlook"], "tools": [chat.ALLOWED_READ_OP]}
        self.build_tool.assert_called_once_with("outlook_read", server)
        self.assertEqual(self.resolve_config.call_args.args[0], self.original_config)
        self.tool.__aenter__.assert_awaited_once()
        self.tool.__aexit__.assert_awaited_once()
        self.tool.call_tool.assert_awaited_once_with(chat.ALLOWED_READ_OP, top=3, fetchOnlyUnread=False)

    def test_tuple_success_with_empty_inbox(self):
        self.assertEqual(chat._read_inbox_live(), ([], None))
        self.tool.call_tool.assert_awaited_once_with(
            chat.ALLOWED_READ_OP, top=chat.INBOX_CHAT_TOP, fetchOnlyUnread=False
        )

    def test_runtime_error_is_retained_exactly_without_connector_calls(self):
        error = "could not resolve url '$OUTLOOK_MCP_ENDPOINT'"
        self.build_tool.return_value = (None, error)

        self.assertEqual(chat._read_inbox_live(), (None, error))
        self.build_tool.assert_called_once()
        self.tool.__aenter__.assert_not_awaited()
        self.tool.call_tool.assert_not_awaited()

    def test_missing_runtime_error_uses_explicit_configuration_error(self):
        self.build_tool.return_value = (None, None)

        self.assertEqual(chat._read_inbox_live(), (None, "Outlook MCP endpoint not configured"))
        self.tool.__aenter__.assert_not_awaited()
        self.tool.call_tool.assert_not_awaited()

    def test_unexpected_exposed_tools_fail_closed_before_any_call(self):
        for names in (
            [],
            ["office365_SendEmailV2"],
            [chat.ALLOWED_READ_OP, "office365_SendEmailV2"],
            [chat.ALLOWED_READ_OP, "teams_PostMessageToConversation"],
        ):
            with self.subTest(names=names):
                self.tool.functions = [SimpleNamespace(name=name) for name in names]
                self.tool.__aexit__.reset_mock()

                emails, error = chat._read_inbox_live()

                self.assertIsNone(emails)
                self.assertEqual(error, f"refusing to read: server exposed unexpected tools {sorted(names)}")
                self.tool.call_tool.assert_not_awaited()
                self.tool.__aexit__.assert_awaited_once()

    def test_transport_error_is_not_an_empty_success(self):
        self.tool.call_tool.side_effect = RuntimeError("connector read failed")

        self.assertEqual(chat._read_inbox_live(), (None, "connector read failed"))
        self.tool.call_tool.assert_awaited_once()
        self.tool.__aexit__.assert_awaited_once()

    def test_missing_outlook_server_does_not_build_teams_tool(self):
        self.config_path.read_text.return_value = json.dumps({"servers": {"teams": self.config["servers"]["teams"]}})

        self.assertEqual(chat._read_inbox_live(), (None, "mcp.json has no 'outlook' server"))
        self.build_tool.assert_not_called()
        self.tool.call_tool.assert_not_awaited()


class InboxChatErrorTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(patch.dict(os.environ, {}, clear=True))
        self.enterContext(patch.object(chat, "_read_local_settings", return_value={}))
        self.enterContext(patch.object(chat, "_inbox_chat_live", return_value=True))
        self.post_chat = self.enterContext(patch.object(chat, "_post_chat"))
        self.sample_emails = self.enterContext(patch.object(chat, "_samples_as_emails", return_value=[]))

    def test_initial_failure_displays_runtime_error_and_explicit_sample_fallback(self):
        error = "could not resolve url '$OUTLOOK_MCP_ENDPOINT'"
        live_read = self.enterContext(patch.object(chat, "_read_inbox_live", return_value=(None, error)))
        self.enterContext(patch("builtins.input", side_effect=["q"]))
        output = io.StringIO()

        with redirect_stdout(output):
            chat.chat_with_inbox()

        self.assertIn(f"Live read failed: {error}", output.getvalue())
        self.assertIn("Falling back to sample-data/inbox/ (no real mailbox was read).", output.getvalue())
        live_read.assert_called_once()
        self.sample_emails.assert_called_once()
        self.post_chat.assert_not_called()

    def test_refresh_failure_keeps_previous_snapshot_and_displays_error(self):
        snapshot = [{"#": 1, "Subject": "Original snapshot"}]
        error = "connector read failed"
        live_read = self.enterContext(
            patch.object(chat, "_read_inbox_live", side_effect=[(snapshot, None), (None, error)])
        )
        self.enterContext(patch("builtins.input", side_effect=["refresh", "summarize", "q"]))
        self.post_chat.side_effect = RuntimeError("offline agent stub")
        output = io.StringIO()

        with redirect_stdout(output):
            chat.chat_with_inbox()

        self.assertIn(f"Refresh failed: {error}", output.getvalue())
        self.assertNotIn("Falling back", output.getvalue())
        self.assertEqual(live_read.call_count, 2)
        self.sample_emails.assert_not_called()
        self.post_chat.assert_called_once()
        message = self.post_chat.call_args.args[1]
        self.assertIn(chat._format_snapshot(snapshot, 1), message)
        self.assertNotIn("INBOX SNAPSHOT v2", message)
