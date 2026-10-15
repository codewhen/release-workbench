"""Small polymorphic executors; scheduling and external effects are injected."""

from __future__ import annotations

import asyncio
import math
from typing import Any

from release_workbench.domain.cards import get_spec
from release_workbench.domain.models import Card, Outcome
from release_workbench.domain.values import ContractError, TypedValue

from .ports import CardExecutor, ExecutionContext


class ExecutionFailure(ContractError):
    """A failed card with its original attempt retained in evidence."""


class EvidenceRequired(ExecutionFailure):
    """An unattended run reached a manual intervention."""


class StartExecutor(CardExecutor):
    async def execute(self, card: Card, context: ExecutionContext) -> Outcome:
        return Outcome(TypedValue.checked(context.inputs, "object"))


class FinishExecutor(CardExecutor):
    async def execute(self, card: Card, context: ExecutionContext) -> Outcome:
        return Outcome(
            TypedValue.checked(card.config.get("value"), card.config.get("returns", "void")),
            signal="finish",
        )


class ReturnExecutor(CardExecutor):
    async def execute(self, card: Card, context: ExecutionContext) -> Outcome:
        return Outcome(
            TypedValue.checked(card.config.get("value"), card.config.get("returns", "json")),
            signal="return",
            handled=card.config.get("handled") is True,
        )


class BreakExecutor(CardExecutor):
    async def execute(self, card: Card, context: ExecutionContext) -> Outcome:
        return Outcome(signal="break")


class ContinueExecutor(CardExecutor):
    async def execute(self, card: Card, context: ExecutionContext) -> Outcome:
        return Outcome(signal="continue")


class OperationExecutor(CardExecutor):
    async def execute(self, card: Card, context: ExecutionContext) -> Outcome:
        value = await context.operation(card)
        declared = (
            card.config.get("returns", "json")
            if card.kind == "python"
            else get_spec(card.kind).output
        )
        return Outcome(TypedValue.checked(value, declared))


class PythonExecutor(OperationExecutor):
    """Python uses the same operation contract with a separate typed return channel."""


class FileExecutor(OperationExecutor):
    """File handlers enforce workspace boundaries independently of control flow."""


class HttpExecutor(OperationExecutor):
    """HTTP remains cancellable through the injected process adapter."""


class VariableExecutor(CardExecutor):
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


def calculate(operation: str, left: Any, right: Any) -> Any:
    if operation == "append":
        if not isinstance(left, list):
            raise ContractError("Append requires an array.")
        return [*left, right]
    if operation in ("equals", "not_equals"):
        equal = type(left) is type(right) and left == right
        return equal if operation == "equals" else not equal
    if operation in ("and", "or", "not"):
        if type(left) is not bool or operation != "not" and type(right) is not bool:
            raise ContractError("Boolean operations require Boolean operands.")
        return (
            not left
            if operation == "not"
            else left and right
            if operation == "and"
            else left or right
        )
    if any(type(value) not in (int, float) or not math.isfinite(value) for value in (left, right)):
        raise ContractError("Arithmetic and numeric comparisons require finite numbers.")
    operations = {
        "add": lambda: left + right,
        "subtract": lambda: left - right,
        "multiply": lambda: left * right,
        "divide": lambda: left / right,
        "less_than": lambda: left < right,
        "greater_than": lambda: left > right,
    }
    if operation not in operations:
        raise ContractError("Unknown calculation operation.")
    return operations[operation]()


class CalculateExecutor(CardExecutor):
    async def execute(self, card: Card, context: ExecutionContext) -> Outcome:
        return Outcome(
            TypedValue.checked(
                calculate(
                    card.config["operator"],
                    card.config.get("left"),
                    card.config.get("right"),
                )
            )
        )


class CallExecutor(CardExecutor):
    async def execute(self, card: Card, context: ExecutionContext) -> Outcome:
        result = await context.invoke(card.config["function"], context.inputs, "call")
        return Outcome(result.value)


class IfExecutor(CardExecutor):
    async def execute(self, card: Card, context: ExecutionContext) -> Outcome:
        result = await context.invoke(card.config["function"], context.inputs, "condition")
        value = TypedValue.checked(result.value.value, "boolean")
        return Outcome(value, "true" if value.value else "false")


class LoopExecutor(CardExecutor):
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


class ParallelExecutor(CardExecutor):
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


class JoinExecutor(CardExecutor):
    async def execute(self, card: Card, context: ExecutionContext) -> Outcome:
        return Outcome(TypedValue.checked(context.inputs["branches"], "object"))


class TryExecutor(CardExecutor):
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


class WaitExecutor(CardExecutor):
    async def execute(self, card: Card, context: ExecutionContext) -> Outcome:
        seconds = card.config.get("seconds", 1)
        if type(seconds) not in (int, float) or not math.isfinite(seconds) or seconds < 0:
            raise ContractError("Wait requires a nonnegative finite duration.")
        await context.sleep(seconds)
        return Outcome()


class PollExecutor(CardExecutor):
    async def execute(self, card: Card, context: ExecutionContext) -> Outcome:
        count = 0
        while True:
            count += 1
            result = await context.invoke(card.config["function"], context.inputs, f"probe-{count}")
            if TypedValue.checked(result.value.value, "boolean").value:
                return Outcome(TypedValue.checked(True, "boolean"))
            await context.sleep(card.config.get("interval", 1))


class ManualExecutor(CardExecutor):
    async def execute(self, card: Card, context: ExecutionContext) -> Outcome:
        return await context.manual(card)


class WorkspaceExecutor(CardExecutor):
    async def execute(self, card: Card, context: ExecutionContext) -> Outcome:
        return await context.workspace(card)


EXECUTORS: dict[str, CardExecutor] = {
    "start": StartExecutor(),
    "finish": FinishExecutor(),
    "return": ReturnExecutor(),
    "break": BreakExecutor(),
    "continue": ContinueExecutor(),
    "variable": VariableExecutor(),
    "calculate": CalculateExecutor(),
    "call": CallExecutor(),
    "if": IfExecutor(),
    "loop": LoopExecutor(),
    "parallel": ParallelExecutor(),
    "join": JoinExecutor(),
    "try": TryExecutor(),
    "wait": WaitExecutor(),
    "poll": PollExecutor(),
    "manual": ManualExecutor(),
    "workspace": WorkspaceExecutor(),
    "python": PythonExecutor(),
    "bash": OperationExecutor(),
    "script": OperationExecutor(),
    "program": OperationExecutor(),
    "check_path": FileExecutor(),
    "read_file": FileExecutor(),
    "write_file": FileExecutor(),
    "http": HttpExecutor(),
}
