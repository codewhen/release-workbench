"""ProgramExecutor implementation."""

from __future__ import annotations

from .operation import OperationExecutor


class ProgramExecutor(OperationExecutor):
    """Execute program through the injected operation adapter."""

    kind = "program"
