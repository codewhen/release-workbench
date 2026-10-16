"""Abstract card specifications and shared field/port validation."""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from typing import Any, ClassVar

from ..models import Card, Workflow


class CardSpec(ABC):
    kind: ClassVar[str]
    category: ClassVar[str]
    label: ClassVar[str]
    defaults: ClassVar[dict[str, Any]] = {}
    fields: ClassVar[list[dict[str, Any]]] = []
    required: ClassVar[tuple[str, ...]] = ()
    output: ClassVar[str] = "void"
    holds_slot: ClassVar[bool] = True
    supports_retry: ClassVar[bool] = False

    def result_type(self, card: Card, workflow: Workflow | None = None) -> str:
        return self.output

    @abstractmethod
    def flow_outputs(self, card: Card) -> tuple[str, ...]:
        """Execution outputs; value ports are a separate contract."""

    def validate(self, card: Card) -> list[str]:
        errors = [
            f"{card.id}: configure {key}."
            for key in self.required
            if key not in card.config or card.config[key] == ""
        ]
        for descriptor in self.fields:
            if descriptor.get("when") and not all(
                card.config.get(key) == expected for key, expected in descriptor["when"].items()
            ):
                continue
            if descriptor.get("unless") and all(
                card.config.get(key) == expected for key, expected in descriptor["unless"].items()
            ):
                continue
            value = card.config.get(descriptor["key"])
            if isinstance(value, dict) and "$ref" in value:
                if descriptor["widget"] in ("function", "global", "select", "type", "boolean"):
                    errors.append(
                        f"{card.id}: {descriptor['label']} must be configured statically."
                    )
                continue
            if descriptor.get("items") == "string" and (
                not isinstance(value, list) or any(not isinstance(item, str) for item in value)
            ):
                errors.append(f"{card.id}: {descriptor['key']} must be an array of strings.")
            if descriptor["widget"] == "select" and value not in descriptor["options"]:
                errors.append(f"{card.id}: invalid {descriptor['label']}.")
            if descriptor["widget"] in (
                "text",
                "textarea",
                "code",
                "function",
                "global",
            ) and not isinstance(value, str):
                errors.append(f"{card.id}: {descriptor['label']} must be text.")
            if descriptor["widget"] == "type" and value not in (
                "void",
                "null",
                "boolean",
                "number",
                "string",
                "array",
                "object",
                "json",
            ):
                errors.append(f"{card.id}: invalid return type.")
            if descriptor["widget"] == "number" and (
                type(value) not in (int, float)
                or not isinstance(value, (float, int))
                or not math.isfinite(value)
                or value < 0
            ):
                errors.append(
                    f"{card.id}: {descriptor['label']} must be a nonnegative finite number."
                )
            if descriptor["widget"] == "boolean" and type(value) is not bool:
                errors.append(f"{card.id}: {descriptor['label']} must be Boolean.")
        return errors

    def metadata(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "category": self.category,
            "label": self.label,
            "defaults": self.defaults,
            "fields": self.fields,
            "output": self.output,
            "ports": list(
                self.flow_outputs(Card("metadata", self.kind, self.label, self.defaults))
            ),
        }


class OperationSpec(CardSpec):
    def flow_outputs(self, card: Card) -> tuple[str, ...]:
        return ("next",)


class TerminalSpec(CardSpec):
    def flow_outputs(self, card: Card) -> tuple[str, ...]:
        return ()


def field(key: str, label: str, widget: str = "text", **extra: Any) -> dict[str, Any]:
    return {"key": key, "label": label, "widget": widget, **extra}
