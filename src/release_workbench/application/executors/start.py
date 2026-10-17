"""StartExecutor implementation."""

from __future__ import annotations

from release_workbench.domain.models import Card, Outcome
from release_workbench.domain.values import TypedValue

from ..ports import CardExecutor, ExecutionContext


class StartExecutor(CardExecutor):
    kind = "start"

    async def execute(self, card: Card, context: ExecutionContext) -> Outcome:
        return Outcome(TypedValue.checked(context.inputs, "object"))
