"""Local test client for the M365 Inbox Agent function app.

Triggers an agent via the Functions admin endpoint, then polls
`out/read-log.txt` for new entries so you can see what the agent actually
did (tool calls, files written) without staring at the host log.

Shows a mode banner at the top: 🟢 Live (real Outlook/Teams MCP endpoints
configured in local.settings.json) vs 🟡 Offline (sample-data fallback).
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
OUT_DIR = Path(os.environ.get("OUT_DIR", "out"))
POLL_TIMEOUT_SEC = int(os.environ.get("POLL_TIMEOUT_SEC", "60"))
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


def admin_url(agent_name: str) -> str:
    url = f"{BASE_URL}/admin/functions/{agent_name}"
    if FUNCTION_KEY:
        url += f"?code={FUNCTION_KEY}"
    return url


def _snapshot_out() -> set[str]:
    """Return relative paths of files currently in out/."""
    if not OUT_DIR.exists():
        return set()
    return {str(p.relative_to(OUT_DIR)) for p in OUT_DIR.rglob("*") if p.is_file()}


def _log_byte_size() -> int:
    return LOG_PATH.stat().st_size if LOG_PATH.exists() else 0


_TEAMS_TRIGGERING_RX = re.compile(r"urgent|p1\b|incident|escalat|outage", re.IGNORECASE)


def _sample_onnewemail_payload(limit: int = 3, exclude_teams_triggers: bool = False) -> list[dict]:
    """Build an OnNewEmailV3-shaped payload from sample-data/inbox/*.json.

    inbox_triage is a connector_trigger; firing it from the admin endpoint
    sends no payload, so the agent has nothing to triage. We synthesize the
    first few sample emails into the shape the agent expects ('a list of email
    objects with fields such as Id, Subject, From, To, BodyPreview, Body,
    Importance, HasAttachments, ConversationId').

    When TEAMS_* settings are placeholders, we drop emails whose subject would
    obviously route to a Teams alert (urgent / P1 / incident / outage). Each
    failed Teams call counts against the agent runtime's 3-error circuit
    breaker, which would otherwise abort the run after 3 VIP-flavored samples.
    """
    if not SAMPLE_INBOX_DIR.is_dir():
        return []
    emails: list[dict] = []
    for f in sorted(SAMPLE_INBOX_DIR.glob("*.json")):
        try:
            graph = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        subject = graph.get("subject", "") or ""
        if exclude_teams_triggers and _TEAMS_TRIGGERING_RX.search(subject):
            continue
        from_addr = graph.get("from", {}).get("emailAddress", {})
        to_list = graph.get("toRecipients", [])
        body = graph.get("body", {}).get("content", "") or ""
        emails.append({
            "Id": graph.get("id", ""),
            "Subject": subject,
            "From": from_addr.get("address", ""),
            "To": ";".join(r.get("emailAddress", {}).get("address", "") for r in to_list),
            "BodyPreview": body[:200],
            "Body": body,
            "Importance": graph.get("importance", "normal"),
            "HasAttachments": graph.get("hasAttachments", False),
            "ConversationId": graph.get("conversationId", graph.get("id", "")),
        })
        if len(emails) >= limit:
            break
    return emails


def _build_input(agent_name: str, is_live: bool) -> tuple[str, str]:
    """Return (input_payload_json_string, hint_for_user).

    inbox_triage gets a synthesized sample-inbox payload so the agent has
    something to triage when run from the admin endpoint. Other agents get a
    small marker so the func host trace shows where the run came from.
    """
    if agent_name == "inbox_triage":
        _, teams_missing = _missing_for("inbox_triage")
        exclude_teams = bool(teams_missing)
        emails = _sample_onnewemail_payload(limit=3, exclude_teams_triggers=exclude_teams)
        if emails:
            subjects = ", ".join(repr(e["Subject"][:48]) for e in emails)
            if exclude_teams:
                hint = (
                    f"  Sending {len(emails)} non-Teams-triggering sample email(s) from {SAMPLE_INBOX_DIR}/:\n"
                    f"    {subjects}\n"
                    "    (VIP / urgent / incident samples skipped: with TEAMS_* placeholders, each\n"
                    "    Teams call would fail and trip the agent's 3-error circuit breaker.)"
                )
            else:
                hint = f"  Sending {len(emails)} sample email(s) as the OnNewEmailV3 payload (from {SAMPLE_INBOX_DIR}/)."
            return json.dumps(emails), hint
        hint = (
            "  ⚠ No sample emails to send (sample-data/inbox/ is empty, or every sample matched\n"
            "    a Teams-triggering filter). inbox_triage will receive an empty payload and\n"
            "    report 'Processed 0 messages'."
        )
        return json.dumps([]), hint
    return (
        json.dumps({"source": "chat.py", "mode": "live" if is_live else "sample-data"}),
        "",
    )


def trigger_agent(agent_name: str, mode_icon: str, mode_label: str = "") -> None:
    is_live = mode_icon == "🟢"
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
        elif conditional_missing:
            names = ", ".join(conditional_missing)
            print(f"\nℹ Note: {agent_name} will run, but {names} is a placeholder.")
            print(f"  Any branch that needs it ({DEP_PURPOSE.get(conditional_missing[0], 'optional path')})")
            print("  will silently no-op. Other actions still work.")
            print()

    log_offset = _log_byte_size()
    files_before = _snapshot_out()

    input_str, input_hint = _build_input(agent_name, is_live)
    payload = {"input": input_str}
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        admin_url(agent_name),
        data=data,
        method="POST",
        headers={"Content-Type": "application/json"},
    )

    start = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            print(f"\n→ Triggered {agent_name} (HTTP {response.status}). Waiting for activity (up to {POLL_TIMEOUT_SEC}s)…")
            if input_hint:
                print(input_hint)
            if is_live:
                print("  Live mode: action goes to real Outlook/Teams. Watch the `func start` terminal for the agent's trace.")
            print()
    except urllib.error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace").strip()
        print(f"\nError triggering {agent_name}: HTTP {exc.code}")
        if details:
            print(details)
        print("Is the Functions host running with `uv run func start`?\n")
        return
    except Exception as exc:
        print(f"\nError triggering {agent_name}: {exc}")
        print("Start the local host with `uv run func start`, then try again.\n")
        return

    # Tail the action log for new lines + watch out/ for new files.
    # In live mode the agent calls real MCP servers and writes nothing to
    # read-log.txt; we still tail in case any local fallback path runs, but
    # the authoritative trace is in the `func start` window.
    seen_lines = 0
    deadline = start + POLL_TIMEOUT_SEC
    last_size = log_offset
    idle_since = time.monotonic()

    while time.monotonic() < deadline:
        time.sleep(1.0)
        size = _log_byte_size()
        if size > last_size and LOG_PATH.exists():
            with LOG_PATH.open("r", encoding="utf-8") as fh:
                fh.seek(last_size)
                chunk = fh.read()
            for line in chunk.splitlines():
                if line.strip():
                    print(f"  ▸ {line}")
                    seen_lines += 1
            last_size = size
            idle_since = time.monotonic()
        elif seen_lines and (time.monotonic() - idle_since) > 8:
            break

    elapsed = time.monotonic() - start
    files_after = _snapshot_out()
    new_files = sorted(files_after - files_before)

    is_offline = mode_icon == "🟡" and "Offline" in (mode_label or "")
    print(f"\n✔ Done ({elapsed:0.1f}s).")

    if is_offline:
        print(f"  Offline mode: {seen_lines} new action(s) in {LOG_PATH}; {len(new_files)} new file(s) in out/.")
        for path in new_files:
            size = (OUT_DIR / path).stat().st_size
            print(f"    + out/{path} ({size}B)")
        if seen_lines == 0 and not new_files:
            print("  (No actions logged. Check the `func start` window for errors.)")
    else:
        print(f"  {mode_icon} {mode_label or 'Live'}: tool calls went to real connectors, not {LOG_PATH}.")
        print(f"  Look at the `func start` window. Every 'Function name: <tool>' line is one")
        print(f"  connector call the agent made. Common things to look for:")
        print(f"    - 'Function name: match_rule' = classification step (one per email)")
        print(f"    - 'Function name: office365_SendEmailV2' = reply or briefing email sent")
        print(f"    - 'Function name: teams_PostMessageToChannelV3' = Teams alert posted")
        print(f"    - 'Maximum consecutive function call errors reached (3)' = circuit breaker tripped;")
        print(f"      the run continued but stopped calling tools. Usually means placeholder settings.")
        if new_files:
            print(f"  Also wrote {len(new_files)} file(s) to out/:")
            for path in new_files:
                size = (OUT_DIR / path).stat().st_size
                print(f"    + out/{path} ({size}B)")
        if forced_through_partial:
            print(f"  Note: you forced through with placeholder settings, so any recipient-bound")
            print(f"  call hit a fake address. Connector may have logged a send error.")
    print()


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
