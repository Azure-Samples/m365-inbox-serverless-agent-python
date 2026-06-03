"""Shared loud-and-clear tool logging.

Each `@tool` function calls `tool_log(name, args, result_summary, offline=True)`
so a single grep for `[TOOL]` shows the full agent flow in the host log.
"""

import logging
from typing import Any


def tool_log(name: str, args: dict[str, Any], result: str, *, offline: bool = True) -> None:
    """Emit a single high-signal line per tool call.

    Example:
        [TOOL] list_inbox(since_minutes=60, top=10) -> 5 sample messages [OFFLINE]
    """
    arg_str = ", ".join(f"{k}={_short(v)}" for k, v in args.items())
    mode = " [OFFLINE]" if offline else ""
    logging.info("[TOOL] %s(%s) -> %s%s", name, arg_str, result, mode)


def _short(value: Any, limit: int = 60) -> str:
    s = repr(value)
    return s if len(s) <= limit else s[: limit - 1] + "…"
