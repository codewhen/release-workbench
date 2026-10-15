"""Immutable workflow definitions and serializable execution outcomes."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .values import VOID, TypedValue


@dataclass(frozen=True)
class Owner:
    card: str
    region: str


@dataclass(frozen=True)
class Card:
    id: str
    kind: str
    name: str
    config: dict[str, Any] = field(default_factory=dict)
    inputs: dict[str, Any] = field(default_factory=dict)
    owner: Owner | None = None
    settings: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Edge:
    id: str
    source: str
    target: str
    source_port: str = "next"
    target_port: str = "entry"
    kind: str = "flow"
    path: str = ""


@dataclass(frozen=True)
class Graph:
    id: str
    cards: dict[str, Card]
    edges: tuple[Edge, ...]

    def outgoing(self, card: str, port: str = "next") -> list[Edge]:
        return [
            edge
            for edge in self.edges
            if edge.kind == "flow" and edge.source == card and edge.source_port == port
        ]


@dataclass(frozen=True)
class Workflow:
    name: str
    graphs: dict[str, Graph]
    functions: dict[str, dict[str, Any]]
    inputs: dict[str, dict[str, Any]]
    globals: dict[str, dict[str, Any]]
    concurrency: int
    raw: dict[str, Any]


@dataclass(frozen=True)
class Outcome:
    value: TypedValue = VOID
    port: str = "next"
    signal: str | None = None
    handled: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "value": self.value.to_dict(),
            "port": self.port,
            "signal": self.signal,
            "handled": self.handled,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Outcome:
        return cls(
            TypedValue.from_dict(data["value"]),
            data.get("port", "next"),
            data.get("signal"),
            data.get("handled", False),
        )


@dataclass(frozen=True)
class CardResult:
    status: str
    outcome: Outcome
    evidence: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "outcome": self.outcome.to_dict(),
            "evidence": list(self.evidence),
        }
