"""Start card specification."""

from __future__ import annotations

from .base import OperationSpec


class StartSpec(OperationSpec):
    kind, category, label, output = "start", "Functions", "Start", "object"
