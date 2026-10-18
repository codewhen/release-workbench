"""Project creation and isolated, non-overwriting starter installation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from release_workbench.application.starters import TEMPLATES, starter

from .documents import render_document
from .library import Library


def register_starters(library: Library) -> None:
    project = library.storage / "projects" / "starter"
    project.mkdir(parents=True, exist_ok=True)
    for template, name in TEMPLATES.items():
        file = project / (template + ".yaml")
        try:
            with file.open("x", encoding="utf-8") as stream:
                stream.write(render_document(starter(name, template)))
        except FileExistsError:
            pass
    existing = {entry["id"] for entry in library.data["entries"]}
    library.register_project(project, restore=False)
    new_entries = [
        entry
        for entry in library.data["entries"]
        if entry["id"] not in existing and Path(entry["path"]).parent == project
    ]
    if new_entries and "Starter" not in library.data["folders"]:
        library.data["folders"].append("Starter")
    for entry in new_entries:
        entry["folder"] = "Starter"
    library.save()


def create_project(root: Path, filename: Path, name: str, storage: Path) -> dict[str, Any]:
    if filename.is_absolute() or len(filename.parts) != 1:
        raise ValueError("Choose a YAML filename in the current directory.")
    library = Library(storage, root)
    return library.create(root, str(filename), name, "blank")
