"""BashExecutor implementation."""

from __future__ import annotations

from .operation import OperationExecutor


class BashExecutor(OperationExecutor):
    """Execute bash through the injected operation adapter."""

    kind = "bash"
