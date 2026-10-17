"""Program card specification."""

from __future__ import annotations

from typing import Any, ClassVar

from .base import OperationSpec, field


class ProgramSpec(OperationSpec):
    supports_retry = True
    kind, category, label, output = "program", "External", "Program", "object"
    defaults: ClassVar[dict[str, Any]] = {"argv": ["python3", "--version"], "capture": "text"}
    required = ("argv",)
    fields: ClassVar[list[dict[str, Any]]] = [
        field("argv", "Program and arguments", "json", items="string"),
        field("capture", "Capture", "select", options=["text", "json"], advanced=True),
    ]
