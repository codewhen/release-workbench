"""CalculateExecutor implementation."""

from __future__ import annotations

from release_workbench.domain.calculations import calculate
from release_workbench.domain.models import Card, Outcome
from release_workbench.domain.values import TypedValue

from ..ports import CardExecutor, ExecutionContext


class CalculateExecutor(CardExecutor):
    kind = "calculate"

    async def execute(self, card: Card, context: ExecutionContext) -> Outcome:
        return Outcome(
            TypedValue.checked(
                calculate(
                    card.config["operator"],
                    card.config.get("left"),
                    card.config.get("right"),
                )
            )
        )
