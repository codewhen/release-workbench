"""Disposable browser fixtures; never touch the user's installation or workflows."""
import sys
from pathlib import Path
import tempfile
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/"src"))
from release_workbench.interfaces.server import serve
with tempfile.TemporaryDirectory(prefix="workbench-browser-") as name:
    root=Path(name);project=root/"projects";project.mkdir()
    serve(project,root/"storage",3115,False)
