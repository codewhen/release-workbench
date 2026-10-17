"""Logical library folders; these paths never address the filesystem."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


def inside(folder: str, ancestor: str) -> bool:
    return folder == ancestor or folder.startswith(ancestor + "/")


class FolderOrganizer:
    """Validate an entire metadata edit before returning its replacement."""

    def __init__(self, data: dict[str, Any]):
        self.data = deepcopy(data)
        self.folders: list[str] = self.data["folders"]

    def require(self, path: str) -> None:
        if path and path not in self.folders:
            raise ValueError("Folder does not exist.")

    def destination(self, parent: str, name: str) -> str:
        self.require(parent)
        name = name.strip()
        if not name or name in {".", "..", "*"} or any(c in name for c in "/\\\x00"):
            raise ValueError("Enter a folder name without path separators or reserved names.")
        return parent + "/" + name if parent else name

    def relocate(self, old: str, new: str) -> None:
        self.require(old)
        if not old:
            raise ValueError("Choose an existing folder.")
        if new == old:
            return
        if inside(new, old):
            raise ValueError("A folder cannot be moved into itself or one of its subfolders.")
        mapping = {path: new + path[len(old) :] for path in self.folders if inside(path, old)}
        if set(mapping.values()) & (set(self.folders) - set(mapping)):
            raise ValueError("A folder with that name already exists at the destination.")
        self.data["folders"] = [mapping.get(path, path) for path in self.folders]
        for entry in self.data["entries"]:
            entry["folder"] = mapping.get(entry["folder"], entry["folder"])

    def apply(self, action: str, key: str, request: dict[str, Any]) -> dict[str, Any]:
        if action == "new_folder":
            path = self.destination(request.get("parent", ""), request["name"])
            if path in self.folders:
                raise ValueError("A folder with that name already exists here.")
            self.folders.append(path)
        elif action in {"rename_folder", "move_folder"}:
            old = request["old"]
            self.require(old)
            parent = (
                old.rpartition("/")[0] if action == "rename_folder" else request.get("parent", "")
            )
            name = request["name"] if action == "rename_folder" else old.rpartition("/")[2]
            self.relocate(old, self.destination(parent, name))
        elif action == "move":
            target = request["folder"]
            self.require(target)
            entry = next((entry for entry in self.data["entries"] if entry["id"] == key), None)
            if entry is None:
                raise ValueError("Workflow is not registered.")
            entry["folder"] = target
        elif action == "remove_folder":
            old = request["name"]
            self.require(old)
            if not old:
                raise ValueError("Choose an existing folder.")
            self.data["folders"] = [path for path in self.folders if not inside(path, old)]
            parent = old.rpartition("/")[0]
            for entry in self.data["entries"]:
                if inside(entry["folder"], old):
                    entry["folder"] = parent
        else:
            raise ValueError("Unknown folder action.")
        return self.data
