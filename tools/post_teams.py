"""Local fallback Teams poster.

Production agents should prefer the Teams MCP channel-post action. This
fallback writes markdown under `out/` so local runs show what would have been
posted to Teams.
"""

import datetime as dt
import re
from pathlib import Path

from azure_functions_agents import tool

from tools.action_log import append_action


@tool
async def post_teams(
    team_id: str,
    channel_id: str,
    body_html: str,
    subject: str | None = None,
) -> str:
    """Post a Teams channel message. MCP preferred; fallback writes `out/teams-*.md`.

    Args:
        team_id: Teams team id or environment placeholder.
        channel_id: Teams channel id or environment placeholder.
        body_html: HTML or markdown-compatible post body.
        subject: Optional post subject.
    """
    out_dir = Path(__file__).resolve().parent.parent / "out"
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now(dt.UTC).strftime("%Y%m%d-%H%M%S")
    path = out_dir / f"teams-{stamp}.md"
    title = subject or "Teams notification"
    body = re.sub(r"<br\s*/?>", "\n", body_html)
    path.write_text(
        f"# {title}\n\n"
        f"- Team: `{team_id}`\n"
        f"- Channel: `{channel_id}`\n"
        f"- Created: {dt.datetime.now(dt.UTC).isoformat()}\n\n"
        f"{body}\n",
        encoding="utf-8",
    )
    summary = re.sub(r"\s+", " ", body).strip()[:120]
    append_action(f'inbox-triage post_teams (offline) channel={channel_id} summary="{summary}"')
    return f"ok: wrote {path.relative_to(Path.cwd())}"
