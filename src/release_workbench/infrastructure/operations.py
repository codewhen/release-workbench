"""Infrastructure operation handlers. No workflow scheduling or branching lives here."""

from __future__ import annotations

import json
import sys
from abc import ABC, abstractmethod
from collections.abc import Callable
from pathlib import Path
from typing import Any

from release_workbench.application.ports import ProcessRunner
from release_workbench.domain.models import Card
from release_workbench.domain.values import ContractError

from .documents import MAX_BYTES, atomic_write


class OperationHandler(ABC):
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


class PythonHandler(OperationHandler):
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
            root,
            environment,
            log,
            check,
            card.settings.get("timeout", 3600),
        )


class ProgramHandler(OperationHandler):
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


class BashHandler(ProgramHandler):
    def arguments(self, card: Card, root: Path) -> list[str]:
        return ["bash", "-c", card.config["code"]]


class ScriptHandler(ProgramHandler):
    def arguments(self, card: Card, root: Path) -> list[str]:
        language = card.config["language"]
        executable = {"python": sys.executable, "bash": "bash"}.get(language)
        if not executable:
            raise ContractError("Choose Python or Bash.")
        return [
            executable,
            str(workspace_path(root, card.config["path"])),
            *card.config.get("arguments", []),
        ]


class HttpHandler(OperationHandler):
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


class CheckPathHandler(OperationHandler):
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


class ReadFileHandler(OperationHandler):
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


class WriteFileHandler(OperationHandler):
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
            with path.open("x") as stream:
                stream.write(text)
        return {"path": str(path.relative_to(root)), "bytes": len(text.encode())}


HANDLERS: dict[str, OperationHandler] = {
    "python": PythonHandler(),
    "bash": BashHandler(),
    "script": ScriptHandler(),
    "program": ProgramHandler(),
    "http": HttpHandler(),
    "check_path": CheckPathHandler(),
    "read_file": ReadFileHandler(),
    "write_file": WriteFileHandler(),
}
