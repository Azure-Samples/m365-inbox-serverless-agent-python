"""Local fallback Teams poster.

Production agents should prefer the Teams MCP channel-post action. This
fallback writes markdown under `out/` so local runs show what would have been
posted to Teams.
"""

from __future__ import annotations

import datetime as dt
import re
from pathlib import Path

from azure_functions_agents.tools import tool
from pydantic import BaseModel, Field

from .action_log import append_action


class PostTeamsParams(BaseModel):
    team_id: str = Field(description="Teams team id or environment placeholder.")
    channel_id: str = Field(description="Teams channel id or environment placeholder.")
    subject: str | None = Field(default=None, description="Optional post subject.")
    body_html: str = Field(description="HTML or markdown-compatible post body.")


@tool
async def post_teams(params: PostTeamsParams) -> str:
    """Post a Teams channel message. MCP preferred; fallback writes `out/teams-*.md`."""
    out_dir = Path(__file__).resolve().parent.parent / "out"
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now(dt.UTC).strftime("%Y%m%d-%H%M%S")
    path = out_dir / f"teams-{stamp}.md"
    title = params.subject or "Teams notification"
    body = re.sub(r"<br\s*/?>", "\n", params.body_html)
    path.write_text(
        f"# {title}\n\n"
        f"- Team: `{params.team_id}`\n"
        f"- Channel: `{params.channel_id}`\n"
        f"- Created: {dt.datetime.now(dt.UTC).isoformat()}\n\n"
        f"{body}\n",
        encoding="utf-8",
    )
    summary = re.sub(r"\s+", " ", body).strip()[:120]
    append_action(f'inbox-triage post_teams (offline) channel={params.channel_id} summary="{summary}"')
    return f"ok: wrote {path.relative_to(Path.cwd())}"
