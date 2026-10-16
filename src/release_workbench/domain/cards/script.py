"""Script card specification."""

from __future__ import annotations

from typing import Any, ClassVar

from .base import OperationSpec, field


class ScriptSpec(OperationSpec):
    supports_retry = True
    kind, category, label, output = "script", "External", "Script file", "object"
    defaults: ClassVar[dict[str, Any]] = {
        "language": "python",
        "path": "",
        "arguments": [],
        "capture": "text",
    }
    required = ("path",)
    fields: ClassVar[list[dict[str, Any]]] = [
        field("language", "Language", "select", options=["python", "bash"]),
        field("path", "Script path"),
        field("arguments", "Arguments", "json", items="string", advanced=True),
        field("capture", "Capture", "select", options=["text", "json"], advanced=True),
    ]
