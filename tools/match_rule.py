"""Pure-Python VIP rule matcher.

This utility has no MCP dependency. It helps agents apply `skills/vip-rules.md`
consistently before any reply, Teams post, or mark-read action is attempted.
"""

from typing import Any

from azure_functions_agents import tool


def _field(mail: dict[str, Any], *names: str) -> str:
    for name in names:
        value = mail.get(name)
        if isinstance(value, dict):
            value = (
                value.get("emailAddress", {}).get("address")
                or value.get("address")
                or value.get("name")
            )
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
    sender = _field(mail, "from", "sender", "From").lower()
    subject = _field(mail, "subject", "Subject").lower()
    body = _field(mail, "body", "bodyPreview", "preview", "Body", "BodyPreview").lower()
    haystack = "\n".join([sender, subject, body])

    for block in _iter_rule_blocks(rules_text):
        triggers = [t.strip().lower() for t in block.get("triggers", []) if t.strip()]
        if not triggers:
            continue
        if any(trigger and trigger in haystack for trigger in triggers):
            return {
                "title": block.get("title", "Untitled rule"),
                "trigger": ", ".join(triggers),
                "action": block.get("action", ""),
                "priority": block.get("priority", ""),
                "safety": block.get("safety", ""),
            }

    return None


def _iter_rule_blocks(rules_text: str) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    current: dict[str, Any] = {}
    for raw_line in rules_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("## "):
            if current:
                blocks.append(current)
            current = {"title": line[3:].strip(), "triggers": []}
            continue
        lower = line.lower()
        if lower.startswith("- trigger:") or lower.startswith("trigger:"):
            value = line.split(":", 1)[1].strip()
            current.setdefault("triggers", []).extend(
                token.strip() for token in value.split(",") if token.strip()
            )
        elif lower.startswith("- action:") or lower.startswith("action:"):
            current["action"] = line.split(":", 1)[1].strip()
        elif lower.startswith("- priority:") or lower.startswith("priority:"):
            current["priority"] = line.split(":", 1)[1].strip()
        elif lower.startswith("- safety:") or lower.startswith("safety:"):
            current["safety"] = line.split(":", 1)[1].strip()
    if current:
        blocks.append(current)
    return blocks
