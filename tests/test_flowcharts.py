import asyncio
import json

from release_workbench.application.compiler import CompilationError
from release_workbench.application.starters import card, edge, ref, starter
from release_workbench.infrastructure.documents import compile_document, render_document
from tests.support import RunCase, by_id, sequence


class Flowcharts(RunCase):
    async def test_all_unattended_starters(self):
        for name in ("blank", "python", "while", "parallel", "recovery"):
            with self.subTest(name=name):
                await self.passed(starter(name, name))

    async def test_while_changes_condition_and_resets_globals(self):
        raw = starter("While", "while")
        for _ in range(2):
            run = await self.passed(raw)
            self.assertEqual(run.globals["count"], 3)
            self.assertEqual(
                sum(
                    e["graph"] == "condition" and e["card"] == "return"
                    for e in run.evidence.state["executions"].values()
                ),
                4,
            )

    async def test_zero_iterations(self):
        raw = starter("While", "while")
        raw["globals"]["count"]["initial"] = 3
        run = await self.passed(raw)
        self.assertEqual(
            run.evidence.state["executions"]["root/main/increment"]["status"], "skipped"
        )

    async def test_count_loop_and_break_continue(self):
        for kind, expected in (("break", 1), ("continue", 5)):
            raw = sequence(
                card("loop", "loop", {"mode": "count", "count": 5}),
                card("control", kind, {}, ("loop", "body")),
            )
            raw["graphs"]["main"]["edges"] = [
                edge("start", "loop"),
                edge("loop", "control", "body"),
                edge("loop", "finish", "done"),
            ]
            run = await self.passed(raw)
            self.assertEqual(
                run.evidence.state["executions"]["root/main/loop"]["outcome"]["value"]["value"][
                    "iterations"
                ],
                expected,
            )

    async def test_nested_loops(self):
        raw = starter("Nested", "while")
        g = raw["graphs"]["main"]
        by_id(raw, "repeat")["config"] = {"mode": "count", "count": 2}
        by_id(raw, "increment")["owner"] = {"card": "inner", "region": "body"}
        g["cards"].append(card("inner", "loop", {"count": 3}, ("repeat", "body")))
        g["edges"] = [
            edge("start", "repeat"),
            edge("repeat", "inner", "body"),
            edge("inner", "increment", "body"),
            edge("increment", "inner", target_port="next_iteration"),
            edge("inner", "repeat", "done", "next_iteration"),
            edge("repeat", "finish", "done"),
        ]
        run = await self.passed(raw)
        self.assertEqual(run.globals["count"], 6)

    async def test_loop_exhaustion(self):
        raw = starter("Limited", "while")
        by_id(raw, "repeat")["config"]["limit"] = 2
        run = self.make(raw)
        self.assertEqual(await run.execute(), 1)
        self.assertIn("iteration limit", run.evidence.state["error"])

    async def test_unlimited_loop_cancellation(self):
        raw = starter("Forever", "while")
        by_id(raw, "compare", "condition")["config"]["right"] = 10**9
        by_id(raw, "repeat")["config"].update(limit=None, timeout=None)
        run = self.make(raw)
        task = asyncio.create_task(run.execute())
        await asyncio.sleep(0.03)
        run.stop()
        self.assertEqual(await asyncio.wait_for(task, 2), 130)

    async def test_value_wire_supplies_config_without_starting_card(self):
        raw = sequence(
            card("a", "python", {"code": "return 4", "returns": "number"}),
            card("calc", "calculate", {"operator": "multiply", "right": 2}),
        )
        raw["graphs"]["main"]["edges"].append(
            {
                "id": "value",
                "kind": "value",
                "source": "a",
                "target": "calc",
                "source_port": "value",
                "target_port": "config:left",
            }
        )
        run = await self.passed(raw)
        self.assertEqual(
            run.evidence.state["executions"]["root/main/calc"]["outcome"]["value"]["value"], 8
        )

    async def test_functions_isolate_inputs_and_return_false(self):
        raw = sequence(
            card("first", "call", {"function": "f"}), card("second", "call", {"function": "f"})
        )
        raw["functions"] = {
            "f": {"graph": "fn", "inputs": {"flag": {"type": "boolean"}}, "returns": "boolean"}
        }
        raw["graphs"]["fn"] = {
            "cards": [
                card("start", "start"),
                card("return", "return", {"value": {"$ref": "input:flag"}}),
            ],
            "edges": [edge("start", "return")],
        }
        by_id(raw, "first")["inputs"] = {"flag": True}
        by_id(raw, "second")["inputs"] = {"flag": False}
        run = await self.passed(raw)
        self.assertIs(
            run.evidence.state["executions"]["root/main/second"]["outcome"]["value"]["value"], False
        )

    async def test_dynamic_wrong_boolean_fails(self):
        raw = starter("Invalid", "manual")
        by_id(raw, "ask", "approval").update(kind="python", config={"code": "return 1"})
        run = self.make(raw)
        self.assertEqual(await run.execute(), 1)
        self.assertIn("boolean", run.evidence.state["error"])

    async def test_parallel_global_conflict_direct_and_function(self):
        for through_function in (False, True):
            raw = starter("Conflict", "parallel")
            raw["globals"] = {"x": {"type": "number", "initial": 0}}
            by_id(raw, "second").update(kind="variable", config={"name": "x", "operation": "get"})
            if through_function:
                raw["functions"] = {
                    "setter": {"graph": "setter", "inputs": {}, "returns": "number"}
                }
                raw["graphs"]["setter"] = {
                    "cards": [
                        card("start", "start"),
                        card("set", "variable", {"name": "x", "operation": "set", "value": 1}),
                        card("return", "return", {"value": ref("set")}),
                    ],
                    "edges": [edge("start", "set"), edge("set", "return")],
                }
                by_id(raw, "first").update(kind="call", config={"function": "setter"})
            else:
                by_id(raw, "first").update(
                    kind="variable", config={"name": "x", "operation": "set", "value": 1}
                )
            with self.assertRaisesRegex(CompilationError, "parallel global conflict"):
                compile_document(raw)

    async def test_external_workspace_isolated_globals_and_output(self):
        child = sequence(card("set", "variable", {"name": "x", "operation": "set", "value": 8}))
        child["globals"] = {"x": {"type": "number", "initial": 0}}
        by_id(child, "finish")["config"] = {"returns": "number", "value": ref("set")}
        folder = self.root / "child"
        folder.mkdir()
        (folder / "workflow.yaml").write_text(render_document(child))
        parent = sequence(card("child", "workspace", {"path": "child/workflow.yaml", "inputs": {}}))
        parent["globals"] = {"x": {"type": "number", "initial": 1}}
        run = await self.passed(parent)
        self.assertEqual(run.globals["x"], 1)
        self.assertEqual(
            run.evidence.state["executions"]["root/main/child"]["outcome"]["value"]["value"], 8
        )

    async def test_manual_noninteractive_blocked_and_no_finally(self):
        raw = starter("Manual", "recovery")
        by_id(raw, "failure").update(kind="manual", config={"mode": "decision"})
        run = self.make(raw)
        self.assertEqual(await run.execute(), 2)
        self.assertFalse(
            any(e["card"] == "cleanup" for e in run.evidence.state["executions"].values())
        )

    async def test_repeated_manual_boolean_prompts(self):
        raw = starter("Manual", "manual")
        by_id(raw, "decision").update(
            kind="loop", config={"mode": "while", "function": "approved", "limit": 5}
        )
        by_id(raw, "work")["owner"] = {"card": "decision", "region": "body"}
        raw["graphs"]["main"]["edges"] = [
            edge("start", "decision"),
            edge("decision", "work", "body"),
            edge("work", "decision", target_port="next_iteration"),
            edge("decision", "finish", "done"),
        ]
        run = self.make(raw, interactive=True)
        task = asyncio.create_task(run.execute())
        paths = []
        for answer in (True, True, False):
            for _ in range(200):
                fresh = [p for p in run.evidence.state["manual"] if p not in paths]
                if fresh:
                    break
                await asyncio.sleep(0.01)
            self.assertTrue(fresh)
            path = fresh[0]
            paths.append(path)
            run.record(path, "Verified", answer)
            await asyncio.sleep(0.05)
        self.assertEqual(await asyncio.wait_for(task, 3), 0)
        self.assertEqual(len(set(paths)), 3)

    async def test_catch_must_acknowledge_original_failure(self):
        raw = starter("Unhandled", "recovery")
        by_id(raw, "catch-end")["config"]["handled"] = False
        run = self.make(raw)
        self.assertEqual(await run.execute(), 1)
        self.assertTrue(
            any(e["card"] == "cleanup" for e in run.evidence.state["executions"].values())
        )

    async def test_finally_after_break_and_stop_does_not_launch_cleanup(self):
        raw = starter("Stop", "recovery")
        by_id(raw, "failure").update(kind="wait", config={"seconds": 30})
        run = self.make(raw)
        task = asyncio.create_task(run.execute())
        await asyncio.sleep(0.05)
        run.stop("root/main/recover/body/body/failure")
        self.assertEqual(await asyncio.wait_for(task, 2), 130)
        self.assertFalse(
            any(e["card"] == "cleanup" for e in run.evidence.state["executions"].values())
        )

    async def test_retry_failure_attempts_retained(self):
        raw = sequence(
            card(
                "flaky",
                "python",
                {
                    "code": "from pathlib import Path\np=Path('attempt')\nif not p.exists():\n    p.write_text('seen')\n    raise ValueError('try again')\nreturn True",
                    "returns": "boolean",
                },
            )
        )
        by_id(raw, "flaky")["settings"] = {"retry": {"attempts": 2, "delay": 0.01, "backoff": 1}}
        run = await self.passed(raw)
        attempts = run.evidence.state["executions"]["root/main/flaky"]["attempts"]
        self.assertEqual([x["status"] for x in attempts], ["failed", "passed"])

    async def test_resume_does_not_repeat_successful_side_effect(self):
        raw = sequence(card("write", "write_file", {"path": "once.txt", "value": "once"}))
        run = await self.passed(raw)
        await self.passed(raw, resume=run.evidence.state["run_id"])
        self.assertEqual((self.root / "once.txt").read_text(), "once")
        raw["name"] = "Changed"
        with self.assertRaisesRegex(ValueError, "changed"):
            self.make(raw, resume=run.evidence.state["run_id"])

    async def test_layout_does_not_change_fingerprint(self):
        raw = starter("Layout")
        one = self.make(raw)
        raw["layout"] = {"main": {"positions": {"start": {"x": 500, "y": 100}}, "areas": []}}
        two = self.make(raw)
        self.assertEqual(one.fingerprint, two.fingerprint)

    async def test_finally_runs_after_loop_break(self):
        raw = starter("Break cleanup", "recovery")
        g = raw["graphs"]["main"]
        g["cards"].append(card("loop", "loop", {"mode": "count", "count": 5}))
        by_id(raw, "recover")["owner"] = {"card": "loop", "region": "body"}
        by_id(raw, "failure").update(kind="break", config={})
        g["cards"] = [c for c in g["cards"] if c["id"] != "body-end"]
        g["edges"] = [
            edge("start", "loop"),
            edge("loop", "recover", "body"),
            edge("recover", "failure", "body"),
            edge("recover", "catch-end", "catch"),
            edge("recover", "cleanup", "finally"),
            edge("cleanup", "finally-end"),
            edge("recover", "loop", "done", "next_iteration"),
            edge("loop", "finish", "done"),
        ]
        run = await self.passed(raw)
        paths = list(run.evidence.state["executions"])
        self.assertTrue(any("/cleanup" in p for p in paths))
        self.assertEqual(
            run.evidence.state["executions"]["root/main/loop"]["outcome"]["value"]["value"][
                "iterations"
            ],
            1,
        )

    async def test_external_workspaces_share_one_budget_with_unique_job_ids(self):
        child = sequence(
            card(
                "operation",
                "python",
                {
                    "code": "import time,json\nfrom pathlib import Path\nstart=time.time()\ntime.sleep(.12)\nPath(inputs['label']+'.json').write_text(json.dumps([start,time.time()]))\nreturn True",
                    "returns": "boolean",
                },
            )
        )
        child["inputs"] = {"label": {"type": "string"}}
        by_id(child, "operation")["inputs"] = {"label": {"$ref": "input:label"}}
        by_id(child, "finish")["config"] = {"returns": "boolean", "value": ref("operation")}
        folder = self.root / "children"
        folder.mkdir()
        (folder / "workflow.yaml").write_text(render_document(child))
        parent = starter("Shared budget", "parallel")
        parent["concurrency"] = 2
        g = parent["graphs"]["main"]
        by_id(parent, "parallel")["config"]["branches"] = ["first", "second", "third", "fourth"]
        for name in ("third", "fourth"):
            g["cards"] += [
                card(name, "workspace", {}, ("parallel", name)),
                card(name + "-return", "return", {"value": ref(name)}, ("parallel", name)),
            ]
            g["edges"] += [edge("parallel", name, name), edge(name, name + "-return")]
        for name in ("first", "second", "third", "fourth"):
            by_id(parent, name).update(
                kind="workspace",
                config={"path": "children/workflow.yaml", "inputs": {"label": name}},
            )
        await self.passed(parent)
        events = []
        for file in folder.glob("*.json"):
            start, end = json.loads(file.read_text())
            events += [(start, 1), (end, -1)]
        active = 0
        peak = 0
        for _, delta in sorted(events):
            active += delta
            peak = max(peak, active)
        self.assertEqual(len(events), 8)
        self.assertLessEqual(peak, 2)

    async def test_parent_fingerprint_includes_child_declared_source(self):
        child = starter("Child")
        child["source_paths"] = ["source.txt"]
        folder = self.root / "child"
        folder.mkdir()
        (folder / "source.txt").write_text("before")
        (folder / "workflow.yaml").write_text(render_document(child))
        parent = sequence(card("child", "workspace", {"path": "child/workflow.yaml", "inputs": {}}))
        first = self.make(parent).fingerprint
        (folder / "source.txt").write_text("after")
        self.assertNotEqual(first, self.make(parent).fingerprint)

    async def test_manual_approval_returns_void(self):
        raw = sequence(
            card("approve", "manual", {"mode": "approval", "instructions": "Check the result."})
        )
        run = self.make(raw, interactive=True)
        task = asyncio.create_task(run.execute())
        for _ in range(100):
            if run.evidence.state["manual"]:
                break
            await asyncio.sleep(0.01)
        path = next(iter(run.evidence.state["manual"]))
        run.record(path, "Checked")
        self.assertEqual(await asyncio.wait_for(task, 2), 0)
        self.assertEqual(
            run.evidence.state["executions"][path]["outcome"]["value"], {"type": "void"}
        )

    async def test_finally_after_normal_completion_skips_catch(self):
        raw = starter("Normal", "recovery")
        by_id(raw, "failure")["config"] = {"code": "return True"}
        run = await self.passed(raw)
        self.assertEqual(
            run.evidence.state["executions"]["root/main/catch-end"]["status"], "skipped"
        )
        self.assertTrue(
            any(
                e["card"] == "cleanup" and e["status"] == "passed"
                for e in run.evidence.state["executions"].values()
            )
        )

    async def test_independent_parallel_branch_completes_after_failure(self):
        raw = starter("Independent", "parallel")
        by_id(raw, "first")["config"] = {"code": "raise ValueError('fail')"}
        run = self.make(raw)
        self.assertEqual(await run.execute(), 1)
        self.assertTrue(
            any(
                e["card"] == "second" and e["status"] == "passed"
                for e in run.evidence.state["executions"].values()
            )
        )
        self.assertFalse(
            any(
                e["card"] == "join" and e["status"] == "passed"
                for e in run.evidence.state["executions"].values()
            )
        )
