"""WaitExecutor implementation."""

from __future__ import annotations

import math

from release_workbench.domain.models import Card, Outcome
from release_workbench.domain.values import ContractError

from ..ports import CardExecutor, ExecutionContext


class WaitExecutor(CardExecutor):
    kind = "wait"

    async def execute(self, card: Card, context: ExecutionContext) -> Outcome:
        seconds = card.config.get("seconds", 1)
        if type(seconds) not in (int, float) or not math.isfinite(seconds) or seconds < 0:
            raise ContractError("Wait requires a nonnegative finite duration.")
        await context.sleep(seconds)
        return Outcome()
