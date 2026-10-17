"""Join card specification."""

from __future__ import annotations

from typing import Any, ClassVar

from .base import OperationSpec, field


class JoinSpec(OperationSpec):
    kind, category, label, output = "join", "Control flows", "Join", "object"
    defaults: ClassVar[dict[str, Any]] = {"parallel": ""}
    required = ("parallel",)
    fields: ClassVar[list[dict[str, Any]]] = [field("parallel", "Parallel card", "text")]
