"""Variable card specification."""

from __future__ import annotations

from typing import Any, ClassVar

from ..models import Card, Workflow
from .base import OperationSpec, field


class VariableSpec(OperationSpec):
    kind, category, label, output = "variable", "Control flows", "Variable", "json"
    defaults: ClassVar[dict[str, Any]] = {
        "operation": "get",
        "name": "",
        "value": 0,
        "operator": "add",
    }
    required = ("name",)
    fields: ClassVar[list[dict[str, Any]]] = [
        field("operation", "Operation", "select", options=["get", "set", "update"]),
        field("name", "Global variable", "global"),
        field("value", "Value", "json", unless={"operation": "get"}),
        field(
            "operator",
            "Update",
            "select",
            options=["add", "subtract", "multiply", "append"],
            when={"operation": "update"},
        ),
    ]

    def result_type(self, card: Card, workflow: Workflow | None = None) -> str:
        return (
            str(workflow.globals.get(card.config.get("name", ""), {}).get("type", "json"))
            if workflow
            else "json"
        )
