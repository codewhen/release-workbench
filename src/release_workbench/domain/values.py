"""JSON-compatible values, with an explicit distinction between Void and null."""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class ValueType(StrEnum):
    VOID = "void"
    NULL = "null"
    BOOLEAN = "boolean"
    NUMBER = "number"
    STRING = "string"
    ARRAY = "array"
    OBJECT = "object"
    JSON = "json"


class ContractError(ValueError):
    """A workflow or runtime value violates its declared contract."""


@dataclass(frozen=True)
class TypedValue:
    type: ValueType
    value: Any = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type.value,
            **({} if self.type == ValueType.VOID else {"value": self.value}),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TypedValue:
        return cls(ValueType(data["type"]), data.get("value"))

    @classmethod
    def checked(cls, value: Any, declared: str = "json") -> TypedValue:
        expected = ValueType(declared)
        actual = infer_type(value)
        if expected == ValueType.VOID:
            if value is not None:
                raise ContractError("Void operations cannot return a value.")
            return VOID
        if expected != ValueType.JSON and actual != expected:
            raise ContractError(f"Expected {expected.value}; received {actual.value}.")
        return cls(actual, value)


def infer_type(value: Any) -> ValueType:
    if value is None:
        return ValueType.NULL
    if type(value) is bool:
        return ValueType.BOOLEAN
    if type(value) in (int, float):
        if not math.isfinite(value):
            raise ContractError("Numbers must be finite.")
        return ValueType.NUMBER
    if isinstance(value, str):
        return ValueType.STRING
    if isinstance(value, list):
        for item in value:
            infer_type(item)
        return ValueType.ARRAY
    if isinstance(value, dict) and all(isinstance(key, str) for key in value):
        for item in value.values():
            infer_type(item)
        return ValueType.OBJECT
    raise ContractError("Values must be JSON-compatible.")


VOID = TypedValue(ValueType.VOID)
