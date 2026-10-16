"""CheckPath card specification."""

from __future__ import annotations

from typing import Any, ClassVar

from .base import OperationSpec, field


class CheckPathSpec(OperationSpec):
    supports_retry = True
    kind, category, label, output = "check_path", "I/O", "Check path", "boolean"
    defaults: ClassVar[dict[str, Any]] = {"path": ".", "type": "exists"}
    required = ("path",)
    fields: ClassVar[list[dict[str, Any]]] = [
        field("path", "Path"),
        field("type", "Check", "select", options=["exists", "file", "directory"]),
    ]
