"""Shared offline action logging helpers."""


import datetime as dt
from pathlib import Path


def append_action(message: str) -> Path:
    """Append a timestamped offline action record and return the log path."""
    out_dir = Path(__file__).resolve().parent.parent / "out"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "read-log.txt"
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"[{dt.datetime.now(dt.UTC).isoformat()}] {message}\n")
    return path
