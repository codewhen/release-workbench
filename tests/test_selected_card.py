"""Run from here follows successors, reusing only compatible upstream data."""

import asyncio
import tempfile
import unittest
from pathlib import Path

from release_workbench.application.runtime import Run
from release_workbench.application.starters import card, edge, starter
from release_workbench.infrastructure.documents import compile_document
from release_workbench.infrastructure.run_checkpoints import latest_checkpoint
from release_workbench.infrastructure.services import LocalServices


class RunFromHere(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()

    def run_from(self, raw, card_id, graph="main", inputs=None, checkpoint=None):
        return Run(
            compile_document(raw),
            self.root,
            self.root / "runs",
            LocalServices(),
            inputs=inputs,
            interactive=True,
            selection=(graph, card_id),
            checkpoint=checkpoint,
        )

    async def test_follows_successors_to_finish_and_skips_predecessors(self):
        raw = starter("Run from sample")
        raw["graphs"]["main"] = {
            "cards": [
                card("start", "start"),
                card("before", "python", {"code": 'raise Exception("must not run")'}),
                card(
                    "selected",
                    "python",
                    {"code": 'print("from-here log")\nreturn False', "returns": "boolean"},
                ),
                card("after", "python", {"code": "return 42", "returns": "number"}),
                card(
                    "finish", "finish", {"returns": "boolean", "value": {"$ref": "card:selected"}}
                ),
            ],
            "edges": [
                edge("start", "before"),
                edge("before", "selected"),
                edge("selected", "after"),
                edge("after", "finish"),
            ],
        }
        run = self.run_from(raw, "selected")
        self.assertEqual(await run.execute(), 0)
        self.assertEqual(
            list(run.evidence.state["executions"]),
            ["root/main/selected", "root/main/after", "root/main/finish"],
        )
        self.assertEqual(run.evidence.state["result"], {"type": "boolean", "value": False})
        self.assertEqual(run.evidence.state["selection"]["mode"], "from_here")

    async def test_function_follows_return_and_checks_its_type(self):
        raw = starter("Function", "manual")
        raw["functions"]["approved"]["inputs"] = {"answer": {"type": "boolean"}}
        raw["graphs"]["approval"]["cards"][1] = {
            **card("ask", "python", {"code": 'return inputs["answer"]', "returns": "boolean"}),
            "inputs": {"answer": {"$ref": "input:answer"}},
        }
        run = self.run_from(raw, "ask", "approval", {"answer": True})
        self.assertEqual(await run.execute(), 0)
        self.assertEqual(
            list(run.evidence.state["executions"]), ["root/approval/ask", "root/approval/return"]
        )
        self.assertTrue(run.evidence.state["result"]["value"])

    async def test_join_reuses_passed_parallel_results_without_rerunning_branches(self):
        raw = starter("Race collection", "parallel")
        for item in raw["graphs"]["main"]["cards"]:
            if item["id"] in {"first", "second"}:
                item["config"]["code"] = (
                    'from pathlib import Path\np=Path("effects.txt")\np.write_text((p.read_text() if p.exists() else "") + "ran\\n")\nreturn 42'
                )
                item["config"]["returns"] = "number"
        full = Run(compile_document(raw), self.root, self.root / "runs", LocalServices())
        self.assertEqual(await full.execute(), 0)
        before = (self.root / "effects.txt").read_text()
        run = self.run_from(raw, "join", checkpoint=full.evidence.snapshot())
        self.assertEqual(await run.execute(), 0)
        self.assertEqual(
            list(run.evidence.state["executions"]), ["root/main/join", "root/main/finish"]
        )
        self.assertEqual((self.root / "effects.txt").read_text(), before)
        self.assertEqual(
            run.evidence.state["executions"]["root/main/join"]["outcome"]["value"]["value"][
                "first"
            ]["value"],
            42,
        )
        self.assertEqual(
            run.evidence.state["input_context"]["source_run"], full.evidence.state["run_id"]
        )
        # The same context survives a restart, and chained partial runs retain inputs.
        saved = latest_checkpoint(self.root / "runs", run.base_fingerprint)
        self.assertEqual(saved["run_id"], run.evidence.state["run_id"])
        again = self.run_from(raw, "join", checkpoint=saved)
        self.assertEqual(await again.execute(), 0)
        self.assertEqual((self.root / "effects.txt").read_text(), before)

    async def test_missing_failed_or_stale_upstream_outputs_are_not_reused(self):
        raw = starter("Join", "parallel")
        full = Run(compile_document(raw), self.root, self.root / "runs", LocalServices())
        self.assertEqual(await full.execute(), 0)
        for mutation in ("missing", "failed", "redacted", "stale"):
            source = full.evidence.snapshot()
            if mutation == "missing":
                source["executions"] = {}
            elif mutation == "failed":
                source["executions"]["root/main/parallel"]["status"] = "failed"
            elif mutation == "redacted":
                source["executions"]["root/main/parallel"]["redacted_result"] = True
            else:
                source["base_fingerprint"] = "changed"
            run = self.run_from(raw, "join", checkpoint=source)
            self.assertEqual(await run.execute(), 1)
            self.assertIn('No result is available from "Parallel"', run.evidence.state["error"])
            self.assertEqual(list(run.evidence.state["executions"]), ["root/main/join"])

    async def test_reuses_upstream_variable_changes_but_reruns_successors(self):
        raw = starter("Variables")
        raw["globals"] = {"count": {"type": "number", "initial": 0}}
        raw["graphs"]["main"] = {
            "cards": [
                card("start", "start"),
                card("set", "variable", {"operation": "set", "name": "count", "value": 8}),
                card(
                    "increment",
                    "variable",
                    {"operation": "update", "name": "count", "operator": "add", "value": 1},
                ),
                card("finish", "finish"),
            ],
            "edges": [edge("start", "set"), edge("set", "increment"), edge("increment", "finish")],
        }
        full = Run(compile_document(raw), self.root, self.root / "runs", LocalServices())
        self.assertEqual(await full.execute(), 0)
        run = self.run_from(raw, "increment", checkpoint=full.evidence.snapshot())
        self.assertEqual(await run.execute(), 0)
        self.assertEqual(run.globals["count"], 9)  # not 10 from the old final state
        self.assertNotIn("root/main/set", run.evidence.state["executions"])

    async def test_stop_cancels_remainder_and_owned_cards_require_container(self):
        raw = starter("Manual", "manual")
        run = self.run_from(raw, "ask", "approval")
        task = asyncio.create_task(run.execute())
        for _ in range(100):
            if run.evidence.state["manual"]:
                break
            await asyncio.sleep(0.01)
        run.stop()
        self.assertEqual(await asyncio.wait_for(task, 5), 130)
        self.assertNotIn("root/approval/return", run.evidence.state["executions"])
        with self.assertRaisesRegex(ValueError, "controlled body"):
            self.run_from(starter("Loop", "while"), "increment")
