"""CallExecutor implementation."""

from __future__ import annotations

from release_workbench.domain.models import Card, Outcome

from ..ports import CardExecutor, ExecutionContext


class CallExecutor(CardExecutor):
    kind = "call"

    async def execute(self, card: Card, context: ExecutionContext) -> Outcome:
        result = await context.invoke(card.config["function"], context.inputs, "call")
        return Outcome(result.value)
