"""Local test client for the M365 Inbox Agent function app.

Triggers an agent via the Functions admin endpoint, then polls
`out/read-log.txt` for new entries so you can see what the agent actually
did (tool calls, files written) without staring at the host log.
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

AGENTS = {
    "1": ("inbox_triage", "Trigger inbox-triage now (with sample-data)"),
    "2": ("daily_briefing", "Trigger daily-briefing now"),
    "3": ("weekly_rule_suggestions", "Trigger weekly-rule-suggestions now"),
}


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


def trigger_agent(agent_name: str) -> None:
    log_offset = _log_byte_size()
    files_before = _snapshot_out()

    payload = {"input": json.dumps({"source": "chat.py", "mode": "sample-data"})}
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
            print(f"\n→ Triggered {agent_name} (HTTP {response.status}). Waiting for activity (up to {POLL_TIMEOUT_SEC}s)…\n")
    except urllib.error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace").strip()
        print(f"\nError triggering {agent_name}: HTTP {exc.code}")
        if details:
            print(details)
        print("Is the Functions host running with `func5 run`?\n")
        return
    except Exception as exc:
        print(f"\nError triggering {agent_name}: {exc}")
        print("Start the local host with `func5 run`, then try again.\n")
        return

    # Tail the action log for new lines + watch out/ for new files.
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
        print("  (Agent ran but produced no actions or files. Check the func5 run log for [TOOL] entries.)")
    print()


def show_recent_actions() -> None:
    if not LOG_PATH.exists():
        print(f"\nNo action log found at {LOG_PATH} yet.")
        print("Trigger an agent first; local fallback tools write actions there.\n")
        return

    lines = [line.strip() for line in LOG_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]
    print("\nLast 10 actions taken")
    print("---------------------")
    if not lines:
        print("Action log is empty.\n")
        return
    for line in lines[-10:]:
        print(f"- {line}")
    print()


def print_menu() -> None:
    print("M365 Inbox Agent — Local Test Client")
    print("====================================")
    for key in ("1", "2", "3"):
        print(f"{key}) {AGENTS[key][1]}")
    print("4) Show last 10 actions taken")
    print("q) Quit")


def main() -> None:
    while True:
        print_menu()
        choice = input("\nSelect an option: ").strip().lower()
        if choice in ("q", "quit", "exit"):
            print("Goodbye!")
            break
        if choice in AGENTS:
            trigger_agent(AGENTS[choice][0])
        elif choice == "4":
            show_recent_actions()
        else:
            print("\nChoose 1, 2, 3, 4, or q.\n")


if __name__ == "__main__":
    main()
