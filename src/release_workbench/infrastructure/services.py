"""Composition root adapters for the application-owned dependency interfaces."""

from __future__ import annotations

import asyncio
import json
import os
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from release_workbench.application.compiler import references
from release_workbench.application.ports import Clock, ProcessRunner
from release_workbench.domain.models import Card, Workflow

from .documents import DocumentStore, compile_document, digest
from .evidence import EvidenceStore, SecretMasker
from .operations import HANDLERS
from .processes import ProcessAdapter


class SystemClock:
    def monotonic(self) -> float:
        return time.monotonic()

    async def sleep(self, seconds: float) -> None:
        await asyncio.sleep(seconds)


class LocalServices:
    def __init__(self, process: ProcessRunner | None = None, clock: Clock | None = None):
        self.process: ProcessRunner = process or ProcessAdapter()
        self.clock: Clock = clock or SystemClock()

    def environment(self, workflow: Workflow) -> dict[str, str]:
        return {**os.environ, **workflow.raw.get("environment", {})}

    def fingerprint(self, workflow: Workflow, root: Path, inputs: dict[str, Any]) -> str:
        source: dict[str, str] = {}
        visited: set[Path] = set()

        def collect(definition: Workflow, directory: Path) -> None:
            for pattern in definition.raw.get("source_paths", []):
                for file in directory.glob(pattern):
                    if file.is_file():
                        source[str(file.resolve())] = digest(file.read_bytes())
            for graph in definition.graphs.values():
                for card in graph.cards.values():
                    path = card.config.get("path")
                    if (
                        card.kind not in ("script", "workspace")
                        or not isinstance(path, str)
                        or not path
                    ):
                        continue
                    file = (directory / path).resolve()
                    if not file.is_file():
                        continue
                    source[str(file)] = digest(file.read_bytes())
                    if card.kind == "workspace" and file not in visited:
                        visited.add(file)
                        try:
                            child = self.load_workflow(file)
                        except (ValueError, OSError):
                            # Validation belongs to the selected child's execution, not an unselected branch.
                            continue
                        collect(child, (file.parent / child.raw.get("workspace", ".")).resolve())

        collect(workflow, root)
        return digest(
            {
                "workspace": str(root.resolve()),
                "workflow": {k: v for k, v in workflow.raw.items() if k != "layout"},
                "source": source,
                "inputs": inputs,
                "environment": {
                    name: digest(self.environment(workflow).get(name, ""))
                    for name in set(workflow.raw.get("secrets", []))
                    | {
                        binding["$ref"][4:]
                        for graph in workflow.graphs.values()
                        for card in graph.cards.values()
                        for binding in references([card.config, card.inputs])
                        if binding["$ref"].startswith("env:")
                    }
                },
            }
        )

    def evidence(
        self,
        directory: Path,
        state: dict[str, Any],
        workflow: Workflow,
        environment: dict[str, str],
    ) -> EvidenceStore:
        return EvidenceStore(
            directory,
            state,
            SecretMasker(
                [
                    value
                    for name in workflow.raw.get("secrets", [])
                    for value in [
                        environment.get(name, ""),
                        *(
                            card.settings.get("environment", {}).get(name, "")
                            for graph in workflow.graphs.values()
                            for card in graph.cards.values()
                        ),
                    ]
                ]
            ),
        )

    def load_state(self, directory: Path) -> dict[str, Any]:
        return json.loads((directory / "summary.json").read_text(encoding="utf-8"))

    def load_workflow(self, file: Path) -> Workflow:
        return compile_document(DocumentStore(file).read()["workflow"])

    async def operation(
        self,
        card: Card,
        root: Path,
        inputs: dict[str, Any],
        environment: dict[str, str],
        log: Callable[[str], None],
        check: Callable[[], None],
    ) -> Any:
        return await HANDLERS[card.kind].execute(
            card, root, inputs, environment, self.process, log, check
        )
