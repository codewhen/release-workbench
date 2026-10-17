"""Locate compatible, completed evidence after a dashboard restart."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from release_workbench.application.start_context import compatible


def latest_checkpoint(storage: Path, fingerprint: str) -> dict[str, Any] | None:
    latest: dict[str, Any] | None = None
    for file in storage.rglob("summary.json"):
        if file.is_symlink() or not file.resolve().is_relative_to(storage.resolve()):
            continue
        try:
            state = json.loads(file.read_text(encoding="utf-8"))
            if not isinstance(state, dict) or state.get("status") not in {
                "passed",
                "failed",
                "cancelled",
                "blocked",
            }:
                continue
            if not compatible(state, fingerprint):
                continue
            if latest is None or state.get("finished", 0) > latest.get("finished", 0):
                latest = state
        except (OSError, ValueError, KeyError, TypeError):
            continue
    return latest
