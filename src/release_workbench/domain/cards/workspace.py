"""Workspace card specification."""

from __future__ import annotations

from typing import Any, ClassVar

from .base import OperationSpec, field


class WorkspaceSpec(OperationSpec):
    holds_slot = False
    kind, category, label, output = (
        "workspace",
        "Functions",
        "External workspace",
        "json",
    )
    defaults: ClassVar[dict[str, Any]] = {"path": "", "inputs": {}}
    required = ("path",)
    fields: ClassVar[list[dict[str, Any]]] = [
        field("path", "Workflow YAML path"),
        field("inputs", "Workflow inputs", "json", advanced=True),
    ]
