import json
import logging
import os
import pathlib
import sys

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
    this loud at host startup so users know what's about to happen. We print to
    stderr (not logging) because the Functions Python worker silences arbitrary
    loggers before our module-level code surfaces.
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

    banner = []
    banner.append("=" * 78)
    banner.append(f"PARTIAL CONFIG: Outlook MCP is wired up but {len(issues)} setting(s) are placeholders.")
    banner.append("Agents will call real M365 connectors with placeholder values,")
    banner.append("which silently no-op (no email arrives, no Teams post lands).")
    banner.append("")
    for key, purpose in issues:
        banner.append(f"  - {key}   (needed for {purpose})")
    banner.append("")
    banner.append("Fix: edit local.settings.json, or run:")
    for key, _ in issues:
        banner.append(f"    azd env set {key} <real-value>")
    banner.append("Then re-run `./infra/scripts/hydrate-local-settings.sh` and restart `func5 run`.")
    banner.append("=" * 78)
    print("\n".join(banner), file=sys.stderr, flush=True)


_warn_on_partial_config()


def _patch_mcp_http_read_timeout() -> None:
    """Work around a hang in azurefunctions-agents-runtime's MCP HTTP client.

    `azure_functions_agents.discovery.mcp._build_http_client` creates the httpx
    client with httpx's default 5s read timeout. MCP streamable-HTTP tool results
    are delivered over a Server-Sent-Events stream; an operation whose response
    streams (for example the Teams connector's `PostMessageToConversation`) needs
    no read timeout. With the 5s cap the SSE read stalls, the JSON-RPC response is
    never dispatched, and the agent call hangs indefinitely. Small/immediate JSON
    responses (e.g. an @mention or Outlook `SendEmailV2`) are unaffected, which is
    why this looks like "Teams posting randomly hangs".

    This is a workaround for the preview runtime; tracked upstream and unfixed on
    main as of azurefunctions-agents-runtime 0.1.0b1:
    https://github.com/Azure/azure-functions-agents-runtime/issues/63
    Remove this shim once `_build_http_client` sets an SSE-friendly read timeout.
    """
    try:
        import httpx
        from azure_functions_agents.discovery import mcp as _mcp

        if getattr(_mcp._build_http_client, "_read_timeout_patched", False):
            return
        _orig = _mcp._build_http_client

        def _patched(*args, **kwargs):  # type: ignore[no-untyped-def]
            client = _orig(*args, **kwargs)
            if client is not None:
                client.timeout = httpx.Timeout(30.0, read=None)
            return client

        _patched._read_timeout_patched = True  # type: ignore[attr-defined]
        _mcp._build_http_client = _patched
    except Exception as exc:  # pragma: no cover - never block host startup
        print(f"[startup] MCP read-timeout shim not applied: {exc}", file=sys.stderr, flush=True)


_patch_mcp_http_read_timeout()

from azure_functions_agents import create_function_app  # noqa: E402

app = create_function_app()
