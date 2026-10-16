"""ManualExecutor implementation."""

from __future__ import annotations

from release_workbench.domain.models import Card, Outcome

from ..ports import CardExecutor, ExecutionContext


class ManualExecutor(CardExecutor):
    kind = "manual"

    async def execute(self, card: Card, context: ExecutionContext) -> Outcome:
        return await context.manual(card)
