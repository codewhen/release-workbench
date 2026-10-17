"""ReadFile card specification."""

from __future__ import annotations

from typing import Any, ClassVar

from .base import OperationSpec, field


class ReadFileSpec(OperationSpec):
    supports_retry = True
    kind, category, label, output = "read_file", "I/O", "Read file", "json"
    defaults: ClassVar[dict[str, Any]] = {"path": "", "format": "text"}
    required = ("path",)
    fields: ClassVar[list[dict[str, Any]]] = [
        field("path", "File path"),
        field("format", "Format", "select", options=["text", "json"]),
    ]
