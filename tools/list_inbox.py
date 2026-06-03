"""Local fallback inbox reader.

This is the offline sample-data path. When deployed to Azure, an MCP server
provides a richer `list_messages` action; locally, this stub always returns
canned sample mail from `sample-data/inbox/` so the demo works without M365
credentials.
"""

import json
import logging
import os
from pathlib import Path
from typing import Any

from azure_functions_agents import tool

from tools._log import tool_log
from tools.action_log import append_action


@tool
async def list_inbox(since_minutes: int = 5, top: int = 50) -> list[dict[str, Any]]:
    """List inbox messages from the local sample-data fixtures.

    Args:
        since_minutes: Lookback window in minutes (>=1). Local stub ignores this
            and returns all sample messages.
        top: Maximum messages to return (1-100).
    """
    if os.getenv("OUTLOOK_MCP_ENDPOINT"):
        logging.info(
            "[TOOL] list_inbox: OUTLOOK_MCP_ENDPOINT is set, but this is the "
            "offline stub. Returning local sample data anyway."
        )

    inbox_dir = Path(__file__).resolve().parent.parent / "sample-data" / "inbox"
    messages: list[dict[str, Any]] = []
    if not inbox_dir.exists():
        tool_log("list_inbox", {"since_minutes": since_minutes, "top": top}, "0 messages (no sample-data dir)")
        return []

    for path in sorted(inbox_dir.glob("*.json"))[:top]:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logging.warning("Skipping unreadable sample message %s: %s", path.name, exc)
            continue
        if isinstance(data, dict):
            messages.append(data)
        if len(messages) >= top:
            break

    tool_log(
        "list_inbox",
        {"since_minutes": since_minutes, "top": top},
        f"{len(messages)} sample messages",
    )
    append_action(f"list_inbox returned {len(messages)} sample messages")
    return messages
