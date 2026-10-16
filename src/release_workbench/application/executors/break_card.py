"""BreakExecutor implementation."""

from __future__ import annotations

from release_workbench.domain.models import Card, Outcome

from ..ports import CardExecutor, ExecutionContext


class BreakExecutor(CardExecutor):
    kind = "break"

    async def execute(self, card: Card, context: ExecutionContext) -> Outcome:
        return Outcome(signal="break")
