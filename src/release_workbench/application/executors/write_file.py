"""WriteFileExecutor implementation."""

from __future__ import annotations

from .operation import OperationExecutor


class WriteFileExecutor(OperationExecutor):
    """Execute write_file through the injected operation adapter."""

    kind = "write_file"
