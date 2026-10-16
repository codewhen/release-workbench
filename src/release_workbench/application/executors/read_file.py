"""ReadFileExecutor implementation."""

from __future__ import annotations

from .operation import OperationExecutor


class ReadFileExecutor(OperationExecutor):
    """Execute read_file through the injected operation adapter."""

    kind = "read_file"
