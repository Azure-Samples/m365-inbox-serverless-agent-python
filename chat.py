"""Local test client for the M365 Inbox Agent function app."""

import json
import os
import urllib.error
import urllib.request
from pathlib import Path

BASE_URL = os.environ.get("AGENT_URL", "http://localhost:7071").rstrip("/")
FUNCTION_KEY = os.environ.get("FUNCTION_KEY", "")
LOG_PATH = Path(os.environ.get("ACTION_LOG_PATH", "out/read-log.txt"))

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


def trigger_agent(agent_name: str) -> None:
    payload = {
        "input": json.dumps(
            {
                "source": "chat.py",
                "mode": "sample-data",
                "sampleDataPath": "sample-data/inbox.json",
            }
        )
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        admin_url(agent_name),
        data=data,
        method="POST",
        headers={"Content-Type": "application/json"},
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            body = response.read().decode("utf-8").strip()
            print(f"\nTriggered {agent_name} ({response.status}).")
            if body:
                print(body)
            print()
    except urllib.error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace").strip()
        print(f"\nError triggering {agent_name}: HTTP {exc.code}")
        if details:
            print(details)
        print("Is the Functions host running with `func start`?\n")
    except Exception as exc:  # pragma: no cover - friendly CLI boundary
        print(f"\nError triggering {agent_name}: {exc}")
        print("Start the local host with `func start`, then try again.\n")


def show_recent_actions() -> None:
    if not LOG_PATH.exists():
        print(f"\nNo action log found at {LOG_PATH} yet.")
        print("Trigger an agent first; local fallback tools write actions there.\n")
        return

    lines = [line.strip() for line in LOG_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]
    print("\nLast 5 actions taken")
    print("--------------------")
    if not lines:
        print("Action log is empty.\n")
        return
    for line in lines[-5:]:
        print(f"- {line}")
    print()


def print_menu() -> None:
    print("M365 Inbox Agent — Local Test Client")
    print("====================================")
    for key in ("1", "2", "3"):
        print(f"{key}) {AGENTS[key][1]}")
    print("4) Show last 5 actions taken")
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
