"""Manual card specification."""

from __future__ import annotations

from typing import Any, ClassVar

from ..models import Card, Workflow
from .base import OperationSpec, field


class ManualSpec(OperationSpec):
    kind, category, label, output = (
        "manual",
        "Interventions",
        "Manual decision / approval",
        "json",
    )
    defaults: ClassVar[dict[str, Any]] = {
        "mode": "decision",
        "instructions": "Record what you checked.",
    }
    fields: ClassVar[list[dict[str, Any]]] = [
        field("mode", "Mode", "select", options=["decision", "approval"]),
        field("instructions", "Instructions", "textarea"),
    ]

    def result_type(self, card: Card, workflow: Workflow | None = None) -> str:
        return "void" if card.config.get("mode", "decision") == "approval" else "boolean"
