import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from release_workbench.application.starters import starter
from release_workbench.infrastructure.documents import render_document
from release_workbench.interfaces.server import WorkbenchApplication


class LibraryRemoval(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.project = self.root / "project"
        self.project.mkdir()
        self.file = self.project / "flow.yaml"
        self.file.write_text(render_document(starter("Example")))
        self.storage = self.root / "storage"
        self.app = WorkbenchApplication(self.project, self.storage)
        self.key = self.app.library.register(self.file)["id"]

    def test_remove_file_preserves_disk_and_survives_restart_until_readded(self):
        report = self.storage / "runs" / "evidence.json"
        report.parent.mkdir()
        report.write_text("saved")
        self.app.mutation("remove", self.key, {})
        self.assertTrue(self.file.exists())
        self.assertEqual(report.read_text(), "saved")
        restarted = WorkbenchApplication(self.project, self.storage)
        self.assertNotIn(self.key, {item["id"] for item in restarted.library.listing()["entries"]})
        restarted.mutation("register", "", {"path": str(self.file)})
        self.assertEqual(restarted.library.file(self.key), self.file)

    def test_project_removal_includes_nested_entries_not_sibling_prefixes(self):
        nested = self.project / "nested"
        nested.mkdir()
        child = nested / "child.yaml"
        child.write_text(self.file.read_text())
        child_key = self.app.library.register(child)["id"]
        sibling = self.root / "project-other"
        sibling.mkdir()
        self.app.library.register_project(sibling)
        self.app.mutation("remove", "", {"project": str(self.project)})
        restarted = WorkbenchApplication(self.project, self.storage)
        self.assertNotIn(str(self.project), restarted.library.data["projects"])
        self.assertIn(str(sibling), restarted.library.data["projects"])
        self.assertNotIn(child_key, {item["id"] for item in restarted.library.data["entries"]})
        self.assertTrue(child.exists())
        restarted.library.register_project(self.project)
        self.assertEqual(restarted.library.file(self.key), self.file)

    def test_active_run_blocks_removal_and_unknown_target_is_rejected(self):
        self.app.runs[self.key] = SimpleNamespace(busy=True)
        for key, data in ((self.key, {}), ("", {"project": str(self.project)})):
            with self.assertRaisesRegex(ValueError, "Stop active runs"):
                self.app.mutation("remove", key, data)
        self.assertTrue(self.app.library.file(self.key).exists())
        with self.assertRaises(ValueError):
            self.app.mutation("remove", "unknown", {})
        with self.assertRaises(ValueError):
            self.app.mutation("remove", "", {"project": str(self.root)})

    def test_removed_starter_is_not_automatically_restored(self):
        starter_project = self.storage / "projects" / "starter"
        self.app.mutation("remove", "", {"project": str(starter_project)})
        restarted = WorkbenchApplication(self.project, self.storage)
        self.assertNotIn(str(starter_project), restarted.library.data["projects"])
        restarted.mutation("register", "", {"path": str(starter_project)})
        self.assertIn(str(starter_project), restarted.library.data["projects"])
