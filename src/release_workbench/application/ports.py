"""Dependency-inversion boundaries used by application services and executors."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from pathlib import Path
from typing import Any, Protocol

from release_workbench.domain.models import Card, Outcome, Workflow


class Clock(Protocol):
    def monotonic(self) -> float: ...
    async def sleep(self, seconds: float) -> None: ...


class ExecutionContext(Protocol):
    inputs: dict[str, Any]
    error: dict[str, Any]
    loop: dict[str, Any]
    path: str

    async def invoke(self, name: str, inputs: dict[str, Any], label: str) -> Outcome: ...
    async def region(self, card: Card, name: str, label: str) -> Outcome: ...
    async def operation(self, card: Card) -> Any: ...
    async def sleep(self, seconds: float) -> None: ...
    async def manual(self, card: Card) -> Outcome: ...
    async def workspace(self, card: Card) -> Outcome: ...
    def global_get(self, name: str) -> Any: ...
    def global_set(self, name: str, value: Any) -> Any: ...
    def check(self) -> None: ...


class CardExecutor(ABC):
    """All concrete card executors obey the same typed result contract."""

    @abstractmethod
    async def execute(self, card: Card, context: ExecutionContext) -> Outcome:
        raise NotImplementedError


class Masker(Protocol):
    values: list[str]

    def text(self, value: str) -> str: ...
    def object(self, value: Any) -> Any: ...
    def contains(self, value: Any) -> bool: ...


class Evidence(Protocol):
    directory: Path
    state: dict[str, Any]
    masker: Masker

    def emit(self, kind: str, path: str, **data: Any) -> None: ...
    def snapshot(self) -> dict[str, Any]: ...
    def save(self) -> None: ...
    def log(self, path: str, text: str) -> None: ...
    def report(self) -> Path: ...


class Services(Protocol):
    clock: Clock

    def environment(self, workflow: Workflow) -> dict[str, str]: ...
    def fingerprint(self, workflow: Workflow, root: Path, inputs: dict[str, Any]) -> str: ...
    def evidence(
        self,
        directory: Path,
        state: dict[str, Any],
        workflow: Workflow,
        environment: dict[str, str],
    ) -> Evidence: ...
    def load_state(self, directory: Path) -> dict[str, Any]: ...
    def load_workflow(self, file: Path) -> Workflow: ...
    async def operation(
        self,
        card: Card,
        root: Path,
        inputs: dict[str, Any],
        environment: dict[str, str],
        log: Any,
        check: Any,
    ) -> Any: ...


class ProcessRunner(Protocol):
    """External execution boundary; tests can inject a runner without inheriting an adapter."""

    async def run(
        self,
        argv: list[str],
        cwd: Path,
        environment: dict[str, str],
        payload: dict[str, Any] | None,
        log: Callable[[str], None],
        check: Callable[[], None],
        timeout: float = 3600,
    ) -> dict[str, Any]: ...
    async def structured(
        self,
        request: dict[str, Any],
        cwd: Path,
        environment: dict[str, str],
        log: Callable[[str], None],
        check: Callable[[], None],
        timeout: float,
    ) -> Any: ...
