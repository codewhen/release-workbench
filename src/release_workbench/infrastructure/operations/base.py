"""Abstract external operation contract and workspace-path boundary."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from pathlib import Path
from typing import Any, ClassVar

from release_workbench.application.ports import ProcessRunner
from release_workbench.domain.models import Card
from release_workbench.domain.values import ContractError


class OperationHandler(ABC):
    kind: ClassVar[str]

    @abstractmethod
    async def execute(
        self,
        card: Card,
        root: Path,
        inputs: dict[str, Any],
        environment: dict[str, str],
        process: ProcessRunner,
        log: Callable[[str], None],
        check: Callable[[], None],
    ) -> Any:
        raise NotImplementedError


def workspace_path(root: Path, name: str) -> Path:
    path = (root / name).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ContractError(
            "File operations must stay inside this workspace, including symlink targets."
        )
    return path
