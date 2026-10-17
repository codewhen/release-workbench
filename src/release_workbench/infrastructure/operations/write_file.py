"""WriteFileHandler external effect adapter."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from release_workbench.application.ports import ProcessRunner
from release_workbench.domain.models import Card
from release_workbench.domain.values import ContractError

from ..documents import MAX_BYTES, atomic_write
from .base import OperationHandler, workspace_path


class WriteFileHandler(OperationHandler):
    kind = "write_file"

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
        value = card.config.get("value")
        if card.config.get("format") == "json":
            text = json.dumps(value, indent=2, allow_nan=False) + "\n"
        elif isinstance(value, str):
            text = value
        else:
            raise ContractError("Text writes require a string; choose JSON for other values.")
        if len(text.encode()) > MAX_BYTES:
            raise ContractError("File output exceeds 1 MiB.")
        path.parent.mkdir(parents=True, exist_ok=True)
        check()
        if card.config.get("overwrite"):
            atomic_write(path, text)
        else:
            with path.open("x", encoding="utf-8") as stream:
                stream.write(text)
        return {"path": str(path.relative_to(root)), "bytes": len(text.encode())}
