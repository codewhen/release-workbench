import tempfile
import unittest
from pathlib import Path

from release_workbench.interfaces.documentation import documentation_file


class DocumentationTests(unittest.TestCase):
    def test_deep_links_downloads_and_unknown_pages(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            (root / "user/cards").mkdir(parents=True)
            (root / "index.html").write_text("Manual")
            (root / "404.html").write_text("Page not found")
            (root / "user/cards/python.html").write_text("Python guide")
            (root / "example.yaml").write_text("version: 3")
            for name in (
                "",
                "index.html",
                "user/cards/python",
                "user/cards/python.html",
                "example.yaml",
            ):
                file, status = documentation_file(name, root)
                self.assertEqual(status, 200)
                self.assertTrue(file.is_file())
            file, status = documentation_file("missing", root)
            self.assertEqual(status, 404)
            self.assertEqual(file, root / "404.html")
            self.assertEqual(documentation_file("../private.json", root), (None, 404))

    def test_symlinks_cannot_expose_adjacent_files(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = base / "docs"
            root.mkdir()
            secret = base / "private.txt"
            secret.write_text("private fixture")
            try:
                (root / "leak.txt").symlink_to(secret)
                (root / "404.html").symlink_to(secret)
            except OSError:
                self.skipTest("Symlinks unavailable for this user/platform")
            self.assertEqual(documentation_file("leak.txt", root), (None, 404))
            self.assertEqual(documentation_file("unknown", root), (None, 404))
