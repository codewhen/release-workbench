"""One invocation's local inputs, values and control-region context."""

from __future__ import annotations

import asyncio
import copy
import json
from typing import TYPE_CHECKING, Any

from release_workbench.domain.models import Card, Graph, Outcome
from release_workbench.domain.values import VOID, ContractError, TypedValue, ValueType

from .executors import EXECUTORS, EvidenceRequired, ExecutionFailure

if TYPE_CHECKING:
    from .runtime import Run


class Frame:
    def __init__(
        self,
        run: Run,
        graph: Graph,
        inputs: dict[str, Any],
        path: str,
        results: dict[str, TypedValue] | None = None,
        loop: dict[str, Any] | None = None,
        error: dict[str, Any] | None = None,
    ):
        self.run, self.graph, self.inputs, self.path = run, graph, inputs, path
        self.results = dict(results or {})
        self.loop, self.error = loop or {}, error or {}
        self._log_buffer = ""

    def for_node(self, path: str) -> Frame:
        return Frame(self.run, self.graph, self.inputs, path, self.results, self.loop, self.error)

    def check(self) -> None:
        self.run.check(self.path)

    def reference(self, reference: str, path: str = "") -> Any:
        if reference.startswith("card:"):
            value = self.results[reference[5:]]
            if value.type == ValueType.VOID:
                raise ContractError("Void has no value to bind.")
            result = value.value
        elif reference.startswith("input:"):
            result = self.inputs[reference[6:]]
        elif reference.startswith("env:"):
            result = self.run.environment[reference[4:]]
        elif reference == "loop":
            result = self.loop
        elif reference == "error":
            result = self.error
        else:
            raise ContractError("Unknown value reference: " + reference)
        for part in path.split(".") if path else []:
            result = result[int(part)] if isinstance(result, list) else result[part]
        return copy.deepcopy(result)

    def resolve(self, value: Any) -> Any:
        if isinstance(value, dict):
            if "$ref" in value:
                return self.reference(value["$ref"], value.get("path", ""))
            return {key: self.resolve(item) for key, item in value.items()}
        if isinstance(value, list):
            return [self.resolve(item) for item in value]
        return value

    async def invoke(self, name: str, inputs: dict[str, Any], label: str) -> Outcome:
        function = self.run.workflow.functions[name]
        arguments = self.run.parameters(function.get("inputs", {}), inputs)
        graph = self.run.workflow.graphs[function["graph"]]
        frame = Frame(self.run, graph, arguments, self.path + "/" + label + "/" + name)
        result = await self.run.walk(frame)
        if result.signal != "return":
            raise ExecutionFailure("Function must reach Return: " + name)
        if result.value.type == ValueType.VOID and function["returns"] != "void":
            raise ContractError("Function returned Void; expected " + function["returns"])
        if result.value.type != ValueType.VOID and function["returns"] == "void":
            raise ContractError("Function must explicitly return Void.")
        value = TypedValue.checked(result.value.value, function["returns"])
        return Outcome(value)

    async def region(self, card: Card, name: str, label: str) -> Outcome:
        edges = self.graph.outgoing(card.id, name)
        if not edges:
            return Outcome()
        loop = (
            {
                "index": int(label.split("-")[-1]) - 1,
                "iteration": int(label.split("-")[-1]),
            }
            if card.kind == "loop"
            else self.loop
        )
        frame = Frame(
            self.run,
            self.graph,
            self.inputs,
            self.path + "/" + label + "/" + name,
            self.results,
            loop,
            self.error,
        )
        return await self.run.walk(frame, edges[0].target)

    async def sleep(self, seconds: float) -> None:
        if type(seconds) not in (float, int) or seconds < 0:
            raise ContractError("Delay must be nonnegative.")
        deadline = self.run.clock.monotonic() + seconds
        while self.run.clock.monotonic() < deadline:
            self.check()
            await self.run.clock.sleep(min(0.03, max(0, deadline - self.run.clock.monotonic())))
        self.check()

    def global_get(self, name: str) -> Any:
        return copy.deepcopy(self.run.globals[name])

    def global_set(self, name: str, value: Any) -> Any:
        TypedValue.checked(value, self.run.workflow.globals[name]["type"])
        self.run.globals[name] = copy.deepcopy(value)
        self.run.evidence.state["executions"][self.path]["global_changes"][name] = copy.deepcopy(
            value
        )
        self.run.evidence.emit("variable_changed", self.path, name=name, value=value)
        return copy.deepcopy(value)

    def log(self, text: str) -> None:
        self.run.evidence.log(self.path, text)
        self._log_buffer += text
        while "\n" in self._log_buffer:
            line, self._log_buffer = self._log_buffer.split("\n", 1)
            if line.startswith("::workbench::"):
                try:
                    progress = json.loads(line[len("::workbench::") :])
                    if (
                        type(progress["done"]) in (int, float)
                        and type(progress["total"]) in (int, float)
                        and progress["total"] > 0
                    ):
                        self.run.evidence.state["executions"][self.path]["progress"] = {
                            "done": progress["done"],
                            "total": progress["total"],
                            "stage": str(progress.get("stage", "")),
                            "measured": True,
                        }
                        self.run.evidence.emit("progress", self.path, **progress)
                except (KeyError, ValueError, TypeError):
                    pass

    async def execute(self, card: Card) -> Outcome:
        # Structural cards must never occupy a slot while waiting on their children.
        structural = {"if", "loop", "parallel", "try", "call", "workspace", "poll"}
        if card.kind in structural:
            return await EXECUTORS[card.kind].execute(card, self)
        resources = set(card.settings.get("resources", []))
        if card.settings.get("interactive"):
            resources.add("desktop")
        entry = self.run.evidence.state["executions"][self.path]
        entry["status"] = "queued"
        async with self.run.coordinator.slot(
            self.run.evidence.state["run_id"] + "/" + self.path,
            resources,
            card.settings.get("exclusive", False),
            self.check,
        ):
            entry["status"] = "running"
            return await EXECUTORS[card.kind].execute(card, self)

    async def operation(self, card: Card) -> Any:
        environment = {**self.run.environment, **card.settings.get("environment", {})}
        return await self.run.services.operation(
            card, self.run.root, self.inputs, environment, self.log, self.check
        )

    async def manual(self, card: Card) -> Outcome:
        if not self.run.interactive:
            raise EvidenceRequired("Manual evidence required: " + card.name)
        mode = card.config.get("mode", "decision")
        self.run.evidence.state["manual"][self.path] = {
            "card": card.id,
            "name": card.name,
            "mode": mode,
            "instructions": card.config.get("instructions", ""),
        }
        self.run.evidence.state["executions"][self.path]["status"] = "manual"
        self.run.evidence.emit("manual_requested", self.path, mode=mode)
        self.run.evidence.save()
        try:
            while self.path not in self.run.manual_answers:
                self.check()
                await self.run.clock.sleep(0.03)
            answer = self.run.manual_answers.pop(self.path)
            self.run.evidence.emit("manual_recorded", self.path, **answer)
            return Outcome(
                TypedValue.checked(answer["decision"], "boolean") if mode == "decision" else VOID
            )
        finally:
            self.run.evidence.state["manual"].pop(self.path, None)

    async def workspace(self, card: Card) -> Outcome:
        file = (self.run.root / card.config["path"]).resolve()
        if file in self.run.stack or len(self.run.stack) >= 16:
            raise ExecutionFailure("Recursive workspace calls are not supported.")
        workflow = self.run.services.load_workflow(file)
        from .runtime import Run

        child = Run(
            workflow,
            file.parent,
            self.run.evidence.directory / "children",
            self.run.services,
            card.config.get("inputs", self.inputs),
            self.run.interactive,
            coordinator=self.run.coordinator,
            stack=(*self.run.stack, file),
        )
        child.evidence.masker.values = sorted(
            set(child.evidence.masker.values + self.run.evidence.masker.values),
            key=len,
            reverse=True,
        )
        self.run.children.append((self.path, child))
        task = asyncio.create_task(child.execute())
        try:
            while not task.done():
                self.check()
                self.run.evidence.state["executions"][self.path]["child_run"] = str(
                    child.evidence.directory
                )
                # Forward child interventions into the parent's prompt surface.
                for path, request in child.evidence.state["manual"].items():
                    self.run.evidence.state["manual"][self.path + "/child/" + path] = {
                        **request,
                        "child": True,
                    }
                    key = self.path + "/child/" + path
                    if key in self.run.manual_answers:
                        answer = self.run.manual_answers.pop(key)
                        child.record(path, answer["note"], answer.get("decision"))
                        self.run.evidence.state["manual"].pop(key, None)
                await self.run.clock.sleep(0.03)
            code = await task
            if code == 2:
                raise EvidenceRequired("Child workflow requires evidence.")
            if code:
                raise ExecutionFailure("Child workflow did not pass.")
            return Outcome(TypedValue.from_dict(child.evidence.state["result"]))
        finally:
            if not task.done():
                child.stop()
                await asyncio.gather(task, return_exceptions=True)
            for key in list(self.run.evidence.state["manual"]):
                if key.startswith(self.path + "/child/"):
                    self.run.evidence.state["manual"].pop(key, None)
