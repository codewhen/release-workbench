"""Preview-only multi-project workflow library; organizing entries never moves files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from release_workbench.application.starters import starter

from .documents import (
    DocumentStore,
    atomic_write,
    compile_document,
    digest,
    render_document,
)


class Library:
    def __init__(self, storage: Path, project: Path):
        self.storage = storage.resolve()
        self.path = self.storage / "library.json"
        self.data = (
            json.loads(self.path.read_text())
            if self.path.exists()
            else {"projects": [], "entries": [], "folders": []}
        )
        self.register_project(project)

    def save(self) -> None:
        atomic_write(self.path, json.dumps(self.data, indent=2))

    def register_project(self, project: Path) -> None:
        project = project.resolve()
        if not project.is_dir():
            raise ValueError("Project folder does not exist.")
        if str(project) not in self.data["projects"]:
            self.data["projects"].append(str(project))
        for file in sorted([*project.glob("*.yaml"), *project.glob("*.yml")]):
            self.register(file, validate=False)
        self.save()

    def register(self, file: Path, validate: bool = True) -> dict[str, Any]:
        file = file.resolve()
        if validate:
            compile_document(DocumentStore(file).read()["workflow"])
        key = digest(str(file).encode())[:20]
        entry = next((item for item in self.data["entries"] if item["id"] == key), None)
        if entry is None:
            entry = {"id": key, "path": str(file), "folder": ""}
            self.data["entries"].append(entry)
        self.save()
        return entry

    def file(self, key: str) -> Path:
        entry = next((item for item in self.data["entries"] if item["id"] == key), None)
        if not entry:
            raise ValueError("Workflow is not registered in this preview library.")
        return Path(entry["path"])

    def listing(self) -> dict[str, Any]:
        entries = []
        for item in self.data["entries"]:
            try:
                record = DocumentStore(Path(item["path"])).read()
                raw = record["workflow"]
                supported = raw.get("version") == 3
                entries.append(
                    {
                        **item,
                        "name": raw.get("name", Path(item["path"]).stem),
                        "supported": supported,
                        "error": None
                        if supported
                        else "Unsupported version; this preview requires schema v3.",
                    }
                )
            except Exception as error:
                entries.append(
                    {
                        **item,
                        "name": Path(item["path"]).stem,
                        "supported": False,
                        "error": str(error),
                    }
                )
        return {**self.data, "entries": entries}

    def create(self, project: Path, filename: str, name: str, template: str) -> dict[str, Any]:
        project = project.resolve()
        if str(project) not in self.data["projects"]:
            self.register_project(project)
        if Path(filename).name != filename or not filename.endswith((".yaml", ".yml")):
            raise ValueError("Use a YAML filename without directory components.")
        file = project / filename
        value = starter(name, template)
        compile_document(value)
        with file.open("x") as stream:
            stream.write(render_document(value))
        return self.register(file)
