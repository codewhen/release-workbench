"""Call card specification."""

from __future__ import annotations

from typing import Any, ClassVar

from ..models import Card, Workflow
from .base import OperationSpec, field


class CallSpec(OperationSpec):
    holds_slot = False
    kind, category, label, output = "call", "Functions", "Call function", "json"
    defaults: ClassVar[dict[str, Any]] = {"function": ""}
    required = ("function",)
    fields: ClassVar[list[dict[str, Any]]] = [field("function", "Function", "function")]

    def result_type(self, card: Card, workflow: Workflow | None = None) -> str:
        return (
            str(workflow.functions.get(card.config.get("function", ""), {}).get("returns", "json"))
            if workflow
            else "json"
        )
