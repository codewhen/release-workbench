"""Return card specification."""

from __future__ import annotations

from typing import Any, ClassVar

from ..models import Card, Workflow
from .base import TerminalSpec, field


class ReturnSpec(TerminalSpec):
    kind, category, label, output = "return", "Functions", "Return", "json"
    defaults: ClassVar[dict[str, Any]] = {"value": None, "handled": False, "returns": "json"}
    fields: ClassVar[list[dict[str, Any]]] = [
        field("returns", "Value type", "type"),
        field("value", "Return value", "json"),
        field("handled", "Error handled", "boolean", advanced=True),
    ]

    def result_type(self, card: Card, workflow: Workflow | None = None) -> str:
        return str(card.config.get("returns", self.defaults.get("returns", self.output)))
