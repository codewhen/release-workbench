import json
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from release_workbench.application.starters import starter
from release_workbench.infrastructure.documents import render_document
from release_workbench.interfaces.server import create_server


class Interfaces(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "test.yaml").write_text(render_document(starter("Test")))
        self.server, self.app = create_server(self.root, self.root / "storage")
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def request(self, path, body=None, headers=None):
        req = Request(
            self.base + path,
            data=json.dumps(body).encode() if body is not None else None,
            headers=headers or {},
        )
        with urlopen(req) as response:
            return response.status, response.read()

    def test_mutation_token_and_origin_protection(self):
        for headers in (
            {},
            {"X-Workbench-Token": self.app.token, "Origin": "https://other.example"},
        ):
            with self.assertRaises(HTTPError) as caught:
                self.request("/api/create", {"filename": "x.yaml", "name": "x"}, headers)
            self.assertEqual(caught.exception.code, 403)
            caught.exception.close()
        status, _ = self.request(
            "/api/create",
            {"project": str(self.root), "filename": "new.yaml", "name": "New"},
            {"X-Workbench-Token": self.app.token},
        )
        self.assertEqual(status, 200)

    def test_report_escape_unknown_and_host_rejected(self):
        for path in ("/reports/%2e%2e/%2e%2e/test.yaml", "/api/missing", "/not-a-page"):
            with self.assertRaises(HTTPError) as caught:
                self.request(path)
            self.assertEqual(caught.exception.code, 404)
            caught.exception.close()
        with self.assertRaises(HTTPError) as caught:
            self.request("/api/library", headers={"Host": "outside.example"})
        self.assertEqual(caught.exception.code, 403)
        caught.exception.close()

    def test_old_workflow_stays_unchanged(self):
        text = "version: 2\nname: Old\nsteps: []\n"
        old = self.root / "old.yaml"
        old.write_text(text)
        with self.assertRaisesRegex(ValueError, "Unsupported"):
            self.app.library.register(old)
        self.assertEqual(old.read_text(), text)

    def test_save_never_starts_commands_and_revision_is_checked(self):
        entry = self.app.library.listing()["entries"][0]
        key = entry["id"]
        record = json.loads(self.request("/api/config?workflow=" + key)[1])
        value = record["workflow"]
        value["name"] = "Changed"
        self.app.mutation("save", key, {"workflow": value, "revision": record["revision"]})
        self.assertFalse(self.app.runs)
        with self.assertRaisesRegex(ValueError, "outside"):
            self.app.mutation("save", key, {"workflow": value, "revision": record["revision"]})
