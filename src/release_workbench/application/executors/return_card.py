"""ReturnExecutor implementation."""

from __future__ import annotations

from release_workbench.domain.models import Card, Outcome
from release_workbench.domain.values import TypedValue

from ..ports import CardExecutor, ExecutionContext


class ReturnExecutor(CardExecutor):
    kind = "return"

    async def execute(self, card: Card, context: ExecutionContext) -> Outcome:
        return Outcome(
            TypedValue.checked(card.config.get("value"), card.config.get("returns", "json")),
            signal="return",
            handled=card.config.get("handled") is True,
        )
