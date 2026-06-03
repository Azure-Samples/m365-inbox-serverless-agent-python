"""Pure-Python VIP rule matcher.

This utility has no MCP dependency. It helps agents apply `skills/vip-rules.md`
consistently during local and cloud runs before any reply, Teams post, or
mark-read action is attempted.
"""

import re
from typing import Any

from azure_functions_agents import tool

from tools._log import tool_log
from tools.action_log import append_action


def _field(mail: dict[str, Any], *names: str) -> str:
    for name in names:
        value = mail.get(name)
        if isinstance(value, dict):
            value = value.get("emailAddress", {}).get("address") or value.get("address") or value.get("name")
        if value:
            return str(value)
    return ""


@tool
async def match_rule(mail: dict[str, Any], rules_text: str) -> dict[str, Any] | None:
    """Return the first VIP/special rule match for a mail object.

    Args:
        mail: Mail object with from, subject, body/preview, and id fields.
        rules_text: Markdown rule text, normally from skills/vip-rules.md.
    """
    subject_preview = str(mail.get("subject", "<no subject>"))[:60]
    sender = _field(mail, "from", "sender").lower()
    subject = _field(mail, "subject").lower()
    body = _field(mail, "body", "bodyPreview", "preview").lower()
    haystack = "\n".join([sender, subject, body])

    matches: list[dict[str, Any]] = []
    for raw_line in rules_text.splitlines():
        line = raw_line.strip().lstrip("-").strip()
        if not line or line.startswith("#"):
            continue
        m = re.match(r'^(?:"|`)?([^"`]+?)(?:"|`)?\s*[:|]\s*(.+)$', line)
        if not m:
            continue
        pattern, action = m.group(1).strip().lower(), m.group(2).strip()
        if pattern and pattern in haystack:
            matches.append({"pattern": pattern, "action": action, "source_line": raw_line.strip()})

    if matches:
        first = matches[0]
        tool_log(
            "match_rule",
            {"subject": subject_preview, "rules_len": len(rules_text)},
            f'MATCH pattern="{first["pattern"]}" action="{first["action"]}"',
            offline=False,
        )
        append_action(
            f'match_rule MATCH "{subject_preview}" '
            f'pattern="{first["pattern"]}" action="{first["action"]}"'
        )
        return first

    tool_log(
        "match_rule",
        {"subject": subject_preview, "rules_len": len(rules_text)},
        "no match",
        offline=False,
    )
    append_action(f'match_rule no-match "{subject_preview}"')
    return None
