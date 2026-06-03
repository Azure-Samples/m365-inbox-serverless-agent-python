"""Local fallback email sender.

Production agents should prefer the Outlook MCP send-mail/reply action. This
fallback writes an RFC-822-like `.eml` file to `out/` so local runs are
inspectable without Microsoft 365 or Foundry credentials.
"""

import datetime as dt
import re
from email.utils import formatdate
from pathlib import Path

from azure_functions_agents import tool

from tools.action_log import append_action


@tool
async def send_reply(
    to: str,
    subject: str,
    body_html: str,
    in_reply_to_id: str | None = None,
) -> str:
    """Send an email reply or digest. MCP preferred; fallback writes `out/*.eml`.

    Args:
        to: Recipient email address.
        subject: Subject line for the reply or digest.
        body_html: HTML body to send.
        in_reply_to_id: Optional message id to reply to.
    """
    today = dt.date.today().isoformat()
    slug = re.sub(r"[^a-z0-9]+", "-", subject.lower()).strip("-")[:48] or "message"
    out_dir = Path(__file__).resolve().parent.parent / "out"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{today}-{slug}.eml"
    reply_headers = ""
    if in_reply_to_id:
        reply_headers = f"In-Reply-To: {in_reply_to_id}\nReferences: {in_reply_to_id}\n"
    path.write_text(
        "From: agent@functions.local\n"
        f"To: {to}\n"
        f"Subject: {subject}\n"
        f"Date: {formatdate(localtime=True)}\n"
        f"{reply_headers}"
        "MIME-Version: 1.0\n"
        "Content-Type: text/html; charset=utf-8\n\n"
        f"{body_html}\n",
        encoding="utf-8",
    )
    append_action(f'inbox-triage send_reply (offline) to={to} subject="{subject}"')
    return f"ok: wrote {path.relative_to(Path.cwd())}"
