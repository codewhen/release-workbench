"""Explicit, bounded discovery commands for trusted local workflow inputs."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from release_workbench.domain.values import TypedValue

from .documents import compile_document
from .evidence import SecretMasker
from .services import LocalServices


def discover(raw: dict[str, Any], directory: Path, services: LocalServices) -> dict[str, Any]:
    compile_document(raw)
    config = raw.get("input_detection")
    if not config:
        raise ValueError("No input discovery command is configured.")
    argv = [sys.executable if isinstance(arg, dict) else arg for arg in config["argv"]]
    root = (directory / raw.get("workspace", ".")).resolve()
    result = asyncio.run(
        services.process.run(
            argv,
            root,
            services.environment(compile_document(raw)),
            None,
            lambda text: None,
            lambda: None,
            config.get("timeout", 30),
        )
    )
    if result.get("truncated"):
        raise ValueError("Input discovery output was truncated.")
    data = json.loads(result["stdout"])
    if not isinstance(data, dict):
        raise ValueError("Input discovery must return a JSON object.")
    warnings = data.get("warnings", [])
    if not isinstance(warnings, list) or any(not isinstance(item, str) for item in warnings):
        raise ValueError("Discovery warnings must be a list of strings.")
    candidates: dict[str, list[dict[str, Any]]] = {}
    for name, definition in raw.get("inputs", {}).items():
        items = data.get(name, [])
        if not isinstance(items, list):
            raise ValueError(f"Discovery candidates for {name} must be an array.")
        candidates[name] = []
        for item in items:
            if not isinstance(item, dict) or "value" not in item:
                raise ValueError(f"Invalid discovery candidate for {name}.")
            value = item["value"]
            # OS process tools conventionally serialize PIDs as decimal text.
            if definition["type"] == "number" and isinstance(value, str) and value.isdecimal():
                value = int(value)
            TypedValue.checked(value, definition["type"])
            candidates[name].append(
                {
                    "value": value,
                    "label": str(item.get("label", value)),
                    "automatic": item.get("automatic", True) is True,
                }
            )
    masker = SecretMasker(
        [
            services.environment(compile_document(raw)).get(name, "")
            for name in raw.get("secrets", [])
        ]
    )
    return dict(masker.object({"candidates": candidates, "warnings": warnings}))
