"""Local fallback inbox reader.

Production agents should prefer the Outlook MCP server declared in `mcp.json`.
When MCP is not configured, this tool loads mock JSON messages from
`sample-data/inbox/` so the sample can run offline.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from azure_functions_agents.tools import tool
from pydantic import BaseModel, Field


class ListInboxParams(BaseModel):
    since_minutes: int = Field(default=5, ge=1, description="Lookback window in minutes.")
    top: int = Field(default=50, ge=1, le=100, description="Maximum messages to return.")


@tool
async def list_inbox(params: ListInboxParams) -> list[dict[str, Any]]:
    """List inbox messages. MCP preferred; this offline fallback returns sample mail."""
    if os.getenv("OUTLOOK_MCP_ENDPOINT"):
        logging.info("OUTLOOK_MCP_ENDPOINT is set; the agent should prefer the Outlook MCP `list_messages` action.")
        return []

    inbox_dir = Path(__file__).resolve().parent.parent / "sample-data" / "inbox"
    messages: list[dict[str, Any]] = []
    if not inbox_dir.exists():
        return []

    for path in sorted(inbox_dir.glob("*.json"))[: params.top]:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logging.warning("Skipping unreadable sample message %s: %s", path.name, exc)
            continue
        if isinstance(data, dict):
            messages.append(data)
        if len(messages) >= min(params.top, 5):
            break
    return messages
