"""Execute documentation downloads in disposable workspaces with synthetic fixtures."""

from __future__ import annotations

import asyncio
import importlib.util
import shutil
import sys
import tempfile
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from release_workbench.application.runtime import Run  # noqa: E402 — standalone script resolves the checkout before imports.
from release_workbench.infrastructure.discovery import discover  # noqa: E402 — standalone script resolves the checkout before imports.
from release_workbench.infrastructure.documents import DocumentStore, compile_document  # noqa: E402 — standalone script resolves the checkout before imports.
from release_workbench.infrastructure.services import LocalServices  # noqa: E402 — standalone script resolves the checkout before imports.


async def execute(file: Path, root: Path, url: str, answer: bool = True) -> Run:
    raw = DocumentStore(file).read()["workflow"]
    for graph in raw["graphs"].values():
        for card in graph["cards"]:
            if card["kind"] == "program":
                card["config"]["argv"][0] = sys.executable
    inputs = {"url": url} if "url" in raw.get("inputs", {}) else {}
    run = Run(
        compile_document(raw), root, root / "evidence", LocalServices(), inputs, interactive=True
    )

    async def answer_prompts() -> None:
        while True:
            for path, pending in list(run.evidence.state["manual"].items()):
                if path not in run.manual_answers:
                    run.record(
                        path,
                        "Synthetic documentation check",
                        answer if pending["mode"] == "decision" else None,
                    )
            await asyncio.sleep(0.01)

    responder = asyncio.create_task(answer_prompts())
    try:
        code = await asyncio.wait_for(run.execute(), 25)
    finally:
        responder.cancel()
        await asyncio.gather(responder, return_exceptions=True)
    if code != 0:
        raise AssertionError(f"{file.name}: {run.evidence.state.get('error')}")
    assert (run.evidence.directory / "report.html").is_file()
    return run


def main() -> None:
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location(
        "doc_http_fixture", ROOT / "docs/examples/http_fixture.py"
    )
    assert spec and spec.loader
    fixture = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fixture)
    server = ThreadingHTTPServer(("127.0.0.1", 0), fixture.Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    count = 0
    try:
        for source in sorted((ROOT / "docs/examples").glob("*.yaml")):
            with tempfile.TemporaryDirectory(prefix="workbench-doc-example-") as directory:
                root = Path(directory)
                for companion in (ROOT / "docs/examples").iterdir():
                    if companion.is_file():
                        shutil.copy2(companion, root / companion.name)
                (root / "ready.txt").write_text("ready", encoding="utf-8")
                if source.stem == "input-discovery":
                    raw = DocumentStore(root / source.name).read()["workflow"]
                    discovered = discover(raw, root, LocalServices())
                    assert discovered["candidates"]["target"][0]["value"] == "."
                    workers = discovered["candidates"]["workers"][0]["value"]
                    assert type(workers) is int and 1 <= workers <= 4
                    assert len(discovered["candidates"]["profile"]) == 2
                    assert all(
                        not candidate["automatic"]
                        for candidate in discovered["candidates"]["profile"]
                    )
                    assert discovered["warnings"]
                run = asyncio.run(
                    execute(
                        root / source.name, root, f"http://127.0.0.1:{server.server_port}/health"
                    )
                )
                state = run.evidence.state
                if source.stem in ("loop", "starter-while"):
                    assert state["globals"]["count"] == 3
                if source.stem == "finish":
                    assert state["result"] == {"type": "boolean", "value": False}
                if source.stem in ("start", "starter-blank"):
                    assert state["result"] == {"type": "void"}
                if source.stem == "input-discovery":
                    assert state["result"]["value"] == {
                        "target": ".",
                        "workers": 1,
                        "profile": "quick",
                        "dry_run": True,
                    }
                if source.stem == "http-io":
                    assert state["result"]["value"] == {"ok": True, "service": "documentation"}
                if source.stem == "workspace":
                    assert state["result"]["value"] == {"greeting": "Hello child"}
                if source.stem in ("manual", "starter-manual"):
                    negative = asyncio.run(execute(root / source.name, root, "", False))
                    assert (
                        negative.evidence.state["executions"]["root/main/work"]["status"]
                        == "skipped"
                    )
                print("Passed example:", source.name)
                count += 1
    finally:
        server.shutdown()
        server.server_close()
    print(
        f"{count} documented workflows executed; False/Void, manual decisions, globals, HTTP and child returns verified."
    )


if __name__ == "__main__":
    main()
