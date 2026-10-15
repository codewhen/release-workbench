"""Disposable browser fixtures; never touch the user's installation or workflows."""
import sys
from pathlib import Path
import tempfile
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/"src"))
from release_workbench.application.starters import starter,TEMPLATES
from release_workbench.infrastructure.documents import render_document
from release_workbench.interfaces.server import serve
with tempfile.TemporaryDirectory(prefix="workbench-browser-") as name:
    root=Path(name);project=root/"projects";project.mkdir()
    for key,title in TEMPLATES.items():
        (project/(key+".yaml")).write_text(render_document(starter(title,key)))
    serve(project,root/"storage",3115,False)
