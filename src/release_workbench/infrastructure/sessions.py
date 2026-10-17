"""Persist local browser sessions so a server restart does not strand open drafts."""

from __future__ import annotations

import json
import secrets
from pathlib import Path

from .documents import atomic_write


class LocalSessions:
    def __init__(self, path: Path):
        if not path.exists():
            atomic_write(path, json.dumps([secrets.token_urlsafe(32)]))
        tokens = json.loads(path.read_text(encoding="utf-8"))
        if (
            not isinstance(tokens, list)
            or not tokens
            or not all(isinstance(value, str) and len(value) >= 32 for value in tokens)
        ):
            raise ValueError("Invalid local browser session file; restore it before restarting.")
        path.chmod(0o600)
        self.token: str = tokens[0]
        self._tokens: tuple[str, ...] = tuple(tokens)

    def accepts(self, token: str | None) -> bool:
        return token is not None and any(
            secrets.compare_digest(token.encode(), candidate.encode()) for candidate in self._tokens
        )
