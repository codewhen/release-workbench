"""LoopExecutor implementation."""

from __future__ import annotations

from release_workbench.domain.models import Card, Outcome
from release_workbench.domain.values import TypedValue

from ..errors import ExecutionFailure
from ..ports import CardExecutor, ExecutionContext


class LoopExecutor(CardExecutor):
    kind = "loop"

    async def execute(self, card: Card, context: ExecutionContext) -> Outcome:
        config = card.config
        count = 0
        while True:
            context.check()
            if config.get("mode") == "count" and count >= config.get("count", 3):
                break
            if config.get("mode") == "while":
                result = await context.invoke(
                    config["function"], context.inputs, f"condition-{count + 1}"
                )
                if TypedValue.checked(result.value.value, "boolean").value is False:
                    break
            limit = config.get("limit", 100)
            if limit is not None and count >= limit:
                raise ExecutionFailure("Loop reached its configured iteration limit.")
            result = await context.region(card, "body", f"iteration-{count + 1}")
            count += 1
            if result.signal == "break":
                break
            if result.signal not in (None, "continue", "return"):
                raise ExecutionFailure(
                    "Loop Body must finish at Next iteration, Continue or Break."
                )
        return Outcome(TypedValue.checked({"iterations": count}, "object"), "done")
