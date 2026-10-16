import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from release_workbench.infrastructure.documents import DocumentStore
from release_workbench.infrastructure.library import Library
from release_workbench.infrastructure.projects import register_starters
from release_workbench.interfaces.cli import main


class CliTests(unittest.TestCase):
    def invoke(self, arguments):
        with patch.object(sys, "argv", ["workbench", *arguments]):
            main()

    def test_primary_commands_start_dashboard_without_running_workflows(self):
        for arguments in ([], ["serve"], ["run"], ["--no-open"]):
            with (
                self.subTest(arguments=arguments),
                patch("release_workbench.interfaces.cli.serve") as serve,
            ):
                self.invoke(arguments)
                serve.assert_called_once()

    def test_create_wizard_writes_current_directory_and_opens_workflow(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            with (
                patch("release_workbench.interfaces.cli.Path.cwd", return_value=root),
                patch("builtins.input", side_effect=["My project", "mine.yaml"]),
                patch("release_workbench.interfaces.cli.serve") as serve,
            ):
                self.invoke(["create", "--storage", str(root / "store")])
                raw = DocumentStore(root / "mine.yaml").read()["workflow"]
                self.assertEqual(raw["name"], "My project")
                self.assertEqual(
                    [c["kind"] for c in raw["graphs"]["main"]["cards"]], ["start", "finish"]
                )
                self.assertEqual(serve.call_args.args[0], root.resolve())
                self.assertTrue(serve.call_args.args[-1])
            with (
                patch("release_workbench.interfaces.cli.Path.cwd", return_value=root),
                patch("release_workbench.interfaces.cli.serve") as serve,
            ):
                with self.assertRaises(SystemExit) as result:
                    self.invoke(
                        [
                            "create",
                            "--name",
                            "Other",
                            "--config",
                            "mine.yaml",
                            "--storage",
                            str(root / "store"),
                        ]
                    )
                self.assertEqual(result.exception.code, 2)
                serve.assert_not_called()
            self.assertEqual(
                DocumentStore(root / "mine.yaml").read()["workflow"]["name"], "My project"
            )

    def test_starters_have_separate_project_and_are_never_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            library = Library(root / "store", root)
            register_starters(library)
            entries = library.listing()["entries"]
            self.assertEqual(len(entries), 7)
            self.assertTrue(all(entry["folder"] == "Starter" for entry in entries))
            file = Path(entries[0]["path"])
            original = file.read_text()
            file.write_text(original + "\n# Keep my edits\n")
            register_starters(library)
            self.assertTrue(file.read_text().endswith("# Keep my edits\n"))
            self.assertEqual(len(library.listing()["entries"]), 7)
            self.assertFalse(list(root.glob("*.yaml")))
