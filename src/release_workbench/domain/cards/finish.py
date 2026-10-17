"""Finish card specification."""

from __future__ import annotations

from typing import Any, ClassVar

from ..models import Card, Workflow
from .base import TerminalSpec, field


class FinishSpec(TerminalSpec):
    kind, category, label, output = "finish", "Functions", "Finish", "json"
    defaults: ClassVar[dict[str, Any]] = {"returns": "void", "value": None}
    fields: ClassVar[list[dict[str, Any]]] = [
        field("returns", "Workflow return type", "type"),
        field("value", "Workflow output", "json"),
    ]

    def result_type(self, card: Card, workflow: Workflow | None = None) -> str:
        return str(card.config.get("returns", self.defaults.get("returns", self.output)))
