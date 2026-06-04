import json
import logging
import os
import pathlib

# Suppress noisy SDK HTTP traces so [TOOL] lines stand out in `func5 run` output.
# These three account for ~95% of the per-invocation log volume.
for noisy in (
    "azure.core.pipeline.policies.http_logging_policy",
    "azure.identity",
    "azure.identity.aio",
    "httpx",
    "httpcore",
    "urllib3",
):
    logging.getLogger(noisy).setLevel(logging.WARNING)


def _is_placeholder(value: str | None) -> bool:
    """True when a setting is empty or still a `<...>` / `$VAR` placeholder."""
    if not value:
        return True
    stripped = value.strip()
    return stripped == "" or stripped.startswith("<") or stripped.startswith("$")


def _warn_on_partial_config() -> None:
    """Detect the 'Outlook MCP wired but mailbox/teams placeholders' trap.

    In that state, the agent successfully calls real connectors with a literal
    `<your-mailbox@example.com>` recipient. The connector returns OK on a no-op
    delivery, the function reports success, and nothing reaches the inbox. Make
    this loud at host startup so users know what's about to happen.
    """
    settings_path = pathlib.Path("local.settings.json")
    if not settings_path.exists():
        return
    try:
        values = json.loads(settings_path.read_text(encoding="utf-8")).get("Values", {})
    except (OSError, json.JSONDecodeError):
        return

    def _resolve(key: str) -> str:
        return (values.get(key) or os.environ.get(key) or "").strip()

    if _is_placeholder(_resolve("OUTLOOK_MCP_ENDPOINT")):
        return

    issues: list[tuple[str, str]] = []
    for key, purpose in (
        ("MAILBOX_OWNER_EMAIL", "Outlook send-mail recipient"),
        ("TEAMS_TEAM_ID", "Teams channel posts (urgent alerts)"),
        ("TEAMS_CHANNEL_ID", "Teams channel posts (urgent alerts)"),
    ):
        if _is_placeholder(_resolve(key)):
            issues.append((key, purpose))

    if not issues:
        return

    log = logging.getLogger("m365.config")
    log.warning("=" * 78)
    log.warning(
        "PARTIAL CONFIG: Outlook MCP is wired up but %d setting(s) are placeholders.",
        len(issues),
    )
    log.warning("Agents will call real M365 connectors with placeholder values,")
    log.warning("which silently no-op (no email arrives, no Teams post lands).")
    log.warning("")
    for key, purpose in issues:
        log.warning("  - %s   (needed for %s)", key, purpose)
    log.warning("")
    log.warning("Fix: edit local.settings.json, or run:")
    for key, _ in issues:
        log.warning("    azd env set %s <real-value>", key)
    log.warning("Then re-run `./infra/scripts/hydrate-local-settings.sh` and restart `uv run func start`.")
    log.warning("=" * 78)


_warn_on_partial_config()

from azure_functions_agents import create_function_app  # noqa: E402

app = create_function_app()
