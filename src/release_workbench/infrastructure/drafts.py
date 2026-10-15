"""Recover a submitted browser draft without changing the saved workflow."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .documents import atomic_write, render_document


class DraftStore:
    def __init__(self, directory: Path):
        self.directory = directory

    def save(self, key: str, raw: dict[str, Any], current: dict[str, Any]) -> None:
        value = {
            "base_revision": current["revision"],
            "workflow": raw,
            "yaml": render_document(raw, current["yaml"]),
        }
        atomic_write(self.directory / (key + ".json"), json.dumps(value, allow_nan=False))

    def matching(self, key: str, revision: str) -> dict[str, Any] | None:
        file = self.directory / (key + ".json")
        if not file.exists():
            return None
        value: dict[str, Any] = json.loads(file.read_text())
        return value if value.get("base_revision") == revision else None

    def clear(self, key: str) -> None:
        (self.directory / (key + ".json")).unlink(missing_ok=True)
