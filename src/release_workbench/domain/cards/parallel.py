"""Parallel card specification."""

from __future__ import annotations

from typing import Any, ClassVar

from ..models import Card
from .base import CardSpec, field


class ParallelSpec(CardSpec):
    holds_slot = False
    kind, category, label, output = "parallel", "Control flows", "Parallel", "object"
    defaults: ClassVar[dict[str, Any]] = {"branches": ["first", "second"]}
    fields: ClassVar[list[dict[str, Any]]] = [field("branches", "Branch names", "json")]

    def flow_outputs(self, card: Card) -> tuple[str, ...]:
        return (*card.config.get("branches", ["first", "second"]), "done")

    def validate(self, card: Card) -> list[str]:
        branches = card.config.get("branches", [])
        if (
            not isinstance(branches, list)
            or len(branches) < 2
            or any(not isinstance(x, str) or not x or x == "done" for x in branches)
            or len(set(branches)) != len(branches)
        ):
            return [f"{card.id}: provide at least two unique branch names, excluding done."]
        return []
