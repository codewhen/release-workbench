"""FinishExecutor implementation."""

from __future__ import annotations

from release_workbench.domain.models import Card, Outcome
from release_workbench.domain.values import TypedValue

from ..ports import CardExecutor, ExecutionContext


class FinishExecutor(CardExecutor):
    kind = "finish"

    async def execute(self, card: Card, context: ExecutionContext) -> Outcome:
        return Outcome(
            TypedValue.checked(card.config.get("value"), card.config.get("returns", "void")),
            signal="finish",
        )
