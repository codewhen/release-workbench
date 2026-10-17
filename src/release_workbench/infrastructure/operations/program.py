"""ProgramHandler external effect adapter."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from release_workbench.application.ports import ProcessRunner
from release_workbench.domain.models import Card
from release_workbench.domain.values import ContractError

from .base import OperationHandler, workspace_path


class ProgramHandler(OperationHandler):
    kind = "program"

    def arguments(self, card: Card, root: Path) -> list[str]:
        return card.config["argv"]

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
        cwd = workspace_path(root, card.settings.get("cwd", "."))
        result = await process.run(
            self.arguments(card, root),
            cwd,
            environment,
            {"inputs": inputs},
            log,
            check,
            card.settings.get("timeout", 3600),
        )
        if card.config.get("capture") == "json":
            try:
                result["json"] = json.loads(result["stdout"])
            except ValueError as error:
                raise ContractError("Program stdout must contain one JSON value.") from error
        return result
