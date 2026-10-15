"""Localhost-only HTTP adapter. Execution and validation belong to application services."""

from __future__ import annotations

import difflib
import json
import mimetypes
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlsplit

from release_workbench.application.compiler import CompilationError
from release_workbench.application.runtime import Run
from release_workbench.application.starters import TEMPLATES
from release_workbench.domain.cards import REGISTRY
from release_workbench.infrastructure.documents import (
    MAX_BYTES,
    SCHEMA,
    DocumentStore,
    compile_document,
    document_readiness,
    parse_document,
    render_document,
    validate_document_schema,
)
from release_workbench.infrastructure.drafts import DraftStore
from release_workbench.infrastructure.library import Library
from release_workbench.infrastructure.services import LocalServices
from release_workbench.infrastructure.sessions import LocalSessions


class WorkbenchApplication:
    def __init__(self, project: Path, storage: Path):
        self.project, self.storage = project.resolve(), storage.resolve()
        self.library = Library(self.storage, self.project)
        self.services = LocalServices()
        self.drafts = DraftStore(self.storage / "drafts")
        self.runs: dict[str, Run] = {}
        self.lock = threading.RLock()
        self.sessions = LocalSessions(self.storage / "browser-sessions.json")
        self.token = self.sessions.token

    def state(self, key: str) -> dict[str, Any]:
        run = self.runs.get(key)
        return (
            {
                **run.evidence.snapshot(),
                "busy": run.busy,
                "paused": run.coordinator.paused,
            }
            if run
            else {
                "status": "pending",
                "executions": {},
                "manual": {},
                "events": [],
                "busy": False,
                "paused": False,
            }
        )

    def mutation(self, route: str, key: str, data: dict[str, Any]) -> dict[str, Any]:
        with self.lock:
            if route == "register":
                path = Path(data["path"]).expanduser()
                if path.is_dir():
                    self.library.register_project(path)
                    return self.library.listing()
                return self.library.register(path)
            if route == "create":
                return self.library.create(
                    Path(data.get("project", self.project)),
                    data["filename"],
                    data["name"],
                    data.get("template", "blank"),
                )
            if route == "organize":
                action = data["action"]
                if action == "new_folder":
                    folder = data["name"].strip()
                    if not folder or folder in self.library.data["folders"]:
                        raise ValueError("Choose a unique folder name.")
                    self.library.data["folders"].append(folder)
                elif action == "rename_folder":
                    old, new = data["old"], data["name"].strip()
                    if not new or new in self.library.data["folders"]:
                        raise ValueError("Choose a unique folder name.")
                    self.library.data["folders"] = [
                        new if item == old else item for item in self.library.data["folders"]
                    ]
                    for entry in self.library.data["entries"]:
                        if entry["folder"] == old:
                            entry["folder"] = new
                elif action == "move":
                    if data["folder"] and data["folder"] not in self.library.data["folders"]:
                        raise ValueError("Folder does not exist.")
                    for entry in self.library.data["entries"]:
                        if entry["id"] == key:
                            entry["folder"] = data["folder"]
                elif action == "remove_folder":
                    self.library.data["folders"] = [
                        f for f in self.library.data["folders"] if f != data["name"]
                    ]
                    for entry in self.library.data["entries"]:
                        if entry["folder"] == data["name"]:
                            entry["folder"] = ""
                self.library.save()
                return self.library.listing()
            if route == "import":
                raw = parse_document(data["yaml"])
                validate_document_schema(raw)
                project = Path(data.get("project", self.project)).resolve()
                filename = data["filename"]
                entry = self.library.create(project, filename, raw["name"], "blank")
                file = self.library.file(entry["id"])
                from release_workbench.infrastructure.documents import atomic_write

                atomic_write(file, data["yaml"])
                return entry
            file = self.library.file(key)
            store = DocumentStore(file)
            if route in ("validate", "save", "draft"):
                if any(run.busy for run in self.runs.values()):
                    raise ValueError("Editing is disabled during execution.")
                current = store.read()
                raw = data.get("workflow") or parse_document(data["yaml"])
                validate_document_schema(raw)
                validation_errors: list[str] = []
                issues: list[dict[str, str]] = []
                try:
                    compile_document(raw)
                except CompilationError as error:
                    validation_errors, issues = error.errors, error.issues
                    if route == "validate":
                        self.drafts.save(key, raw, current)
                        raise CompilationError(
                            [
                                "Draft backed up. You can save incomplete work in the updated editor; Run still requires the following fixes.",
                                *error.errors,
                            ],
                            error.issues,
                        ) from error
                yaml = render_document(raw, current["yaml"])
                if route == "save":
                    result = store.save(yaml, data["revision"])
                    self.runs.pop(key, None)
                    self.drafts.clear(key)
                    return {
                        **result,
                        "runnable": not validation_errors,
                        "validation_errors": validation_errors,
                        "issues": issues,
                    }
                return {
                    "workflow": raw,
                    "yaml": yaml,
                    "runnable": not validation_errors,
                    "validation_errors": validation_errors,
                    "issues": issues,
                    "diff": "".join(
                        difflib.unified_diff(
                            current["yaml"].splitlines(True),
                            yaml.splitlines(True),
                            fromfile="Saved",
                            tofile="Draft",
                        )
                    ),
                }
            if route == "run":
                if any(run.busy for run in self.runs.values()):
                    raise ValueError(
                        "Another workflow is executing. Stop it or wait before starting another."
                    )
                record = store.read()
                if data.get("revision") != record["revision"]:
                    raise ValueError("Configuration changed. Save/reload before running.")
                workflow = compile_document(record["workflow"])
                run = Run(
                    workflow,
                    file.parent,
                    self.storage / "runs",
                    self.services,
                    data.get("inputs", {}),
                    interactive=True,
                    resume=data.get("resume"),
                    retry=data.get("retry", False),
                    stack=(file,),
                )
                self.runs[key] = run
                run.start()
            elif route == "stop":
                self.runs[key].stop(data.get("execution"))
            elif route == "pause":
                self.runs[key].coordinator.paused = bool(data["paused"])
            elif route == "record":
                self.runs[key].record(data["execution"], data["note"], data.get("decision"))
            else:
                raise ValueError("Unknown action.")
            return self.state(key)


def create_server(
    project: Path, storage: Path, port: int = 0
) -> tuple[ThreadingHTTPServer, WorkbenchApplication]:
    """Construct a disposable server without starting it, for hosts and acceptance tests."""
    app = WorkbenchApplication(project, storage)
    static = Path(__file__).resolve().parents[1] / "static"

    class Handler(BaseHTTPRequestHandler):
        server: ThreadingHTTPServer

        def log_message(self, format: str, *args: Any) -> None:
            pass

        def send(
            self, data: bytes, status: int = 200, content_type: str = "application/json"
        ) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.end_headers()
            self.wfile.write(data)

        def json(self, data: Any, status: int = 200) -> None:
            self.send(json.dumps(data, allow_nan=False).encode(), status)

        def authorized_host(self) -> bool:
            return self.headers.get("Host") in (
                f"127.0.0.1:{self.server.server_port}",
                f"localhost:{self.server.server_port}",
            )

        def do_GET(self) -> None:
            if not self.authorized_host():
                self.json({"error": "Localhost access only."}, 403)
                return
            parsed = urlsplit(self.path)
            key = parse_qs(parsed.query).get("workflow", [""])[0]
            route = parsed.path
            try:
                if route == "/api/library":
                    self.json(app.library.listing())
                elif route == "/api/catalog":
                    self.json(
                        {
                            "cards": [spec.metadata() for spec in REGISTRY.values()],
                            "templates": TEMPLATES,
                            "schema": SCHEMA,
                        }
                    )
                elif route == "/api/schema":
                    self.json(SCHEMA)
                elif route == "/api/config":
                    record = DocumentStore(app.library.file(key)).read()
                    self.json(
                        {
                            **record,
                            **document_readiness(record["workflow"]),
                            "recovery": app.drafts.matching(key, record["revision"]),
                        }
                    )
                elif route == "/api/state":
                    self.json(app.state(key))
                elif route == "/api/history":
                    records = []
                    for file in sorted((app.storage / "runs").glob("*/summary.json"), reverse=True):
                        value = json.loads(file.read_text())
                        records.append(
                            {k: value[k] for k in ("run_id", "name", "status", "fingerprint")}
                        )
                    self.json(records)
                elif route.startswith("/api/"):
                    self.json({"error": "Unknown endpoint."}, 404)
                else:
                    base = app.storage / "runs" if route.startswith("/reports/") else static
                    name = unquote(
                        route[len("/reports/") :]
                        if route.startswith("/reports/")
                        else route.lstrip("/") or "index.html"
                    )
                    file = (base / name).resolve()
                    if not file.is_relative_to(base.resolve()) or not file.is_file():
                        self.json({"error": "File not found."}, 404)
                        return
                    content = file.read_bytes()
                    if file.name == "index.html":
                        content = content.replace(b"__TOKEN__", app.token.encode())
                    self.send(
                        content,
                        content_type=mimetypes.guess_type(file.name)[0]
                        or "application/octet-stream",
                    )
            except Exception as error:
                self.json(
                    {
                        "error": str(error),
                        "issues": error.issues if isinstance(error, CompilationError) else [],
                    },
                    400,
                )

        def do_POST(self) -> None:
            origin = self.headers.get("Origin")
            if (
                not self.authorized_host()
                or not app.sessions.accepts(self.headers.get("X-Workbench-Token"))
                or origin
                not in (
                    None,
                    f"http://localhost:{self.server.server_port}",
                    f"http://127.0.0.1:{self.server.server_port}",
                )
            ):
                self.json({"error": "Invalid local request token or origin."}, 403)
                return
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size <= MAX_BYTES:
                    raise ValueError("Request body must be between 1 byte and 1 MiB.")
                data = json.loads(self.rfile.read(size))
                parsed = urlsplit(self.path)
                key = parse_qs(parsed.query).get("workflow", [""])[0]
                self.json(app.mutation(parsed.path.removeprefix("/api/"), key, data))
            except Exception as error:
                self.json(
                    {
                        "error": str(error),
                        "issues": error.issues if isinstance(error, CompilationError) else [],
                    },
                    400,
                )

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.daemon_threads = True
    return server, app


def serve(project: Path, storage: Path, port: int = 3104, open_browser: bool = True) -> None:
    server, app = create_server(project, storage, port)
    print(f"Workflow Workbench v3 preview: http://127.0.0.1:{port}/", flush=True)
    print(f"Isolated preview storage: {storage}", flush=True)
    if open_browser:
        import webbrowser

        webbrowser.open(f"http://127.0.0.1:{port}/")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        for run in app.runs.values():
            if run.busy:
                run.stop()
        for run in app.runs.values():
            if run.thread:
                run.thread.join(timeout=10)
    finally:
        server.server_close()
