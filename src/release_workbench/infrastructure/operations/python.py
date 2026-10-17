"""PythonHandler external effect adapter."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from release_workbench.application.ports import ProcessRunner
from release_workbench.domain.models import Card

from .base import OperationHandler, workspace_path


class PythonHandler(OperationHandler):
    kind = "python"

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
        return await process.structured(
            {"mode": "python", "code": card.config["code"], "inputs": inputs},
            workspace_path(root, card.settings.get("cwd", ".")),
            environment,
            log,
            check,
            card.settings.get("timeout", 3600),
        )
