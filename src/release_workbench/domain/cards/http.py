"""Http card specification."""

from __future__ import annotations

from typing import Any, ClassVar

from .base import OperationSpec, field


class HttpSpec(OperationSpec):
    supports_retry = True
    kind, category, label, output = "http", "I/O", "HTTP request", "object"
    defaults: ClassVar[dict[str, Any]] = {"method": "GET", "url": "", "headers": {}, "body": None}
    required = ("url",)
    fields: ClassVar[list[dict[str, Any]]] = [
        field(
            "method",
            "Method",
            "select",
            options=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD"],
        ),
        field("url", "URL"),
        field("headers", "Headers", "json", advanced=True),
        field("body", "JSON body", "json", advanced=True),
    ]
