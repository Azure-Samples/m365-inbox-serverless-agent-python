"""Installed-runtime smoke tests: isolated configuration and no external calls."""

import asyncio
import importlib.util
import json
import os
import shutil
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import chat

ROOT = Path(__file__).resolve().parent.parent


class RuntimeCompatibilityTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(patch.dict(os.environ, {}, clear=True))
        self.network_calls = [
            self.enterContext(patch(target, side_effect=AssertionError("unexpected network call")))
            for target in ("socket.socket.connect", "socket.create_connection", "urllib.request.urlopen")
        ]
        from azure_functions_agents.config.paths import set_app_root
        from azure_functions_agents.discovery.mcp import clear_mcp_cache

        self.addCleanup(set_app_root, ROOT)
        self.addCleanup(clear_mcp_cache)
        clear_mcp_cache()
        self.app_root = Path(self.enterContext(TemporaryDirectory()))
        for filename in ("agents.config.yaml", "mcp.json", "host.json"):
            shutil.copyfile(ROOT / filename, self.app_root / filename)
        for source in ROOT.glob("*.agent.md"):
            shutil.copyfile(source, self.app_root / source.name)
        shutil.copytree(ROOT / "tools", self.app_root / "tools")
        shutil.copytree(ROOT / "skills", self.app_root / "skills")
        self.enterContext(patch.object(chat, "_read_local_settings", return_value={}))
        self.enterContext(patch.object(chat, "MCP_JSON_PATH", self.app_root / "mcp.json"))
        self.credential = Mock()
        self.credential.get_token.side_effect = AssertionError("unexpected token request")
        self.enterContext(patch("azure_functions_agents.discovery.mcp.build_credential", return_value=self.credential))

    def tearDown(self):
        self.credential.get_token.assert_not_called()
        for network_call in self.network_calls:
            network_call.assert_not_called()

    def test_real_builder_tuple_success_preserves_read_allowlist(self):
        self.enterContext(patch.dict(os.environ, {"OUTLOOK_MCP_ENDPOINT": "https://outlook.example.invalid/mcp"}))
        tool = MagicMock(spec=["__aenter__", "__aexit__", "functions", "call_tool"])
        tool.__aenter__ = AsyncMock(return_value=tool)
        tool.__aexit__ = AsyncMock(return_value=False)
        tool.functions = [SimpleNamespace(name=chat.ALLOWED_READ_OP)]
        tool.call_tool = AsyncMock(return_value=[SimpleNamespace(text='{"value": []}')])
        transport = self.enterContext(
            patch("azure_functions_agents.discovery.mcp.MCPStreamableHTTPTool", return_value=tool)
        )
        self.enterContext(patch("azure_functions_agents.discovery.mcp._build_header_provider", return_value=None))

        self.assertEqual(chat._read_inbox_live(top=2), ([], None))

        transport.assert_called_once()
        self.assertEqual(transport.call_args.kwargs["allowed_tools"], [chat.ALLOWED_READ_OP])
        self.assertEqual(transport.call_args.kwargs["name"], "outlook_read")
        tool.call_tool.assert_awaited_once_with(chat.ALLOWED_READ_OP, top=2, fetchOnlyUnread=False)

    def test_real_builder_configuration_error_is_retained_exactly(self):
        config = json.loads((self.app_root / "mcp.json").read_text())
        config["servers"]["outlook"]["url"] = ""
        (self.app_root / "mcp.json").write_text(json.dumps(config))
        transport = self.enterContext(patch("azure_functions_agents.discovery.mcp.MCPStreamableHTTPTool"))

        self.assertEqual(chat._read_inbox_live(), (None, "missing 'url'"))
        transport.assert_not_called()

    def test_global_config_preserves_capabilities_for_every_sample_agent(self):
        from azure_functions_agents.config.loader import load_agent_specs, load_global_config
        from azure_functions_agents.config.merge import compose
        from azure_functions_agents.registration.capabilities import build_capabilities

        global_config = load_global_config(self.app_root)
        self.assertIs(global_config.system_tools.web_request, False)
        specs = load_agent_specs(self.app_root)
        self.assertEqual(len(specs), 4)
        matcher = SimpleNamespace(name="match_rule")
        connectors = {name: SimpleNamespace(name=name) for name in ("outlook", "teams")}
        for spec in specs:
            source_name = Path(spec.source_file).name
            with self.subTest(agent=source_name):
                resolved = compose(
                    spec, global_config, discovered_mcp_names=list(connectors), discovered_skill_names=[]
                )
                capabilities = build_capabilities(
                    resolved,
                    discovered_user_tools=[matcher],
                    discovered_mcp_tools=connectors,
                    discovered_skills={},
                )
                self.assertIsNone(resolved.web_request_config)
                self.assertIsNone(resolved.sandbox_config)
                self.assertIsNone(resolved.workflows)
                self.assertEqual(resolved.builtin_endpoints.http_auth.mode, "function")
                self.assertEqual(capabilities.web_request_tools, [])
                self.assertEqual(capabilities.filtered_workflow_tools, [])
                if source_name == "inbox-chat.agent.md":
                    self.assertEqual(capabilities.filtered_user_tools, [])
                    self.assertEqual(capabilities.filtered_mcp_tools, [])
                else:
                    self.assertEqual(capabilities.filtered_user_tools, [matcher])
                    self.assertEqual(capabilities.filtered_mcp_tools, list(connectors.values()))

    def test_entry_point_indexes_expected_routes_and_timeout_shim(self):
        from azure_functions_agents import create_function_app
        from azure_functions_agents.discovery import mcp

        factory = self.enterContext(
            patch("azure_functions_agents.create_function_app", side_effect=lambda: create_function_app(self.app_root))
        )
        spec = importlib.util.spec_from_file_location("isolated_function_app", ROOT / "function_app.py")
        self.assertIsNotNone(spec)
        entry_point = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(entry_point)
        factory.assert_called_once_with()
        functions = entry_point.app.get_functions()
        names = {function.get_function_name() for function in functions}
        self.assertTrue({"inbox_triage", "daily_briefing", "weekly_rule_suggestions"} <= names)
        routes = {}
        for function in functions:
            for binding in function.get_bindings():
                data = binding.get_dict_repr()
                if data["type"] == "httpTrigger":
                    routes[data["route"]] = data
        expected = {
            f"agents/{name}/chat"
            for name in ("inbox_triage", "daily_briefing", "weekly_rule_suggestions", "inbox_chat")
        }
        self.assertTrue(expected <= routes.keys())
        for route, binding in routes.items():
            self.assertNotIn("workflow", route)
            self.assertEqual(str(binding["authLevel"]).lower(), "function")
        self.assertTrue(getattr(mcp._build_http_client, "_read_timeout_patched", False))
        self.assertIsNone(mcp._build_http_client(None))
        provider = Mock(return_value={})
        client = mcp._build_http_client(provider)
        try:
            self.assertIsNone(client.timeout.read)
            self.assertEqual(client.timeout.connect, 30.0)
            provider.assert_not_called()
        finally:
            asyncio.run(client.aclose())
