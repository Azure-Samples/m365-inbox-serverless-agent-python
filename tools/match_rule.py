"""Pure-Python VIP rule matcher.

This utility has no MCP dependency. It helps agents apply `skills/vip-rules.md`
consistently before any reply, Teams post, or mark-read action is attempted.

The tool always loads the canonical rules from `skills/vip-rules.md`, so the
model never has to supply (or invent) the rule text. Arguments are flat and
optional so a small model can call it reliably with just the email's subject,
sender, and body.
"""

import os
import re
from pathlib import Path
from typing import Any

from azure_functions_agents import tool

RULES_PATH = Path(__file__).resolve().parent.parent / "skills" / "vip-rules.md"

_BACKTICK_RX = re.compile(r"`([^`]+)`")
_BOLD_RX = re.compile(r"\*\*")
_LABEL_RX = re.compile(
    r"^-?\s*(trigger|condition|action|priority|safety|channel)\b[^:]*:", re.IGNORECASE
)

# A route name is a short, lowercase identifier: letters, digits, and internal
# hyphens only. This keeps the env-suffix transform (`-` -> `_`, upper) free of
# collisions, since a route name can never itself contain an underscore.
_ROUTE_RX = re.compile(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?$")

# Values that mean "this setting was never wired up". Mirrors the placeholder
# detection used at host startup so an unset named route falls back to default
# instead of posting to a literal placeholder.
_PLACEHOLDER_VALUES = {
    "todo",
    "changeme",
    "replace_me",
    "your-team-id",
    "your-channel-id",
    "your-value",
}


def _is_unresolved(value: str | None) -> bool:
    """True when a Teams id env var is empty or still a placeholder."""
    if not value:
        return True
    stripped = value.strip()
    if not stripped or stripped.startswith("$") or stripped.startswith("<"):
        return True
    return stripped.lower() in _PLACEHOLDER_VALUES


def _resolve_channel(route: str) -> dict[str, Any] | None:
    """Resolve a rule's named route to a Teams recipient.

    Named routes are additive env-var pairs `TEAMS_TEAM_ID__<ROUTE>` and
    `TEAMS_CHANNEL_ID__<ROUTE>` (see skills/teams-channels.md). The default
    channel (`TEAMS_TEAM_ID` / `TEAMS_CHANNEL_ID`) is a distinct first-class
    concept and is never returned here.

    Returns None when the rule names no route. When a route is named:
      - fully wired   -> {channel, route_resolved: True, teams_recipient:{groupId, channelId}}
      - unset/invalid -> {channel, route_resolved: False}  (caller uses default)
    `teams_recipient` is intentionally omitted unless a named route is fully
    wired, so the default path keeps using the prompt's $TEAMS_* literals and no
    real ids surface for routes that are not configured.
    """
    route = (route or "").strip().strip("`").lower()
    if not route:
        return None
    if not _ROUTE_RX.match(route):
        return {"channel": route, "route_resolved": False}
    suffix = route.upper().replace("-", "_")
    team = os.environ.get(f"TEAMS_TEAM_ID__{suffix}")
    channel = os.environ.get(f"TEAMS_CHANNEL_ID__{suffix}")
    if _is_unresolved(team) or _is_unresolved(channel):
        return {"channel": route, "route_resolved": False}
    return {
        "channel": route,
        "route_resolved": True,
        "teams_recipient": {"groupId": team.strip(), "channelId": channel.strip()},
    }

_rules_cache: tuple[tuple[str, int], str] | None = None


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


def _load_rules_text() -> str:
    """Read skills/vip-rules.md, cached by file mtime. Returns '' if missing."""
    global _rules_cache
    try:
        stat = RULES_PATH.stat()
    except OSError:
        return ""
    key = (str(RULES_PATH), stat.st_mtime_ns)
    if _rules_cache is not None and _rules_cache[0] == key:
        return _rules_cache[1]
    try:
        text = RULES_PATH.read_text(encoding="utf-8")
    except OSError:
        return ""
    _rules_cache = (key, text)
    return text


def _iter_rule_blocks(rules_text: str) -> list[dict[str, Any]]:
    """Parse the `### Rule N:` blocks from vip-rules.md.

    Trigger and Condition lines carry the matchable tokens inside backticks
    (for example `vip-name@example.com` or `p1`). A `regex:<pattern>` token is
    treated as a regular expression. Only `### ` headings are treated as rules,
    so document sections like `## Matching notes` are ignored.
    """
    blocks: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    in_fence = False
    for raw_line in rules_text.splitlines():
        line = raw_line.strip()
        if line.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence or not line:
            continue
        if line.startswith("### "):
            if current:
                blocks.append(current)
            current = {
                "title": line[4:].strip(),
                "tokens": [],
                "regexes": [],
                "action": [],
                "priority": "",
                "safety": "",
                "channel": "",
            }
            continue
        if current is None:
            continue
        clean = _BOLD_RX.sub("", line)
        match = _LABEL_RX.match(clean)
        if not match:
            continue
        label = match.group(1).lower()
        value = clean.split(":", 1)[1].strip() if ":" in clean else ""
        if label in ("trigger", "condition"):
            for token in _BACKTICK_RX.findall(clean):
                token = token.strip()
                if token.lower().startswith("regex:"):
                    pattern = token.split(":", 1)[1].strip()
                    if pattern:
                        current["regexes"].append(pattern)
                elif token:
                    current["tokens"].append(token.lower())
        elif label == "action" and value:
            current["action"].append(value)
        elif label == "priority" and not current["priority"]:
            current["priority"] = value
        elif label == "safety" and not current["safety"]:
            current["safety"] = value
        elif label == "channel" and not current["channel"]:
            current["channel"] = value
    if current:
        blocks.append(current)
    return blocks


@tool
async def match_rule(
    mail: dict[str, Any] | None = None,
    subject: str = "",
    sender: str = "",
    body: str = "",
) -> dict[str, Any] | None:
    """Check one email against skills/vip-rules.md and return the first matching rule.

    Pass the email's subject, sender address, and body (or preview) text. Every
    argument is optional; when a full mail object is supplied any missing field
    is taken from it. The VIP rules are loaded from disk automatically, so do
    not pass rule text. Returns None when no rule matches.

    When the matched rule names a Teams route (a `Channel:` line) that is fully
    wired, the result also includes `channel`, `route_resolved: true`, and a
    `teams_recipient` object `{groupId, channelId}` to copy straight into a Teams
    post's `body.recipient`. If the named route is unset, `route_resolved` is
    false and no `teams_recipient` is returned, so the caller uses the default
    `$TEAMS_TEAM_ID` / `$TEAMS_CHANNEL_ID` channel.

    Args:
        mail: Optional full mail object (OnNewEmailV3 or Graph shape). Used to
            fill any field not passed explicitly.
        subject: Email subject line.
        sender: Sender email address.
        body: Email body or preview text.
    """
    if mail:
        subject = subject or _field(mail, "subject", "Subject")
        sender = sender or _field(mail, "from", "sender", "From")
        body = body or _field(mail, "body", "bodyPreview", "preview", "Body", "BodyPreview")

    haystack = "\n".join([sender.lower(), subject.lower(), body.lower()])
    if not haystack.strip():
        return None

    for block in _iter_rule_blocks(_load_rules_text()):
        matched = any(token and token in haystack for token in block["tokens"])
        if not matched:
            for pattern in block["regexes"]:
                try:
                    if re.search(pattern, haystack, re.IGNORECASE):
                        matched = True
                        break
                except re.error:
                    continue
        if matched:
            result: dict[str, Any] = {
                "title": block["title"],
                "trigger": ", ".join(block["tokens"]) or "pattern",
                "action": ", ".join(block["action"]),
                "priority": block["priority"],
                "safety": block["safety"],
            }
            route = _resolve_channel(block.get("channel", ""))
            if route:
                result.update(route)
            return result

    return None
