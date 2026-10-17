"""Poll card specification."""

from __future__ import annotations

import math
from typing import Any, ClassVar

from ..models import Card
from .base import OperationSpec, field


class PollSpec(OperationSpec):
    holds_slot = False
    kind, category, label, output = "poll", "Interventions", "Poll until", "boolean"
    defaults: ClassVar[dict[str, Any]] = {"function": "", "interval": 1, "timeout": 1800}
    required = ("function",)
    fields: ClassVar[list[dict[str, Any]]] = [
        field("function", "Boolean probe", "function", returns="boolean"),
        field("interval", "Interval seconds", "number"),
        field("timeout", "Timeout (null = unlimited)", "json", advanced=True),
    ]

    def validate(self, card: Card) -> list[str]:
        errors = super().validate(card)
        timeout = card.config.get("timeout", self.defaults["timeout"])
        if timeout is not None and (
            not isinstance(timeout, (int, float))
            or type(timeout) is bool
            or not math.isfinite(timeout)
            or timeout <= 0
        ):
            errors.append(f"{card.id}: timeout must be a positive finite number or null.")
        return errors
