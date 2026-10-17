"""PythonExecutor implementation."""

from __future__ import annotations

from .operation import OperationExecutor


class PythonExecutor(OperationExecutor):
    """Python uses the same operation contract with a separate typed return channel."""

    kind = "python"
