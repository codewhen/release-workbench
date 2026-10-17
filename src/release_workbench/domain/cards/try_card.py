"""Try card specification."""

from __future__ import annotations

from ..models import Card
from .base import CardSpec


class TrySpec(CardSpec):
    holds_slot = False
    kind, category, label, output = (
        "try",
        "Control flows",
        "Try / Catch / Finally",
        "json",
    )

    def flow_outputs(self, card: Card) -> tuple[str, ...]:
        return ("body", "catch", "finally", "done")
