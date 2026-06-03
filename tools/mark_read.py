"""Local fallback read-marker.

Production agents should prefer the Outlook MCP message update action. This
fallback appends message ids to `out/read-log.txt` for offline verification.
"""

from __future__ import annotations

from azure_functions_agents import tool
from pydantic import BaseModel, Field

from tools.action_log import append_action


class MarkReadParams(BaseModel):
    message_id: str = Field(description="Message identifier to mark as read.")


@tool
async def mark_read(params: MarkReadParams) -> str:
    """Mark a message as read. MCP preferred; fallback logs the message id."""
    append_action(f"inbox-triage mark_read (offline) message_id={params.message_id}")
    return f"ok: logged {params.message_id}"
