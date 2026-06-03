"""Local fallback read-marker.

Production agents should prefer the Outlook MCP message update action. This
fallback appends message ids to `out/read-log.txt` for offline verification.
"""

from azure_functions_agents import tool

from tools._log import tool_log
from tools.action_log import append_action


@tool
async def mark_read(message_id: str) -> str:
    """Mark a message as read (offline stub logs the id only).

    Args:
        message_id: Message identifier to mark as read.
    """
    tool_log("mark_read", {"message_id": message_id}, "logged to read-log.txt")
    append_action(f"mark_read message_id={message_id}")
    return f"ok: logged {message_id}"
