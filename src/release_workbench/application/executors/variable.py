"""VariableExecutor implementation."""

from __future__ import annotations

from release_workbench.domain.calculations import calculate
from release_workbench.domain.models import Card, Outcome
from release_workbench.domain.values import ContractError, TypedValue

from ..ports import CardExecutor, ExecutionContext


class VariableExecutor(CardExecutor):
    kind = "variable"

    async def execute(self, card: Card, context: ExecutionContext) -> Outcome:
        config = card.config
        name = config["name"]
        operation = config.get("operation", "get")
        if operation == "get":
            value = context.global_get(name)
        elif operation == "set":
            value = context.global_set(name, config.get("value"))
        elif operation == "update":
            value = calculate(
                config.get("operator", "add"),
                context.global_get(name),
                config.get("value"),
            )
            value = context.global_set(name, value)
        else:
            raise ContractError("Unknown variable operation.")
        return Outcome(TypedValue.checked(value))
