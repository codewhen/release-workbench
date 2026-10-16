"""TryExecutor implementation."""

from __future__ import annotations

import asyncio

from release_workbench.domain.models import Card, Outcome

from ..errors import EvidenceRequired, ExecutionFailure
from ..ports import CardExecutor, ExecutionContext


class TryExecutor(CardExecutor):
    kind = "try"

    async def execute(self, card: Card, context: ExecutionContext) -> Outcome:
        failure: ExecutionFailure | None = None
        result = Outcome()
        cleanup = True
        try:
            result = await context.region(card, "body", "body")
        except (EvidenceRequired, asyncio.CancelledError):
            cleanup = False
            raise
        except ExecutionFailure as error:
            failure = error
            context.error = {"message": str(error), "type": type(error).__name__}
            result = await context.region(card, "catch", "catch")
            if result.handled:
                failure = None
        finally:
            # Stop cancels instead of executing new user cleanup operations.
            if cleanup:
                context.check()
                final = await context.region(card, "finally", "finally")
                if final.signal in ("break", "continue") and failure is None:
                    result = final
        if failure:
            raise failure
        if result.signal in ("break", "continue"):
            return result
        return Outcome(result.value, "done")
