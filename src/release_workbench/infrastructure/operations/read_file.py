"""ReadFileHandler external effect adapter."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from release_workbench.application.ports import ProcessRunner
from release_workbench.domain.models import Card
from release_workbench.domain.values import ContractError

from ..documents import MAX_BYTES
from .base import OperationHandler, workspace_path


class ReadFileHandler(OperationHandler):
    kind = "read_file"

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
        if path.stat().st_size > MAX_BYTES:
            raise ContractError("File exceeds 1 MiB.")
        data = path.read_bytes()
        if len(data) > MAX_BYTES:
            raise ContractError("File exceeds 1 MiB.")
        return json.loads(data) if card.config.get("format") == "json" else data.decode("utf-8")
