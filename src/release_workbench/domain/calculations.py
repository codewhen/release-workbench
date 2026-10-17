"""Pure, strict JSON-compatible arithmetic and comparisons."""

import math
from typing import Any

from .values import ContractError


def json_equal(left: Any, right: Any) -> bool:
    """Compare typed JSON recursively: Booleans differ from numbers at every depth."""
    if type(left) in (int, float) and type(right) in (int, float):
        return bool(left == right)
    if type(left) is not type(right):
        return False
    if isinstance(left, list):
        return len(left) == len(right) and all(
            json_equal(a, b) for a, b in zip(left, right, strict=True)
        )
    if isinstance(left, dict):
        return left.keys() == right.keys() and all(
            json_equal(value, right[key]) for key, value in left.items()
        )
    return bool(left == right)


def calculate(operation: str, left: Any, right: Any) -> Any:
    if operation == "append":
        if not isinstance(left, list):
            raise ContractError("Append requires an array.")
        return [*left, right]
    if operation in ("equals", "not_equals"):
        equal = json_equal(left, right)
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
