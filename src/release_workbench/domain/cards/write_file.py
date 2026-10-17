"""WriteFile card specification."""

from __future__ import annotations

from typing import Any, ClassVar

from .base import OperationSpec, field


class WriteFileSpec(OperationSpec):
    supports_retry = True
    kind, category, label, output = "write_file", "I/O", "Write file", "object"
    defaults: ClassVar[dict[str, Any]] = {
        "path": "",
        "format": "text",
        "value": "",
        "overwrite": False,
    }
    required = ("path",)
    fields: ClassVar[list[dict[str, Any]]] = [
        field("path", "File path"),
        field("format", "Format", "select", options=["text", "json"]),
        field("value", "Content", "json", advanced=True),
        field("overwrite", "Overwrite existing", "boolean", advanced=True),
    ]
