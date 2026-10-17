"""ScriptExecutor implementation."""

from __future__ import annotations

from .operation import OperationExecutor


class ScriptExecutor(OperationExecutor):
    """Execute script through the injected operation adapter."""

    kind = "script"
