"""PollExecutor implementation."""

from __future__ import annotations

from release_workbench.domain.models import Card, Outcome
from release_workbench.domain.values import TypedValue

from ..ports import CardExecutor, ExecutionContext


class PollExecutor(CardExecutor):
    kind = "poll"

    async def execute(self, card: Card, context: ExecutionContext) -> Outcome:
        count = 0
        while True:
            count += 1
            result = await context.invoke(card.config["function"], context.inputs, f"probe-{count}")
            if TypedValue.checked(result.value.value, "boolean").value:
                return Outcome(TypedValue.checked(True, "boolean"))
            await context.sleep(card.config.get("interval", 1))
