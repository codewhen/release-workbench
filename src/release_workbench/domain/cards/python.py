"""Python card specification."""

from __future__ import annotations

from typing import Any, ClassVar

from ..models import Card, Workflow
from .base import OperationSpec, field


class PythonSpec(OperationSpec):
    supports_retry = True
    kind, category, label, output = "python", "External", "Python", "json"
    defaults: ClassVar[dict[str, Any]] = {
        "code": 'print("Running Python")\nreturn inputs.get("value", True)',
        "returns": "json",
    }
    required = ("code",)
    fields: ClassVar[list[dict[str, Any]]] = [
        field("code", "Python statements", "code", advanced=True),
        field("returns", "Return type", "type"),
    ]

    def result_type(self, card: Card, workflow: Workflow | None = None) -> str:
        return str(card.config.get("returns", self.defaults.get("returns", self.output)))
