"""HttpHandler external effect adapter."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from release_workbench.application.ports import ProcessRunner
from release_workbench.domain.models import Card

from .base import OperationHandler


class HttpHandler(OperationHandler):
    kind = "http"

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
            {
                "mode": "http",
                "config": card.config,
                "timeout": card.settings.get("timeout", 30),
            },
            root,
            environment,
            log,
            check,
            card.settings.get("timeout", 30),
        )
