"""Typed graph interpreter with explicit frames, ownership and hierarchical evidence."""

from __future__ import annotations

import asyncio
import copy
import datetime
import threading
import time
import uuid
from dataclasses import replace
from pathlib import Path
from typing import Any

from release_workbench.domain.cards import get_spec
from release_workbench.domain.models import (
    Card,
    CardResult,
    Outcome,
    Workflow,
)
from release_workbench.domain.values import ContractError, TypedValue

from .coordinator import Coordinator
from .executors import EvidenceRequired, ExecutionFailure
from .frame import Frame
from .ports import Services


class Run:
    def __init__(
        self,
        workflow: Workflow,
        root: Path,
        storage: Path,
        services: Services,
        inputs: dict[str, Any] | None = None,
        interactive: bool = False,
        resume: str | None = None,
        retry: bool = False,
        coordinator: Coordinator | None = None,
        stack: tuple[Path, ...] = (),
    ):
        self.workflow, self.root, self.storage = (
            workflow,
            root.resolve(),
            storage.resolve(),
        )
        self.inputs = self.parameters(workflow.inputs, inputs or {})
        self.globals = {
            name: copy.deepcopy(value["initial"]) for name, value in workflow.globals.items()
        }
        self.interactive, self.retry, self.stack = interactive, retry, stack
        self.coordinator = coordinator or Coordinator(workflow.concurrency)
        self.services, self.clock = services, services.clock
        self.cancelled = threading.Event()
        self.cancelled_paths: set[str] = set()
        self.manual_answers: dict[str, dict[str, Any]] = {}
        self.children: list[tuple[str, Run]] = []
        self.deadlines: dict[str, float] = {}
        environment = services.environment(workflow)
        self.environment = environment
        self.fingerprint = services.fingerprint(workflow, self.root, self.inputs)
        run_id = (
            resume
            or datetime.datetime.now(datetime.UTC).strftime("%Y%m%dT%H%M%S")
            + "-"
            + uuid.uuid4().hex[:8]
        )
        if Path(run_id).name != run_id or run_id in (".", ".."):
            raise ValueError("Invalid run ID.")
        directory = self.storage / run_id
        if resume:
            state = services.load_state(directory)
            if state["fingerprint"] != self.fingerprint:
                raise ValueError("Workflow, source or inputs changed. Start a new run.")
        else:
            state = {
                "run_id": run_id,
                "name": workflow.name,
                "fingerprint": self.fingerprint,
                "status": "pending",
                "executions": {},
                "events": [],
                "manual": {},
            }
        state["manual"] = {}
        self.evidence = services.evidence(directory, state, workflow, environment)
        self.thread: threading.Thread | None = None

    @staticmethod
    def parameters(definitions: dict[str, Any], supplied: dict[str, Any]) -> dict[str, Any]:
        unexpected = supplied.keys() - definitions.keys()
        if unexpected:
            raise ContractError("Unknown inputs: " + ", ".join(sorted(unexpected)))
        values = {}
        for name, definition in definitions.items():
            if name not in supplied and "default" not in definition:
                raise ContractError("Required input: " + name)
            value = supplied.get(name, definition.get("default"))
            TypedValue.checked(value, definition["type"])
            values[name] = copy.deepcopy(value)
        return values

    def start(self) -> None:
        if self.busy:
            raise ValueError("Workflow is already running.")
        self.thread = threading.Thread(target=lambda: asyncio.run(self.execute()), daemon=True)
        self.thread.start()

    @property
    def busy(self) -> bool:
        return self.thread is not None and self.thread.is_alive()

    def stop(self, path: str | None = None) -> None:
        if path:
            self.cancelled_paths.add(path)
        else:
            self.cancelled.set()
        for parent_path, child in self.children:
            if path is None or parent_path == path or parent_path.startswith(path + "/"):
                child.stop()
        self.evidence.emit("stop_requested", path or "root")

    def record(self, path: str, note: str, decision: Any = None) -> None:
        pending = self.evidence.state["manual"].get(path)
        if not pending:
            raise ValueError("This manual execution is no longer waiting.")
        if not isinstance(note, str) or not note.strip():
            raise ValueError("Record evidence notes before continuing.")
        if pending["mode"] == "decision" and type(decision) is not bool:
            raise ValueError("Choose True or False.")
        self.manual_answers[path] = {"note": note, "decision": decision}

    def check(self, path: str) -> None:
        if self.cancelled.is_set() or any(
            path == key or path.startswith(key + "/") for key in self.cancelled_paths
        ):
            raise asyncio.CancelledError("Stopped by user.")
        for parent, deadline in list(self.deadlines.items()):
            if (
                path == parent or path.startswith(parent + "/")
            ) and self.clock.monotonic() >= deadline:
                raise ExecutionFailure("Configured time limit exceeded at " + parent)

    async def execute(self) -> int:
        self.evidence.state.pop("error", None)
        self.evidence.state.update(status="running", started=time.time())
        self.evidence.save()
        try:
            frame = Frame(self, self.workflow.graphs["main"], self.inputs, "root/main")
            outcome = await self.walk(frame)
            if outcome.signal != "finish":
                raise ExecutionFailure("Main execution must reach Finish.")
            self.evidence.state.update(status="passed", result=outcome.value.to_dict())
            visited = {
                entry["card"]
                for entry in self.evidence.state["executions"].values()
                if entry["graph"] == "main"
            }
            for card in self.workflow.graphs["main"].cards.values():
                if card.id not in visited:
                    path = "root/main/" + card.id
                    self.evidence.state["executions"][path] = {
                        "card": card.id,
                        "graph": "main",
                        "name": card.name,
                        "kind": card.kind,
                        "path": path,
                        "status": "skipped",
                        "started": time.time(),
                        "seconds": 0,
                        "attempts": [],
                        "reason": "Execution followed another branch or the loop ran zero times.",
                    }
        except EvidenceRequired as error:
            self.evidence.state.update(status="blocked", error=str(error))
        except asyncio.CancelledError:
            self.evidence.state.update(status="cancelled", error="Stopped by user.")
        except Exception as error:
            self.evidence.state.update(status="failed", error=self.evidence.masker.text(str(error)))
        finally:
            self.evidence.state.update(
                finished=time.time(), globals=self.evidence.masker.object(self.globals)
            )
            self.evidence.state["manual"] = {}
            self.evidence.report()
        return {"passed": 0, "failed": 1, "blocked": 2, "cancelled": 130}[
            self.evidence.state["status"]
        ]

    async def walk(self, frame: Frame, first: str | None = None) -> Outcome:
        if first is None:
            first = next(card.id for card in frame.graph.cards.values() if card.kind == "start")
        current = first
        while True:
            self.check(frame.path)
            card = frame.graph.cards[current]
            outcome = await self.node(frame, card)
            await self.clock.sleep(0)
            frame.results[current] = outcome.value
            if outcome.signal:
                return outcome
            edges = frame.graph.outgoing(current, outcome.port)
            if len(edges) != 1:
                raise ExecutionFailure(f"{current}.{outcome.port}: expected one next card.")
            edge = edges[0]
            if edge.target_port == "next_iteration":
                return Outcome(signal="continue")
            current = edge.target

    async def node(self, frame: Frame, definition: Card) -> Outcome:
        path = frame.path + "/" + definition.id
        self.check(path)
        await self.coordinator.ready(lambda: self.check(path))
        old = self.evidence.state["executions"].get(path)
        if old and old["status"] in ("passed", "recorded"):
            if old.get("redacted_result"):
                raise EvidenceRequired(
                    "Saved output was redacted; explicitly start a new run to recompute it safely."
                )
            for key, value in old.get("global_changes", {}).items():
                self.globals[key] = copy.deepcopy(value)
            self.evidence.emit("resumed", path)
            return Outcome.from_dict(old["outcome"])
        if (
            old
            and old["status"] in ("running", "cancelled", "failed", "blocked")
            and not self.retry
        ):
            raise EvidenceRequired(
                "Interrupted or failed execution requires an explicit retry: " + path
            )
        context = frame.for_node(path)
        card = definition
        entry: dict[str, Any] = {
            "card": card.id,
            "graph": frame.graph.id,
            "name": card.name,
            "kind": card.kind,
            "status": "running",
            "started": time.time(),
            "path": path,
            "attempts": [],
            "expected_seconds": card.settings.get("expected_seconds"),
            "global_changes": {},
        }
        if old:
            entry["previous_attempt"] = copy.deepcopy(old)
        self.evidence.state["executions"][path] = entry
        started = self.clock.monotonic()
        self.evidence.emit("started", path, card=card.id, graph=frame.graph.id)
        self.evidence.save()
        try:
            config = context.resolve(definition.config)
            inputs = context.resolve(definition.inputs)
            for edge in frame.graph.edges:
                if edge.kind == "value" and edge.target == definition.id:
                    value = context.reference("card:" + edge.source, edge.path)
                    if edge.target_port.startswith("config:"):
                        config[edge.target_port[7:]] = value
                    else:
                        inputs[edge.target_port.removeprefix("input:")] = value
            if definition.kind == "join":
                inputs["branches"] = context.reference("card:" + config["parallel"])
            context.inputs = copy.deepcopy(frame.inputs) if definition.kind == "start" else inputs
            card = replace(definition, config=config, inputs=inputs)
            timeout = (
                card.config.get("timeout")
                if card.kind in ("loop", "poll")
                else card.settings.get("timeout")
            )
            if timeout is not None:
                self.deadlines[path] = self.clock.monotonic() + timeout
            retry = card.settings.get("retry", {"attempts": 1})
            for attempt in range(retry["attempts"]):
                try:
                    validation_errors = get_spec(card.kind).validate(card)
                    if validation_errors:
                        raise ExecutionFailure("; ".join(validation_errors))
                    outcome = await context.execute(card)
                    entry.update(
                        status="recorded" if card.kind == "manual" else "passed",
                        outcome=outcome.to_dict(),
                        redacted_result=self.evidence.masker.contains(outcome.to_dict()),
                        result=CardResult(
                            "recorded" if card.kind == "manual" else "passed", outcome, (path,)
                        ).to_dict(),
                    )
                    entry["attempts"].append({"status": entry["status"], "number": attempt + 1})
                    break
                except (EvidenceRequired, asyncio.CancelledError):
                    raise
                except Exception as error:
                    entry["attempts"].append(
                        {
                            "status": "failed",
                            "number": attempt + 1,
                            "error": self.evidence.masker.text(str(error)),
                        }
                    )
                    self.evidence.emit(
                        "attempt_failed", path, attempt=attempt + 1, error=str(error)
                    )
                    if attempt + 1 == retry["attempts"] or (
                        retry.get("errors_contain")
                        and not any(text in str(error) for text in retry["errors_contain"])
                    ):
                        raise ExecutionFailure(str(error)) from error
                    await context.sleep(retry.get("delay", 1) * retry.get("backoff", 1) ** attempt)
            # Collect only descendants' declared writes, never unrelated parallel state.
            for child_path, child in self.evidence.state["executions"].items():
                if child_path.startswith(path + "/"):
                    entry["global_changes"].update(child.get("global_changes", {}))
            entry["redacted_result"] = entry.get(
                "redacted_result", False
            ) or self.evidence.masker.contains(entry["global_changes"])
            return outcome
        except EvidenceRequired as error:
            entry.update(status="blocked", error=str(error))
            raise
        except asyncio.CancelledError:
            entry.update(status="cancelled", error="Stopped by user.")
            raise
        except Exception as error:
            entry.update(status="failed", error=self.evidence.masker.text(str(error)))
            raise ExecutionFailure(str(error)) from error
        finally:
            entry.setdefault("result", CardResult(entry["status"], Outcome(), (path,)).to_dict())
            self.deadlines.pop(path, None)
            entry["seconds"] = round(self.clock.monotonic() - started, 3)
            self.evidence.emit("finished", path, status=entry["status"], seconds=entry["seconds"])
            self.evidence.save()
