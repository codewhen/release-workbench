"""Calculate card specification."""

from __future__ import annotations

from typing import Any, ClassVar

from .base import OperationSpec, field


class CalculateSpec(OperationSpec):
    kind, category, label, output = "calculate", "Control flows", "Calculate", "json"
    defaults: ClassVar[dict[str, Any]] = {"operator": "add", "left": 0, "right": 1}
    fields: ClassVar[list[dict[str, Any]]] = [
        field(
            "operator",
            "Operation",
            "select",
            options=[
                "add",
                "subtract",
                "multiply",
                "divide",
                "equals",
                "not_equals",
                "less_than",
                "greater_than",
                "and",
                "or",
                "not",
            ],
        ),
        field("left", "First value", "json"),
        field("right", "Second value", "json", unless={"operator": "not"}),
    ]
