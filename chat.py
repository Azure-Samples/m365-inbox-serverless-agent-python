"""Local test client for the M365 Inbox Agent function app.

Triggers an agent via the Functions admin endpoint, then polls
`out/read-log.txt` for new entries so you can see what the agent actually
did (tool calls, files written) without staring at the host log.

Shows a mode banner at the top: 🟢 Live (real Outlook/Teams MCP endpoints
configured in local.settings.json) vs 🟡 Offline (sample-data fallback).
"""

import json
import os
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

AGENTS = {
    "1": ("inbox_triage", "inbox-triage", "Triage inbox now (classify VIP / incident / FYI; reply or alert)"),
    "2": ("daily_briefing", "daily-briefing", "Send today's briefing to MAILBOX_OWNER_EMAIL"),
    "3": ("weekly_rule_suggestions", "weekly-rule-suggestions", "Propose rule updates based on recent decisions"),
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


def detect_mode() -> tuple[str, str]:
    """Return (icon, label) describing whether the host is wired to real M365."""
    values = _read_local_settings()
    outlook = (values.get("OUTLOOK_MCP_ENDPOINT") or os.environ.get("OUTLOOK_MCP_ENDPOINT") or "").strip()
    mailbox = (values.get("MAILBOX_OWNER_EMAIL") or os.environ.get("MAILBOX_OWNER_EMAIL") or "").strip()
    if outlook and not outlook.startswith("<") and mailbox and not mailbox.startswith("<"):
        return ("🟢", f"Live M365  ({mailbox})")
    if outlook and not outlook.startswith("<"):
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


def trigger_agent(agent_name: str, mode_icon: str) -> None:
    log_offset = _log_byte_size()
    files_before = _snapshot_out()
    is_live = mode_icon == "🟢"

    payload = {"input": json.dumps({"source": "chat.py", "mode": "live" if is_live else "sample-data"})}
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

    print(f"\n✔ Done ({elapsed:0.1f}s). {seen_lines} new action(s); {len(new_files)} new file(s) in out/.")
    for path in new_files:
        size = (OUT_DIR / path).stat().st_size
        print(f"    + out/{path} ({size}B)")
    if seen_lines == 0 and not new_files:
        if is_live:
            print("  (Live mode: actions go to real Outlook/Teams, not read-log.txt.")
            print("   Check the `func start` window for [TOOL] entries, or your inbox/Teams channel.)")
        else:
            print("  (Agent ran but produced no actions or files. Check the func start log for [TOOL] entries.)")
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
            trigger_agent(AGENTS[choice][0], mode_icon)
            # Re-detect mode after each run in case the user just authorized connectors.
            mode_icon, mode_label = detect_mode()
        elif choice == "4":
            show_recent_actions()
        else:
            print("\nChoose 1, 2, 3, 4, or q.\n")


if __name__ == "__main__":
    main()
