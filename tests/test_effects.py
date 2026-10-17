import asyncio
import os
import sys
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import psutil

from release_workbench.application.coordinator import Coordinator
from release_workbench.application.starters import card, starter
from release_workbench.infrastructure.documents import DocumentStore, render_document
from release_workbench.infrastructure.evidence import EvidenceStore, SecretMasker
from tests.support import RunCase, by_id, sequence


class Effects(RunCase):
    async def test_python_return_separate_from_logs_and_serialized_input(self):
        value = "' );raise SystemExit('injected') #"
        raw = sequence(
            card(
                "py",
                "python",
                {"code": "print('logging only')\nreturn inputs['value']", "returns": "string"},
            )
        )
        by_id(raw, "py")["inputs"] = {"value": value}
        run = await self.passed(raw)
        entry = run.evidence.state["executions"]["root/main/py"]
        self.assertEqual(entry["outcome"]["value"]["value"], value)
        self.assertIn("logging only", entry["tail"])

    async def test_program_and_bash_capture(self):
        operations = [
            card(
                "program",
                "program",
                {
                    "argv": [sys.executable, "-c", "import json; print(json.dumps({'answer':42}))"],
                    "capture": "json",
                },
            )
        ]
        if os.name != "nt":
            operations.append(card("bash", "bash", {"code": "printf 'hello'", "capture": "text"}))
        run = await self.passed(sequence(*operations))
        self.assertEqual(
            run.evidence.state["executions"]["root/main/program"]["outcome"]["value"]["value"][
                "json"
            ]["answer"],
            42,
        )

    async def test_script_file_receives_json_stdin_and_cwd(self):
        (self.root / "script.py").write_text(
            "import json,sys\nprint(json.dumps(json.load(sys.stdin)['inputs']))"
        )
        raw = sequence(
            card("script", "script", {"path": "script.py", "language": "python", "capture": "json"})
        )
        by_id(raw, "script")["inputs"] = {"n": 3}
        run = await self.passed(raw)
        self.assertEqual(
            run.evidence.state["executions"]["root/main/script"]["outcome"]["value"]["value"][
                "json"
            ],
            {"n": 3},
        )

    async def test_file_roundtrip_and_escape_rejected(self):
        raw = sequence(
            card(
                "write",
                "write_file",
                {"path": "data/a.json", "format": "json", "value": {"ok": True}},
            ),
            card("read", "read_file", {"path": "data/a.json", "format": "json"}),
            card("check", "check_path", {"path": "data/a.json", "type": "file"}),
        )
        run = await self.passed(raw)
        self.assertEqual(
            run.evidence.state["executions"]["root/main/read"]["outcome"]["value"]["value"],
            {"ok": True},
        )
        bad = sequence(card("escape", "read_file", {"path": "../secret"}))
        run = self.make(bad)
        self.assertEqual(await run.execute(), 1)
        self.assertIn("workspace", run.evidence.state["error"])

    async def test_invalid_json_file_fails(self):
        (self.root / "bad.json").write_text("not json")
        run = self.make(sequence(card("read", "read_file", {"path": "bad.json", "format": "json"})))
        self.assertEqual(await run.execute(), 1)

    async def test_output_limit_and_invalid_program_json(self):
        for code, capture in (
            ("print('x' * 1100000)", "text"),
            ("print('hello')", "json"),
            ("raise SystemExit(3)", "text"),
        ):
            raw = sequence(
                card("bad", "program", {"argv": [sys.executable, "-c", code], "capture": capture})
            )
            run = self.make(raw)
            self.assertEqual(await run.execute(), 1)

    async def test_timeout_and_process_tree_cleanup(self):
        pidfile = self.root / "pid"
        source = "import subprocess,sys,time\nfrom pathlib import Path\np=subprocess.Popen([sys.executable,'-c','import time;time.sleep(60)'],start_new_session=True)\nPath('pid').write_text(str(p.pid))\ntime.sleep(60)"
        raw = sequence(card("process", "python", {"code": source}))
        by_id(raw, "process")["settings"] = {"timeout": 0.3}
        run = self.make(raw)
        self.assertEqual(await run.execute(), 1)
        self.assertTrue(pidfile.exists())
        pid = int(pidfile.read_text())
        await asyncio.sleep(0.1)
        self.assertTrue(
            not psutil.pid_exists(pid) or psutil.Process(pid).status() == psutil.STATUS_ZOMBIE
        )

    async def test_cancel_process(self):
        raw = sequence(
            card("process", "python", {"code": "import time\ntime.sleep(60)\nreturn True"})
        )
        run = self.make(raw)
        task = asyncio.create_task(run.execute())
        await asyncio.sleep(0.1)
        run.stop()
        self.assertEqual(await asyncio.wait_for(task, 3), 130)

    async def test_http_success_failure_timeout_and_cancel(self):
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                if self.path == "/slow":
                    time.sleep(0.6)
                status = 503 if self.path == "/bad" else 200
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                try:
                    self.wfile.write(b'{"ok":true}')
                except (BrokenPipeError, ConnectionResetError):
                    pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        base = f"http://127.0.0.1:{server.server_port}"
        run = await self.passed(sequence(card("request", "http", {"url": base})))
        self.assertTrue(
            run.evidence.state["executions"]["root/main/request"]["outcome"]["value"]["value"][
                "json"
            ]["ok"]
        )
        for path in ("/bad", "/slow"):
            raw = sequence(card("request", "http", {"url": base + path}))
            by_id(raw, "request")["settings"] = {"timeout": 0.15}
            run = self.make(raw)
            self.assertEqual(await run.execute(), 1)
        raw = sequence(card("request", "http", {"url": base + "/slow"}))
        run = self.make(raw)
        task = asyncio.create_task(run.execute())
        await asyncio.sleep(0.1)
        run.stop()
        self.assertEqual(await asyncio.wait_for(task, 2), 130)

    async def test_secret_masking_across_chunks(self):
        directory = self.root / "secret-evidence"
        store = EvidenceStore(
            directory,
            {
                "executions": {"x": {"status": "passed"}},
                "name": "Secret",
                "run_id": "one",
                "fingerprint": "x",
                "status": "passed",
            },
            SecretMasker(["abc-secret-xyz"]),
        )
        store.log("x", "before abc-sec")
        store.log("x", "ret-xyz after")
        store.emit("value", "x", value="abc-secret-xyz")
        store.report()
        for file in directory.iterdir():
            self.assertNotIn("abc-secret-xyz", file.read_text())
            self.assertNotIn("abc-sec", file.read_text())

    async def test_report_html_escapes_logs_and_values(self):
        raw = sequence(card("py", "python", {"code": "return '<script>alert(1)</script>'"}))
        run = await self.passed(raw)
        page = (run.evidence.directory / "report.html").read_text()
        self.assertNotIn("<script>", page)
        self.assertIn("&lt;script&gt;", page)

    async def test_protected_save_and_comment_preservation(self):
        path = self.root / "workflow.yaml"
        path.write_text("# keep comment\n" + render_document(starter("Save")))
        store = DocumentStore(path)
        record = store.read()
        value = record["workflow"]
        value["name"] = "Updated"
        store.save(render_document(value, record["yaml"]), record["revision"])
        self.assertIn("# keep comment", path.read_text())
        with self.assertRaisesRegex(ValueError, "outside"):
            store.save(record["yaml"], record["revision"])

    async def test_retry_matching_and_redacted_resume(self):
        raw = sequence(card("bad", "python", {"code": "raise ValueError('permanent')"}))
        by_id(raw, "bad")["settings"] = {
            "retry": {"attempts": 3, "delay": 0, "errors_contain": ["temporary"]}
        }
        run = self.make(raw)
        self.assertEqual(await run.execute(), 1)
        self.assertEqual(len(run.evidence.state["executions"]["root/main/bad"]["attempts"]), 1)
        raw = sequence(card("secret", "python", {"code": "return inputs['token']"}))
        raw["environment"] = {"WORKBENCH_TEST_SECRET": "test-secret-value"}
        raw["secrets"] = ["WORKBENCH_TEST_SECRET"]
        by_id(raw, "secret")["inputs"] = {"token": {"$ref": "env:WORKBENCH_TEST_SECRET"}}
        run = await self.passed(raw)
        resumed = self.make(raw, resume=run.evidence.state["run_id"])
        self.assertEqual(await resumed.execute(), 2)
        self.assertNotIn("test-secret-value", (run.evidence.directory / "summary.json").read_text())

    async def test_interrupted_requires_retry_and_source_changes_new_run(self):
        raw = sequence(card("wait", "wait", {"seconds": 0.1}))
        run = self.make(raw)
        task = asyncio.create_task(run.execute())
        await asyncio.sleep(0.02)
        run.stop()
        self.assertEqual(await task, 130)
        resumed = self.make(raw, resume=run.evidence.state["run_id"])
        self.assertEqual(await resumed.execute(), 2)
        retried = await self.passed(raw, resume=run.evidence.state["run_id"], retry=True)
        self.assertIn("previous_attempt", retried.evidence.state["executions"]["root/main/wait"])
        (self.root / "source.txt").write_text("one")
        raw["source_paths"] = ["source.txt"]
        run = await self.passed(raw)
        (self.root / "source.txt").write_text("two")
        with self.assertRaisesRegex(ValueError, "changed"):
            self.make(raw, resume=run.evidence.state["run_id"])

    async def test_void_function_and_null_are_distinct(self):
        from release_workbench.application.starters import edge

        raw = sequence(card("call", "call", {"function": "f"}))
        raw["functions"] = {"f": {"graph": "fn", "inputs": {}, "returns": "void"}}
        raw["graphs"]["fn"] = {
            "cards": [card("start", "start"), card("return", "return", {"returns": "void"})],
            "edges": [edge("start", "return")],
        }
        run = await self.passed(raw)
        self.assertEqual(
            run.evidence.state["executions"]["root/main/call"]["outcome"]["value"], {"type": "void"}
        )
        by_id(raw, "return", "fn")["config"] = {"returns": "json", "value": None}
        run = self.make(raw)
        self.assertEqual(await run.execute(), 1)

    async def test_poll_timeout_and_immediate_true(self):
        raw = starter("Poll", "poll")
        by_id(raw, "poll")["config"]["timeout"] = 0.05
        run = self.make(raw)
        self.assertEqual(await run.execute(), 1)
        self.assertIn("time limit", run.evidence.state["error"])
        (self.root / "ready.txt").write_text("ready")
        await self.passed(raw)

    async def test_invalid_progress_cannot_corrupt_evidence(self):
        code = "\n".join(
            [
                'print(\'::workbench::{"done":NaN,"total":1}\')',
                'print(\'::workbench::{"done":1,"total":Infinity}\')',
                'print(\'::workbench::{"done":-1,"total":1}\')',
                'print(\'::workbench::{"done":1,"total":2,"stage":"Working","kind":"spoofed"}\')',
                "return True",
            ]
        )
        run = await self.passed(sequence(card("progress", "python", {"code": code})))
        entry = run.evidence.state["executions"]["root/main/progress"]
        self.assertEqual(
            entry["progress"], {"done": 1, "total": 2, "stage": "Working", "measured": True}
        )
        self.assertTrue((run.evidence.directory / "report.html").is_file())
        self.assertFalse(any(event["kind"] == "spoofed" for event in run.evidence.state["events"]))

    async def test_declared_secret_environment_overrides_are_masked(self):
        raw = sequence(
            card(
                "override",
                "python",
                {
                    "code": "import os\nvalue=os.environ['WORKBENCH_DEMO_SECRET']\nprint(value)\nreturn value"
                },
            )
        )
        raw["environment"] = {"WORKBENCH_DEMO_SECRET": "demo-base-secret"}
        raw["secrets"] = ["WORKBENCH_DEMO_SECRET"]
        by_id(raw, "override")["settings"] = {
            "environment": {"WORKBENCH_DEMO_SECRET": "demo-card-secret"}
        }
        run = await self.passed(raw)
        for file in run.evidence.directory.iterdir():
            if file.is_file():
                text = file.read_text()
                self.assertNotIn("demo-base-secret", text)
                self.assertNotIn("demo-card-secret", text)
        self.assertIn("[REDACTED]", (run.evidence.directory / "summary.json").read_text())

    async def test_unicode_output_is_preserved_across_stream_chunks(self):
        import os

        from release_workbench.infrastructure.processes import ProcessAdapter

        logs = []
        text = "x" * 4095 + "€" + " done"
        result = await ProcessAdapter().run(
            [
                sys.executable,
                "-c",
                "import sys;sys.stdout.buffer.write(" + repr(text.encode()) + ")",
            ],
            self.root,
            dict(os.environ),
            None,
            logs.append,
            lambda: None,
        )
        self.assertEqual(result["stdout"], text)
        self.assertEqual("".join(logs), text)

    async def test_python_print_is_live_without_explicit_flush(self):
        raw = sequence(
            card(
                "live",
                "python",
                {
                    "code": "import time\nfrom pathlib import Path\nprint('live without flush')\nwhile not Path('release-print.flag').exists():\n    time.sleep(0.01)\nreturn True"
                },
            )
        )
        run = self.make(raw)
        task = asyncio.create_task(run.execute())
        try:

            async def wait_for_log():
                while "live without flush" not in run.evidence.state["executions"].get(
                    "root/main/live", {}
                ).get("tail", ""):
                    await asyncio.sleep(0.01)

            await asyncio.wait_for(wait_for_log(), 5)
            self.assertFalse(task.done())
        finally:
            (self.root / "release-print.flag").write_text("ready")
            await asyncio.wait_for(task, 5)

    async def test_python_respects_its_configured_working_directory(self):
        (self.root / "nested").mkdir()
        raw = sequence(
            card("cwd", "python", {"code": "from pathlib import Path\nreturn Path.cwd().name"})
        )
        by_id(raw, "cwd")["settings"] = {"cwd": "nested"}
        run = await self.passed(raw)
        self.assertEqual(
            run.evidence.state["executions"]["root/main/cwd"]["outcome"]["value"]["value"], "nested"
        )


class Scheduling(unittest.IsolatedAsyncioTestCase):
    async def test_budget_resource_contention_and_exclusive(self):
        coordinator = Coordinator(2)
        active = set()
        observed = []

        async def job(name, resources=None, exclusive=False):
            async with coordinator.slot(name, resources or set(), exclusive, lambda: None):
                active.add(name)
                observed.append(set(active))
                await asyncio.sleep(0.04)
                active.remove(name)

        await asyncio.gather(
            job("a", {"device"}),
            job("b", {"device"}),
            job("c"),
            job("exclusive", exclusive=True),
            job("last"),
        )
        self.assertLessEqual(max(map(len, observed)), 2)
        self.assertTrue(all(not {"a", "b"} <= group for group in observed))
        self.assertTrue(all(len(group) == 1 for group in observed if "exclusive" in group))

    async def test_pause_and_cancel_pending_slot(self):
        coordinator = Coordinator(1)
        coordinator.paused = True
        cancel = False

        def check():
            if cancel:
                raise asyncio.CancelledError()

        task = asyncio.create_task(coordinator.ready(check))
        await asyncio.sleep(0.03)
        self.assertFalse(task.done())
        cancel = True
        with self.assertRaises(asyncio.CancelledError):
            await task


class OptionalStdin(unittest.IsolatedAsyncioTestCase):
    async def test_successful_non_reader_may_close_stdin_early(self):
        from types import SimpleNamespace
        from unittest.mock import AsyncMock, Mock, patch

        from release_workbench.infrastructure.processes import ProcessAdapter

        for error in (BrokenPipeError("closed"), ConnectionResetError("Connection lost")):
            with self.subTest(error=type(error).__name__):
                stdout = asyncio.StreamReader()
                stdout.feed_data(b"done")
                stdout.feed_eof()
                stderr = asyncio.StreamReader()
                stderr.feed_eof()
                stream = SimpleNamespace(
                    write=Mock(), drain=AsyncMock(side_effect=error), close=Mock()
                )
                process = SimpleNamespace(
                    pid=99999999,
                    stdin=stream,
                    stdout=stdout,
                    stderr=stderr,
                    returncode=0,
                    wait=AsyncMock(return_value=0),
                )
                adapter = ProcessAdapter()
                adapter._cleanup = AsyncMock()
                with patch("asyncio.create_subprocess_exec", AsyncMock(return_value=process)):
                    result = await adapter.run(
                        ["example"], Path.cwd(), {}, {"inputs": {}}, lambda _: None, lambda: None
                    )
                self.assertEqual(result["exit_code"], 0)
                self.assertEqual(result["stdout"], "done")
                stream.close.assert_called_once()
