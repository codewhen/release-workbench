"""ParallelExecutor implementation."""

from __future__ import annotations

import asyncio

from release_workbench.domain.models import Card, Outcome
from release_workbench.domain.values import TypedValue

from ..ports import CardExecutor, ExecutionContext


class ParallelExecutor(CardExecutor):
    kind = "parallel"

    async def execute(self, card: Card, context: ExecutionContext) -> Outcome:
        names = card.config["branches"]
        tasks = [asyncio.create_task(context.region(card, name, name)) for name in names]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        errors = [value for value in results if isinstance(value, BaseException)]
        if errors:
            raise errors[0]
        signals = [value.signal for value in results if isinstance(value, Outcome)]
        if "break" in signals or "continue" in signals:
            return Outcome(signal="break" if "break" in signals else "continue")
        values = {
            name: value.value.to_dict()
            for name, value in zip(names, results, strict=True)
            if isinstance(value, Outcome)
        }
        return Outcome(TypedValue.checked(values, "object"), "done")
