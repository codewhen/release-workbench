"""If card specification."""

from __future__ import annotations

from typing import Any, ClassVar

from ..models import Card
from .base import CardSpec, field


class IfSpec(CardSpec):
    holds_slot = False
    kind, category, label, output = "if", "Control flows", "If / Else", "boolean"
    defaults: ClassVar[dict[str, Any]] = {"function": ""}
    required = ("function",)
    fields: ClassVar[list[dict[str, Any]]] = [
        field("function", "Condition function", "function", returns="boolean")
    ]

    def flow_outputs(self, card: Card) -> tuple[str, ...]:
        return ("true", "false")
