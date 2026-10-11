"""Append-only audit trail for agent activity (output/audit_trail.json)."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
AUDIT_PATH = ROOT_DIR / "output" / "audit_trail.json"
MAX_AUDIT_CHARS = 2000


def _clip(value: Any) -> Any:
    """Shorten very long strings so the trail stays readable."""
    if isinstance(value, str) and len(value) > MAX_AUDIT_CHARS:
        return value[:MAX_AUDIT_CHARS] + f"... [{len(value) - MAX_AUDIT_CHARS} more chars]"
    if isinstance(value, dict):
        return {k: _clip(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_clip(v) for v in value]
    return value


def load_events() -> list[dict]:
    if not AUDIT_PATH.exists() or AUDIT_PATH.stat().st_size == 0:
        return []
    data = json.loads(AUDIT_PATH.read_text())
    return data if isinstance(data, list) else [data]


def append_event(event: str, **details: Any) -> None:
    """Append one event to the trail. Earlier entries are never removed or rewritten."""
    entry = {"timestamp": datetime.now(timezone.utc).isoformat(timespec="milliseconds"), "event": event}
    entry.update(_clip(details))
    events = load_events()
    events.append(entry)
    AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = AUDIT_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(events, indent=2, default=str))
    os.replace(tmp, AUDIT_PATH)
