"""IfExecutor implementation."""

from __future__ import annotations

from release_workbench.domain.models import Card, Outcome
from release_workbench.domain.values import TypedValue

from ..ports import CardExecutor, ExecutionContext


class IfExecutor(CardExecutor):
    kind = "if"

    async def execute(self, card: Card, context: ExecutionContext) -> Outcome:
        result = await context.invoke(card.config["function"], context.inputs, "condition")
        value = TypedValue.checked(result.value.value, "boolean")
        return Outcome(value, "true" if value.value else "false")
