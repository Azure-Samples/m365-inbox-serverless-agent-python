"""Pure-Python VIP rule matcher.

This utility has no MCP dependency. It helps agents apply `skills/vip-rules.md`
consistently during local and cloud runs before any reply, Teams post, or
mark-read action is attempted.
"""

from __future__ import annotations

import re
from typing import Any

from azure_functions_agents.tools import tool
from pydantic import BaseModel, Field

from .action_log import append_action


class MatchRuleParams(BaseModel):
    mail: dict[str, Any] = Field(description="Mail object with from, subject, body/preview, and id fields.")
    rules_text: str = Field(description="Markdown rule text, normally from skills/vip-rules.md.")


def _field(mail: dict[str, Any], *names: str) -> str:
    for name in names:
        value = mail.get(name)
        if isinstance(value, dict):
            value = value.get("emailAddress", {}).get("address") or value.get("address") or value.get("name")
        if value:
            return str(value)
    return ""


@tool
async def match_rule(params: MatchRuleParams) -> dict[str, Any] | None:
    """Return the first VIP/special rule match. MCP is not needed for this helper."""
    sender = _field(params.mail, "from", "sender").lower()
    subject = _field(params.mail, "subject").lower()
    body = _field(params.mail, "body", "bodyPreview", "preview").lower()
    haystack = "\n".join([sender, subject, body])

    default_rules: list[dict[str, Any]] = [
        {
            "name": "VIP contact",
            "sender": "vip-name@example.com",
            "action": "post_teams",
            "priority": "first",
            "reason": "VIP sender matched; alert Teams before normal processing.",
        },
        {
            "name": "Product incident",
            "sender": "incident.bot@contoso.example",
            "keywords": ["p1", "checkout api", "customer impact", "sev", "incident", "impact"],
            "action": "post_teams",
            "priority": "first",
            "reason": "Incident sender matched with product-impact wording.",
        },
        {
            "name": "Partner contact",
            "sender": "<partner-contact>@example.com",
            "action": "reply_within_1_business_day",
            "priority": "normal",
            "reason": "Partner sender matched; ensure timely response.",
        },
    ]

    for rule in default_rules:
        sender_rule = str(rule.get("sender", "")).lower()
        if sender_rule and sender_rule in haystack:
            keywords = [str(k).lower() for k in rule.get("keywords", [])]
            if keywords and not any(keyword in haystack for keyword in keywords):
                continue
            append_action(
                f'inbox-triage match_rule matched "{params.mail.get("subject", "unknown subject")}" '
                f"as {rule['action']} ({rule['name']})"
            )
            return {"matched": True, **rule}

    rule_blocks = re.split(r"\n(?=###\s+)", params.rules_text or "")
    for block in rule_blocks:
        title_match = re.search(r"###\s+(.+)", block)
        trigger_match = re.search(r"[-*]\s+\*\*Trigger:\*\*\s*(.+)", block, re.IGNORECASE)
        action_match = re.search(r"[-*]\s+\*\*Action:\*\*\s*(.+)", block, re.IGNORECASE)
        if not trigger_match:
            continue
        trigger = trigger_match.group(1)
        candidates = re.findall(r"`([^`]+)`", trigger)
        matched_value = None
        for candidate in candidates:
            if candidate.startswith("regex:"):
                pattern = candidate.removeprefix("regex:").strip()
                if re.search(pattern, haystack, re.IGNORECASE):
                    matched_value = candidate
                    break
            elif candidate.lower() in haystack:
                matched_value = candidate
                break
        if matched_value:
            rule_name = title_match.group(1).strip() if title_match else "Markdown rule"
            action = action_match.group(1).strip() if action_match else "review"
            append_action(
                f'inbox-triage match_rule matched "{params.mail.get("subject", "unknown subject")}" '
                f"as {action} ({rule_name})"
            )
            return {
                "matched": True,
                "name": rule_name,
                "trigger": matched_value,
                "action": action,
                "priority": "first" if "first" in block.lower() else "normal",
                "reason": f"Matched rule trigger `{matched_value}`.",
            }
    return None
