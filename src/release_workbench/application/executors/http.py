"""HttpExecutor implementation."""

from __future__ import annotations

from .operation import OperationExecutor


class HttpExecutor(OperationExecutor):
    """Execute http through the injected operation adapter."""

    kind = "http"
