"""Disposable documentation screenshot/browser fixture server."""

import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from release_workbench.interfaces.server import serve

root = Path(__file__).resolve().parents[2]
with tempfile.TemporaryDirectory(prefix="workbench-docs-") as directory:
    project = Path(directory) / "project"
    shutil.copytree(
        root / "docs/examples", project, ignore=shutil.ignore_patterns("__pycache__", "*.pyc")
    )
    serve(project, Path(directory) / "storage", 3117, False)
