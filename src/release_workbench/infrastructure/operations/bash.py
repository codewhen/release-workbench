"""BashHandler external effect adapter."""

from __future__ import annotations

from pathlib import Path

from release_workbench.domain.models import Card

from .program import ProgramHandler


class BashHandler(ProgramHandler):
    kind = "bash"

    def arguments(self, card: Card, root: Path) -> list[str]:
        return ["bash", "-c", card.config["code"]]
