"""Wait card specification."""

from __future__ import annotations

from typing import Any, ClassVar

from .base import OperationSpec, field


class WaitSpec(OperationSpec):
    kind, category, label = "wait", "Interventions", "Wait"
    defaults: ClassVar[dict[str, Any]] = {"seconds": 1}
    fields: ClassVar[list[dict[str, Any]]] = [field("seconds", "Seconds", "number")]
