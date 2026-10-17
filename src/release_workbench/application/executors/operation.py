"""Shared external-operation result contract; concrete cards declare their own kind."""

from __future__ import annotations

from release_workbench.domain.cards import get_spec
from release_workbench.domain.models import Card, Outcome
from release_workbench.domain.values import TypedValue

from ..ports import CardExecutor, ExecutionContext


class OperationExecutor(CardExecutor):
    async def execute(self, card: Card, context: ExecutionContext) -> Outcome:
        value = await context.operation(card)
        declared = get_spec(card.kind).result_type(card)
        return Outcome(TypedValue.checked(value, declared))
