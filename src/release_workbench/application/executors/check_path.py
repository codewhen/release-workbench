"""CheckPathExecutor implementation."""

from __future__ import annotations

from .operation import OperationExecutor


class CheckPathExecutor(OperationExecutor):
    """Execute check_path through the injected operation adapter."""

    kind = "check_path"
