"""Local test client for the M365 Inbox Agent function app.

Calls each agent's built-in synchronous chat endpoint
(`POST /api/agents/<agent>/chat`, enabled by `builtin_endpoints.chat_api`
in the .agent.md frontmatter), then prints exactly what the agent did:
every tool call it made and its final one-line summary. No log scraping.

Shows a mode banner at the top: 🟢 Live (real Outlook/Teams MCP endpoints
configured in local.settings.json) vs 🟡 Partial (Outlook wired but mailbox
is a placeholder) vs 🟡 Offline (sample-data fallback).
"""

import json
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE_URL = os.environ.get("AGENT_URL", "http://localhost:7071").rstrip("/")
FUNCTION_KEY = os.environ.get("FUNCTION_KEY", "")
LOG_PATH = Path(os.environ.get("ACTION_LOG_PATH", "out/read-log.txt"))
CHAT_TIMEOUT_SEC = int(os.environ.get("CHAT_TIMEOUT_SEC", "180"))
SETTINGS_PATH = Path(os.environ.get("LOCAL_SETTINGS_PATH", "local.settings.json"))
SAMPLE_INBOX_DIR = Path(os.environ.get("SAMPLE_INBOX_DIR", "sample-data/inbox"))

AGENTS = {
    "1": ("inbox_triage", "inbox-triage", "Triage inbox now (classify VIP / incident / FYI; reply or alert)"),
    "2": ("daily_briefing", "daily-briefing", "Send today's briefing to MAILBOX_OWNER_EMAIL"),
    "3": ("weekly_rule_suggestions", "weekly-rule-suggestions", "Propose rule updates based on recent decisions"),
}

# Per-agent settings dependencies. REQUIRED keys are used on every run; if any
# are placeholders the agent silently no-ops, so we hard-gate. CONDITIONAL keys
# are only touched on certain branches (e.g. Teams alerts on urgent matches),
# so we surface a soft warning but still allow the run.
AGENT_DEPS: dict[str, dict[str, tuple[str, ...]]] = {
    "inbox_triage": {
        "required": (),
        "conditional": ("TEAMS_TEAM_ID", "TEAMS_CHANNEL_ID"),
    },
    "daily_briefing": {
        "required": ("MAILBOX_OWNER_EMAIL",),
        "conditional": ("TEAMS_TEAM_ID", "TEAMS_CHANNEL_ID"),
    },
    "weekly_rule_suggestions": {
        "required": ("MAILBOX_OWNER_EMAIL",),
        "conditional": (),
    },
}
DEP_PURPOSE = {
    "MAILBOX_OWNER_EMAIL": "Outlook recipient",
    "TEAMS_TEAM_ID": "Teams alerts on urgent items",
    "TEAMS_CHANNEL_ID": "Teams alerts on urgent items",
}


def _read_local_settings() -> dict[str, str]:
    if not SETTINGS_PATH.exists():
        return {}
    try:
        data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    values = data.get("Values") or {}
    return {k: v for k, v in values.items() if isinstance(v, str)}


def _is_placeholder(value: str | None) -> bool:
    if not value:
        return True
    s = value.strip()
    return s == "" or s.startswith("<") or s.startswith("$")


def _missing_for(agent_name: str) -> tuple[list[str], list[str]]:
    """Return (required_missing, conditional_missing) settings for an agent."""
    values = _read_local_settings()
    deps = AGENT_DEPS.get(agent_name, {"required": (), "conditional": ()})

    def _check(keys: tuple[str, ...]) -> list[str]:
        out = []
        for k in keys:
            v = values.get(k) or os.environ.get(k) or ""
            if _is_placeholder(v):
                out.append(k)
        return out

    return _check(deps["required"]), _check(deps["conditional"])


def detect_mode() -> tuple[str, str]:
    """Return (icon, label) describing whether the host is wired to real M365."""
    values = _read_local_settings()
    outlook = values.get("OUTLOOK_MCP_ENDPOINT") or os.environ.get("OUTLOOK_MCP_ENDPOINT") or ""
    mailbox = values.get("MAILBOX_OWNER_EMAIL") or os.environ.get("MAILBOX_OWNER_EMAIL") or ""
    if not _is_placeholder(outlook) and not _is_placeholder(mailbox):
        return ("🟢", f"Live M365  ({mailbox.strip()})")
    if not _is_placeholder(outlook):
        return ("🟡", "Partial: Outlook MCP set, but MAILBOX_OWNER_EMAIL is a placeholder")
    return ("🟡", "Offline (sample-data + out/read-log.txt)")


def _mailbox_owner() -> str | None:
    """Return a real MAILBOX_OWNER_EMAIL if set, else None."""
    values = _read_local_settings()
    mailbox = values.get("MAILBOX_OWNER_EMAIL") or os.environ.get("MAILBOX_OWNER_EMAIL") or ""
    return None if _is_placeholder(mailbox) else mailbox.strip()


def chat_url(agent_name: str) -> str:
    url = f"{BASE_URL}/api/agents/{agent_name}/chat"
    if FUNCTION_KEY:
        url += f"?code={FUNCTION_KEY}"
    return url


_TEAMS_TRIGGERING_RX = re.compile(r"urgent|p1\b|incident|escalat|outage", re.IGNORECASE)
_SKIP_RX = re.compile(r"^\s*fyi\b|newsletter", re.IGNORECASE)


def _classify_subject(subject: str) -> str:
    """Predict which branch inbox_triage will take for a given subject.

    Mirrors the agent's operating loop so we only send samples whose required
    connectors are actually configured:
      - 'teams' : urgent / P1 / incident / outage  -> posts to Teams
      - 'skip'  : FYI / newsletter                 -> no outbound connector call
      - 'reply' : everything else                  -> replies to the sender
    """
    if _TEAMS_TRIGGERING_RX.search(subject):
        return "teams"
    if _SKIP_RX.search(subject):
        return "skip"
    return "reply"


def _graph_to_onnewemail(graph: dict, from_override: str | None = None) -> dict:
    """Convert a Graph-shaped sample email to the OnNewEmailV3 PascalCase shape."""
    subject = graph.get("subject", "") or ""
    original_from = graph.get("from", {}).get("emailAddress", {}).get("address", "")
    to_list = graph.get("toRecipients", [])
    body = graph.get("body", {}).get("content", "") or ""
    return {
        "Id": graph.get("id", ""),
        "Subject": subject,
        "From": from_override or original_from,
        "To": ";".join(r.get("emailAddress", {}).get("address", "") for r in to_list),
        "BodyPreview": body[:200],
        "Body": body,
        "Importance": graph.get("importance", "normal"),
        "HasAttachments": graph.get("hasAttachments", False),
        "ConversationId": graph.get("conversationId", graph.get("id", "")),
    }


def _select_samples() -> tuple[list[dict], list[str]]:
    """Pick sample emails whose required connectors are configured.

    Returns (emails, notes). A sample is only included when the agent's likely
    branch can actually complete:
      - reply samples require a real MAILBOX_OWNER_EMAIL. When set, we rewrite
        the sample's From to the owner so the agent's reply (To = sender) lands
        in the owner's own mailbox: a real, visible round-trip. When the mailbox
        is a placeholder, reply samples are excluded so we never send to a fake
        @example.com address (those bounce, fail 3x, and trip the agent's
        circuit breaker).
      - teams samples require TEAMS_TEAM_ID and TEAMS_CHANNEL_ID. When either is
        a placeholder, they are excluded for the same reason.
      - skip samples (FYI / newsletter) take no outbound action and are always
        safe to send.
    """
    if not SAMPLE_INBOX_DIR.is_dir():
        return [], [f"  ⚠ {SAMPLE_INBOX_DIR}/ not found; sending an empty inbox."]

    mailbox = _mailbox_owner()
    _, teams_missing = _missing_for("inbox_triage")
    teams_ok = not teams_missing

    emails: list[dict] = []
    excluded_reply = 0
    excluded_teams = 0
    for f in sorted(SAMPLE_INBOX_DIR.glob("*.json")):
        try:
            graph = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        category = _classify_subject(graph.get("subject", "") or "")
        if category == "teams" and not teams_ok:
            excluded_teams += 1
            continue
        if category == "reply" and not mailbox:
            excluded_reply += 1
            continue
        from_override = mailbox if (category == "reply" and mailbox) else None
        emails.append(_graph_to_onnewemail(graph, from_override=from_override))

    notes: list[str] = []
    if emails:
        listed = "\n".join(
            f"    - {e['Subject'][:60]}  ({_classify_subject(e['Subject'])})" for e in emails
        )
        notes.append(f"  Sending {len(emails)} sample email(s) as the OnNewEmailV3 payload:")
        notes.append(listed)
    else:
        notes.append("  No safe samples to send for the current config (see exclusions below).")
    if excluded_reply:
        notes.append(
            f"  Skipped {excluded_reply} reply sample(s): MAILBOX_OWNER_EMAIL is a placeholder, so a\n"
            "    reply would be sent to a fake address, bounce, and trip the agent's circuit breaker.\n"
            "    Set a real MAILBOX_OWNER_EMAIL to have the agent reply into your own inbox."
        )
    if excluded_teams:
        notes.append(
            f"  Skipped {excluded_teams} Teams sample(s): TEAMS_TEAM_ID / TEAMS_CHANNEL_ID is a placeholder.\n"
            "    Set both to have the agent post urgent items to your channel."
        )
    return emails, notes


def _build_prompt(agent_name: str) -> tuple[str, list[str]]:
    """Return (prompt, notes) for the /chat call."""
    if agent_name == "inbox_triage":
        emails, notes = _select_samples()
        prompt = (
            "A new batch of email arrived in the mailbox.\n\n"
            "Trigger data:\n"
            "```json\n"
            f"{json.dumps(emails, indent=2)}\n"
            "```\n\n"
            "Run your operating loop for every message and end with the one-line summary."
        )
        return prompt, notes
    if agent_name == "daily_briefing":
        return ("Run today's daily inbox briefing now, following your required steps.", [])
    if agent_name == "weekly_rule_suggestions":
        return (
            "Review this week's inbox activity now and email your VIP rule suggestions, "
            "following your required steps.",
            [],
        )
    return ("Run now.", [])


def _post_chat(agent_name: str, prompt: str) -> dict:
    """POST to the agent's built-in /chat endpoint and return the parsed result.

    Returns the runtime's JSON: {session_id, response, tool_calls}. The call is
    synchronous: it blocks until the agent finishes, so the result reflects every
    tool the agent actually ran.
    """
    data = json.dumps({"prompt": prompt}).encode("utf-8")
    req = urllib.request.Request(
        chat_url(agent_name),
        data=data,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=CHAT_TIMEOUT_SEC) as response:
        raw = response.read().decode("utf-8", errors="replace")
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"response": raw, "tool_calls": []}


def _tool_failed(call: dict) -> bool:
    """Best-effort detection of a failed tool call from its recorded result."""
    result = call.get("result")
    if result is None:
        return False
    text = result if isinstance(result, str) else json.dumps(result)
    return bool(re.search(r"\b(error|failed|exception|forbidden|unauthorized|invalidrecipient)\b", text, re.IGNORECASE))


def _render_result(agent_name: str, result: dict, elapsed: float, forced_through_partial: bool) -> None:
    """Print exactly what the agent did: tool calls grouped by name, then its summary."""
    tool_calls = result.get("tool_calls") or []
    response_text = (result.get("response") or "").strip()

    print(f"\n✔ Done ({elapsed:0.1f}s).")

    if tool_calls:
        counts: dict[str, list[int]] = {}
        for call in tool_calls:
            name = call.get("tool_name") or "(unknown)"
            ok, fail = counts.setdefault(name, [0, 0])
            if _tool_failed(call):
                counts[name][1] += 1
            else:
                counts[name][0] += 1
        print(f"  Tool calls ({len(tool_calls)} total):")
        for name, (ok, fail) in counts.items():
            suffix = f", {fail} failed" if fail else ""
            print(f"    - {name} ×{ok + fail}{suffix}")
        any_fail = any(fail for _, (ok, fail) in counts.items())
    else:
        print("  Tool calls: none.")
        any_fail = False

    if response_text:
        print("\n  Agent summary:")
        for line in response_text.splitlines() or [response_text]:
            print(f"    {line}")

    breaker = re.search(r"maximum consecutive function call errors", response_text, re.IGNORECASE)
    if breaker or any_fail:
        print("\n  ⚠ Some tool calls failed. Common causes:")
        print("    - reply/briefing sent to a placeholder recipient (set MAILBOX_OWNER_EMAIL)")
        print("    - Teams post with empty TEAMS_TEAM_ID / TEAMS_CHANNEL_ID")
        print("    - 3 consecutive failures trip the runtime's circuit breaker, which")
        print("      stops further tool calls but still returns a (partial) summary.")
        print("    Run `uv run func start --verbose` to see the exact connector error.")
    if forced_through_partial and not any_fail:
        print("\n  Note: you forced through with a placeholder recipient; delivery is a no-op.")
    print()


def trigger_agent(agent_name: str, mode_icon: str, mode_label: str = "") -> None:
    is_offline = mode_icon == "🟡" and "Offline" in mode_label
    forced_through_partial = False

    if not is_offline:
        required_missing, conditional_missing = _missing_for(agent_name)

        if required_missing:
            names = ", ".join(required_missing)
            print(f"\n⚠ Skipped: {agent_name} needs {names} but it's still a placeholder.")
            print("  The agent would call real M365 connectors with a placeholder recipient,")
            print("  which returns OK but delivers nothing. Output would look successful")
            print("  while nothing arrives in your inbox.")
            print()
            print("  Fix:")
            for k in required_missing:
                print(f"    - set {k} ({DEP_PURPOSE.get(k, 'used by this agent')}) in local.settings.json")
            print("    - Ctrl-C the `uv run func start` window and restart it.")
            print()
            answer = input("  Trigger anyway? (y/N): ").strip().lower()
            if answer != "y":
                print()
                return
            forced_through_partial = True
            print()
        elif conditional_missing and agent_name != "inbox_triage":
            names = ", ".join(conditional_missing)
            print(f"\nℹ Note: {agent_name} will run, but {names} is a placeholder.")
            print(f"  Any branch that needs it ({DEP_PURPOSE.get(conditional_missing[0], 'optional path')})")
            print("  will silently no-op. Other actions still work.")
            print()

    prompt, notes = _build_prompt(agent_name)
    for line in notes:
        print(line)
    if notes:
        print()

    print(f"→ Calling {agent_name} /chat (synchronous, up to {CHAT_TIMEOUT_SEC}s)…")
    start = time.monotonic()
    try:
        result = _post_chat(agent_name, prompt)
    except urllib.error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace").strip()
        print(f"\nError calling {agent_name} /chat: HTTP {exc.code}")
        if exc.code == 404:
            print("  The /chat endpoint is not registered. Add this to the agent's .agent.md")
            print("  frontmatter, then restart `uv run func start`:")
            print("      builtin_endpoints:")
            print("        chat_api: true")
        if details:
            print(f"  {details}")
        print()
        return
    except Exception as exc:
        print(f"\nError calling {agent_name} /chat: {exc}")
        print("Is the Functions host running with `uv run func start`?\n")
        return

    elapsed = time.monotonic() - start
    _render_result(agent_name, result, elapsed, forced_through_partial)


def show_recent_actions() -> None:
    if not LOG_PATH.exists():
        print(f"\nNo action log found at {LOG_PATH} yet.")
        print("Trigger an agent first; local fallback tools write actions there.\n")
        return

    lines = [line.strip() for line in LOG_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]
    print("\nLast 10 actions taken (offline-fallback log)")
    print("--------------------------------------------")
    if not lines:
        print("Action log is empty.\n")
        return
    for line in lines[-10:]:
        print(f"- {line}")
    print()


def print_menu(mode_icon: str, mode_label: str) -> None:
    print("M365 Inbox Agent. Local Test Client")
    print("====================================")
    print(f"Mode: {mode_icon} {mode_label}")
    if mode_icon == "🟡" and "Partial" in mode_label:
        print("      Run `azd env set MAILBOX_OWNER_EMAIL you@your-tenant.com`")
        print("      then `./infra/scripts/hydrate-local-settings.sh` to go fully live.")
    elif mode_icon == "🟡":
        print("      To go live: `azd env set MAILBOX_OWNER_EMAIL you@your-tenant.com`,")
        print("      then `./infra/scripts/hydrate-local-settings.sh`, then `./infra/scripts/authorize-connectors.sh`.")
    print()
    for key in ("1", "2", "3"):
        _, name, desc = AGENTS[key]
        print(f"{key}) {name:<26} {desc}")
    print("4) Show last 10 actions (offline log)")
    print("q) Quit")


def main() -> None:
    mode_icon, mode_label = detect_mode()
    while True:
        print_menu(mode_icon, mode_label)
        choice = input("\nSelect an option: ").strip().lower()
        if choice in ("q", "quit", "exit"):
            print("Goodbye!")
            break
        if choice in AGENTS:
            trigger_agent(AGENTS[choice][0], mode_icon, mode_label)
            # Re-detect mode after each run in case the user just authorized connectors.
            mode_icon, mode_label = detect_mode()
        elif choice == "4":
            show_recent_actions()
        else:
            print("\nChoose 1, 2, 3, 4, or q.\n")


if __name__ == "__main__":
    main()
