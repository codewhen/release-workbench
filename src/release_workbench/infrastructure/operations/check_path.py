"""CheckPathHandler external effect adapter."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from release_workbench.application.ports import ProcessRunner
from release_workbench.domain.models import Card

from .base import OperationHandler, workspace_path


class CheckPathHandler(OperationHandler):
    kind = "check_path"

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
        check()
        path = workspace_path(root, card.config["path"])
        operations = {
            "exists": path.exists,
            "file": path.is_file,
            "directory": path.is_dir,
        }
        return operations[card.config.get("type", "exists")]()
