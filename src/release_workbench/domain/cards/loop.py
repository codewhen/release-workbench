"""Loop card specification."""

from __future__ import annotations

import math
from typing import Any, ClassVar

from ..models import Card
from .base import CardSpec, field


class LoopSpec(CardSpec):
    holds_slot = False
    kind, category, label, output = "loop", "Control flows", "Loop", "object"
    defaults: ClassVar[dict[str, Any]] = {
        "mode": "count",
        "count": 3,
        "function": "",
        "limit": 100,
        "timeout": 1800,
    }
    fields: ClassVar[list[dict[str, Any]]] = [
        field("mode", "Loop mode", "select", options=["count", "while"]),
        field("count", "Repeat count", "number", when={"mode": "count"}),
        field(
            "function",
            "Condition function",
            "function",
            returns="boolean",
            when={"mode": "while"},
        ),
        field("limit", "Maximum iterations (null = unlimited)", "json", advanced=True),
        field("timeout", "Time limit in seconds (null = unlimited)", "json", advanced=True),
    ]

    def flow_outputs(self, card: Card) -> tuple[str, ...]:
        return ("body", "done")

    def validate(self, card: Card) -> list[str]:
        errors = super().validate(card)
        mode = card.config.get("mode", "count")
        if mode not in ("count", "while"):
            errors.append(f"{card.id}: choose Count or While.")
        if mode == "count" and (
            type(card.config.get("count", 3)) is not int or card.config.get("count", 3) < 0
        ):
            errors.append(f"{card.id}: repeat count must be a nonnegative integer.")
        for key in ("limit", "timeout"):
            value = card.config.get(key, self.defaults[key])
            if value is not None and (
                not isinstance(value, (int, float))
                or type(value) is bool
                or not math.isfinite(value)
                or value <= 0
                or (key == "limit" and type(value) is not int)
            ):
                errors.append(
                    f"{card.id}: {key} must be a positive {'integer' if key == 'limit' else 'finite number'} or null."
                )
        return errors
