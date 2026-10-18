"""Nested metadata folders preserve files and validate whole-subtree operations."""

import copy
import tempfile
import unittest
from pathlib import Path

from release_workbench.domain.library_folders import FolderOrganizer
from release_workbench.infrastructure.library import Library
from release_workbench.infrastructure.projects import register_starters


class LibraryFolders(unittest.TestCase):
    def setUp(self):
        self.data = {
            "folders": ["Tests", "Tests/Phone", "Tests/Phone/Recovery", "Builds"],
            "entries": [
                {"id": "one", "folder": "Tests/Phone/Recovery", "path": "/synthetic/workflow.yaml"}
            ],
        }

    def apply(self, action, **request):
        return FolderOrganizer(self.data).apply(action, "one", request)

    def test_same_leaf_names_allowed_in_distinct_parents(self):
        result = self.apply("new_folder", name="Phone", parent="Builds")
        self.assertIn("Builds/Phone", result["folders"])
        self.assertNotIn("Builds/Phone", self.data["folders"])

    def test_rename_and_move_preserve_whole_subtree_memberships(self):
        result = self.apply("rename_folder", old="Tests/Phone", name="Android")
        self.assertEqual(result["entries"][0]["folder"], "Tests/Android/Recovery")
        self.assertIn("Tests/Android/Recovery", result["folders"])
        result = self.apply("move_folder", old="Tests/Phone", parent="Builds")
        self.assertEqual(result["entries"][0]["folder"], "Builds/Phone/Recovery")

    def test_cycle_collision_and_missing_parent_leave_original_unchanged(self):
        original = copy.deepcopy(self.data)
        for action, request in [
            ("move_folder", {"old": "Tests", "parent": "Tests/Phone"}),
            ("rename_folder", {"old": "Tests", "name": "Builds"}),
            ("new_folder", {"name": "Phone", "parent": "Tests"}),
            ("new_folder", {"name": "Other", "parent": "missing"}),
            ("new_folder", {"name": "../escape"}),
            ("move", {"folder": "missing"}),
        ]:
            with self.subTest(action=action, request=request), self.assertRaises(ValueError):
                self.apply(action, **request)
            self.assertEqual(self.data, original)

    def test_remove_subtree_returns_workflows_to_parent(self):
        result = self.apply("remove_folder", name="Tests/Phone")
        self.assertEqual(result["folders"], ["Tests", "Builds"])
        self.assertEqual(result["entries"][0]["folder"], "Tests")
        result = self.apply("remove_folder", name="Tests")
        self.assertEqual(result["entries"][0]["folder"], "")

    def test_moves_survive_restart_without_changing_yaml(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            library = Library(root / "storage", root)
            entry = library.create(root, "demo.yaml", "Demo", "blank")
            before = (root / "demo.yaml").read_bytes()
            library.organize("new_folder", "", {"name": "Tests"})
            library.organize("new_folder", "", {"name": "Phone", "parent": "Tests"})
            library.organize("move", entry["id"], {"folder": "Tests/Phone"})
            library.organize("rename_folder", "", {"old": "Tests", "name": "Checks"})
            restored = Library(root / "storage", root)
            self.assertEqual(restored.listing()["entries"][0]["folder"], "Checks/Phone")
            self.assertEqual((root / "demo.yaml").read_bytes(), before)

    def test_starter_organization_is_not_reset_on_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            library = Library(root / "storage", root)
            register_starters(library)
            library.organize("new_folder", "", {"name": "Examples"})
            library.organize("move_folder", "", {"old": "Starter", "parent": "Examples"})
            restored = Library(root / "storage", root)
            register_starters(restored)
            self.assertNotIn("Starter", restored.data["folders"])
            self.assertTrue(
                all(entry["folder"] == "Examples/Starter" for entry in restored.data["entries"])
            )
