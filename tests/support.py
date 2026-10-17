import tempfile
import unittest
from pathlib import Path

from release_workbench.application.runtime import Run
from release_workbench.application.starters import card, edge, starter
from release_workbench.infrastructure.documents import compile_document
from release_workbench.infrastructure.services import LocalServices


class RunCase(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="workbench-test-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def make(self, raw, **kwargs):
        return Run(
            compile_document(raw), self.root, self.root / "evidence", LocalServices(), **kwargs
        )

    async def passed(self, raw, **kwargs):
        run = self.make(raw, **kwargs)
        self.assertEqual(await run.execute(), 0, run.evidence.state.get("error"))
        return run


def sequence(*operations):
    value = starter("Test")
    cards = [card("start", "start"), *operations, card("finish", "finish")]
    value["graphs"]["main"] = {
        "cards": cards,
        "edges": [edge(a["id"], b["id"]) for a, b in zip(cards, cards[1:], strict=False)],
    }
    return value


def by_id(raw, name, graph="main"):
    return next(c for c in raw["graphs"][graph]["cards"] if c["id"] == name)
