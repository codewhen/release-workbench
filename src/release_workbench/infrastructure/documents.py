"""Bounded YAML/JSON persistence; saves are atomic and revision checked."""

from __future__ import annotations

import hashlib
import io
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from ruamel.yaml import YAML

from release_workbench.application.compiler import CompilationError, Compiler
from release_workbench.domain.models import Workflow

MAX_BYTES = 1024 * 1024
SCHEMA_PATH = Path(__file__).resolve().parents[1] / "schema.json"
SCHEMA = json.loads(SCHEMA_PATH.read_text())


def digest(value: Any) -> str:
    data = (
        value
        if isinstance(value, bytes)
        else json.dumps(value, sort_keys=True, allow_nan=False).encode()
    )
    return hashlib.sha256(data).hexdigest()


def parse_document(text: str) -> dict[str, Any]:
    if len(text.encode()) > MAX_BYTES:
        raise ValueError("Workflow exceeds 1 MiB.")
    from ruamel.yaml.tokens import AliasToken, TagToken

    codec = YAML(typ="safe")
    if any(isinstance(token, (AliasToken, TagToken)) for token in codec.scan(text)):
        raise ValueError("YAML aliases and tags are not supported.")
    value = codec.load(text)
    if not isinstance(value, dict):
        raise ValueError("A workflow must be a YAML object.")
    json.dumps(value, allow_nan=False)
    return value


def render_document(value: dict[str, Any], original: str = "") -> str:
    codec = YAML()
    codec.preserve_quotes = True
    codec.indent(mapping=2, sequence=4, offset=2)
    old = codec.load(original) if original.strip() else None

    def merge(previous: Any, current: Any) -> Any:
        if isinstance(previous, dict) and isinstance(current, dict):
            for key in list(previous):
                if key not in current:
                    del previous[key]
            for key, item in current.items():
                previous[key] = merge(previous.get(key), item)
            return previous
        if isinstance(previous, list) and isinstance(current, list):
            by_id = {v.get("id"): v for v in previous if isinstance(v, dict) and "id" in v}
            previous[:] = [
                merge(by_id.get(item.get("id")) if isinstance(item, dict) else None, item)
                for item in current
            ]
            return previous
        return current

    stream = io.StringIO()
    codec.dump(merge(old, value), stream)
    return stream.getvalue()


def compile_document(raw: dict[str, Any]) -> Workflow:
    if raw.get("version") != 3:
        raise CompilationError(
            [
                "Unsupported workflow version. This preview accepts schema v3 only; the original file was not changed."
            ]
        )
    errors = [
        f"{'.'.join(map(str, error.path))}: {error.message}"
        for error in Draft202012Validator(SCHEMA).iter_errors(raw)
    ]
    if errors:
        raise CompilationError(errors)
    return Compiler().compile(raw)


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(prefix=".workbench-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


class DocumentStore:
    def __init__(self, path: Path):
        self.path = path.resolve()

    def read(self) -> dict[str, Any]:
        if self.path.stat().st_size > MAX_BYTES:
            raise ValueError("Workflow exceeds 1 MiB.")
        text = self.path.read_text()
        return {
            "workflow": parse_document(text),
            "yaml": text,
            "revision": digest(text.encode()),
            "path": str(self.path),
        }

    def save(self, text: str, revision: str) -> dict[str, Any]:
        current = self.read()
        if current["revision"] != revision:
            raise ValueError("This workflow changed outside the editor. Reload before saving.")
        compile_document(parse_document(text))
        atomic_write(self.path, text)
        return self.read()
