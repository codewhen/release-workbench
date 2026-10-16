"""Bash card specification."""

from __future__ import annotations

from typing import Any, ClassVar

from .base import OperationSpec, field


class BashSpec(OperationSpec):
    supports_retry = True
    kind, category, label, output = "bash", "External", "Bash", "object"
    defaults: ClassVar[dict[str, Any]] = {"code": "printf 'Hello workflow\n'", "capture": "text"}
    required = ("code",)
    fields: ClassVar[list[dict[str, Any]]] = [
        field("code", "Bash script", "code", advanced=True),
        field("capture", "Capture", "select", options=["text", "json"]),
    ]
