"""Local fallback read-marker.

Production agents should prefer the Outlook MCP message update action. This
fallback appends message ids to `out/read-log.txt` for offline verification.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

from azure_functions_agents.tools import tool
from pydantic import BaseModel, Field


class MarkReadParams(BaseModel):
    message_id: str = Field(description="Message identifier to mark as read.")


@tool
async def mark_read(params: MarkReadParams) -> str:
    """Mark a message as read. MCP preferred; fallback logs the message id."""
    out_dir = Path(__file__).resolve().parent.parent / "out"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "read-log.txt"
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"{dt.datetime.now(dt.UTC).isoformat()} {params.message_id}\n")
    return f"ok: logged {params.message_id}"
