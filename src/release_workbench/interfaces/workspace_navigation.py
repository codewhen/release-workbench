"""Resolve child definitions with the same workspace rules as execution."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from release_workbench.infrastructure.documents import validate_document_schema


def child_definition(
    parent: Path,
    raw: dict[str, Any],
    graph: str,
    card_id: str,
    execution: dict[str, Any] | None = None,
) -> Path:
    validate_document_schema(raw)
    cards = raw["graphs"].get(graph, {}).get("cards", [])
    card = next((card for card in cards if card["id"] == card_id), None)
    if card is None or card["kind"] != "workspace":
        raise ValueError("Select an External workspace card.")
    if execution:
        if execution.get("card") != card_id or execution.get("graph") != graph:
            raise ValueError("The selected execution does not belong to this card.")
        if execution.get("child_source"):
            return Path(execution["child_source"]).resolve()
    path = card.get("config", {}).get("path")
    if not isinstance(path, str) or not path.strip():
        raise ValueError(
            "Choose a child workflow path. Dynamic paths can be opened after the call resolves them during a run."
        )
    workspace = (parent.parent / raw.get("workspace", ".")).resolve()
    if not workspace.is_dir():
        raise ValueError("The parent workflow's execution workspace does not exist.")
    return (workspace / path).resolve()
