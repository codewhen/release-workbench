"""The canonical card catalog. UI forms and compiler ports use this registry."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, ClassVar

from .models import Card
from .values import ContractError


class CardSpec(ABC):
    kind: ClassVar[str]
    category: ClassVar[str]
    label: ClassVar[str]
    defaults: ClassVar[dict[str, Any]] = {}
    fields: ClassVar[list[dict[str, Any]]] = []
    required: ClassVar[tuple[str, ...]] = ()
    output: ClassVar[str] = "void"

    @abstractmethod
    def flow_outputs(self, card: Card) -> tuple[str, ...]:
        """Execution outputs; value ports are a separate contract."""

    def validate(self, card: Card) -> list[str]:
        errors = [
            f"{card.id}: configure {key}."
            for key in self.required
            if key not in card.config or card.config[key] == ""
        ]
        for descriptor in self.fields:
            value = card.config.get(descriptor["key"])
            if isinstance(value, dict) and "$ref" in value:
                if descriptor["widget"] in ("function", "global", "select", "type", "boolean"):
                    errors.append(
                        f"{card.id}: {descriptor['label']} must be configured statically."
                    )
                continue
            if descriptor["widget"] == "select" and value not in descriptor["options"]:
                errors.append(f"{card.id}: invalid {descriptor['label']}.")
            if descriptor["widget"] in (
                "text",
                "textarea",
                "code",
                "function",
                "global",
            ) and not isinstance(value, str):
                errors.append(f"{card.id}: {descriptor['label']} must be text.")
            if descriptor["widget"] == "type" and value not in (
                "void",
                "null",
                "boolean",
                "number",
                "string",
                "array",
                "object",
                "json",
            ):
                errors.append(f"{card.id}: invalid return type.")
            if descriptor["widget"] == "number" and (
                type(value) not in (int, float)
                or not __import__("math").isfinite(value)
                or not isinstance(value, (float, int))
                or value < 0
            ):
                errors.append(
                    f"{card.id}: {descriptor['label']} must be a nonnegative finite number."
                )
            if descriptor["widget"] == "boolean" and type(value) is not bool:
                errors.append(f"{card.id}: {descriptor['label']} must be Boolean.")
        for key in ("argv", "arguments"):
            if key in card.config and (
                not isinstance(card.config[key], list)
                or any(not isinstance(v, str) for v in card.config[key])
            ):
                errors.append(f"{card.id}: {key} must be an array of strings.")
        return errors

    def metadata(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "category": self.category,
            "label": self.label,
            "defaults": self.defaults,
            "fields": self.fields,
            "output": self.output,
            "ports": list(
                self.flow_outputs(Card("metadata", self.kind, self.label, self.defaults))
            ),
        }


class OperationSpec(CardSpec):
    def flow_outputs(self, card: Card) -> tuple[str, ...]:
        return ("next",)


class TerminalSpec(CardSpec):
    def flow_outputs(self, card: Card) -> tuple[str, ...]:
        return ()


def field(key: str, label: str, widget: str = "text", **extra: Any) -> dict[str, Any]:
    return {"key": key, "label": label, "widget": widget, **extra}


class StartSpec(OperationSpec):
    kind, category, label, output = "start", "Functions", "Start", "object"


class FinishSpec(TerminalSpec):
    kind, category, label, output = "finish", "Functions", "Finish", "json"
    defaults: ClassVar[dict[str, Any]] = {"returns": "void", "value": None}
    fields: ClassVar[list[dict[str, Any]]] = [
        field("returns", "Workflow return type", "type"),
        field("value", "Workflow output", "json", unless={"returns": "void"}),
    ]


class ReturnSpec(TerminalSpec):
    kind, category, label, output = "return", "Functions", "Return", "json"
    defaults: ClassVar[dict[str, Any]] = {"value": None, "handled": False, "returns": "json"}
    fields: ClassVar[list[dict[str, Any]]] = [
        field("returns", "Value type", "type"),
        field("value", "Return value", "json", unless={"returns": "void"}),
        field("handled", "Error handled", "boolean", advanced=True),
    ]


class IfSpec(CardSpec):
    kind, category, label, output = "if", "Control flows", "If / Else", "boolean"
    defaults: ClassVar[dict[str, Any]] = {"function": ""}
    required = ("function",)
    fields: ClassVar[list[dict[str, Any]]] = [
        field("function", "Condition function", "function", returns="boolean")
    ]

    def flow_outputs(self, card: Card) -> tuple[str, ...]:
        return ("true", "false")


class LoopSpec(CardSpec):
    kind, category, label, output = "loop", "Control flows", "Loop", "object"
    defaults: ClassVar[dict[str, Any]] = {
        "mode": "count",
        "count": 3,
        "function": "",
        "limit": 100,
        "timeout": 1800,
    }
    fields: ClassVar[list[dict[str, Any]]] = [
        field("mode", "Loop mode", "select", options=["count", "while"]),
        field("count", "Repeat count", "number", when={"mode": "count"}),
        field(
            "function",
            "Condition function",
            "function",
            returns="boolean",
            when={"mode": "while"},
        ),
        field("limit", "Maximum iterations (null = unlimited)", "json", advanced=True),
        field("timeout", "Time limit in seconds (null = unlimited)", "json", advanced=True),
    ]

    def flow_outputs(self, card: Card) -> tuple[str, ...]:
        return ("body", "done")

    def validate(self, card: Card) -> list[str]:
        errors = super().validate(card)
        mode = card.config.get("mode", "count")
        if mode not in ("count", "while"):
            errors.append(f"{card.id}: choose Count or While.")
        if mode == "count" and (
            type(card.config.get("count", 3)) is not int or card.config.get("count", 3) < 0
        ):
            errors.append(f"{card.id}: repeat count must be a nonnegative integer.")
        for key in ("limit", "timeout"):
            value = card.config.get(key, self.defaults[key])
            if value is not None and (type(value) not in (int, float) or value <= 0):
                errors.append(f"{card.id}: {key} must be positive or null.")
        return errors


class VariableSpec(OperationSpec):
    kind, category, label, output = "variable", "Control flows", "Variable", "json"
    defaults: ClassVar[dict[str, Any]] = {
        "operation": "get",
        "name": "",
        "value": 0,
        "operator": "add",
    }
    required = ("name",)
    fields: ClassVar[list[dict[str, Any]]] = [
        field("operation", "Operation", "select", options=["get", "set", "update"]),
        field("name", "Global variable", "global"),
        field("value", "Value", "json", unless={"operation": "get"}),
        field(
            "operator",
            "Update",
            "select",
            options=["add", "subtract", "multiply", "append"],
            when={"operation": "update"},
        ),
    ]


class CalculateSpec(OperationSpec):
    kind, category, label, output = "calculate", "Control flows", "Calculate", "json"
    defaults: ClassVar[dict[str, Any]] = {"operator": "add", "left": 0, "right": 1}
    fields: ClassVar[list[dict[str, Any]]] = [
        field(
            "operator",
            "Operation",
            "select",
            options=[
                "add",
                "subtract",
                "multiply",
                "divide",
                "equals",
                "not_equals",
                "less_than",
                "greater_than",
                "and",
                "or",
                "not",
            ],
        ),
        field("left", "First value", "json"),
        field("right", "Second value", "json", unless={"operator": "not"}),
    ]


class BreakSpec(TerminalSpec):
    kind, category, label = "break", "Control flows", "Break"


class ContinueSpec(TerminalSpec):
    kind, category, label = "continue", "Control flows", "Continue"


class ParallelSpec(CardSpec):
    kind, category, label, output = "parallel", "Control flows", "Parallel", "object"
    defaults: ClassVar[dict[str, Any]] = {"branches": ["first", "second"]}
    fields: ClassVar[list[dict[str, Any]]] = [field("branches", "Branch names", "json")]

    def flow_outputs(self, card: Card) -> tuple[str, ...]:
        return (*card.config.get("branches", ["first", "second"]), "done")

    def validate(self, card: Card) -> list[str]:
        branches = card.config.get("branches", [])
        if (
            not isinstance(branches, list)
            or len(branches) < 2
            or any(not isinstance(x, str) or not x or x == "done" for x in branches)
            or len(set(branches)) != len(branches)
        ):
            return [f"{card.id}: provide at least two unique branch names, excluding done."]
        return []


class JoinSpec(OperationSpec):
    kind, category, label, output = "join", "Control flows", "Join", "object"
    defaults: ClassVar[dict[str, Any]] = {"parallel": ""}
    required = ("parallel",)
    fields: ClassVar[list[dict[str, Any]]] = [field("parallel", "Parallel card", "text")]


class TrySpec(CardSpec):
    kind, category, label, output = (
        "try",
        "Control flows",
        "Try / Catch / Finally",
        "json",
    )

    def flow_outputs(self, card: Card) -> tuple[str, ...]:
        return ("body", "catch", "finally", "done")


class PythonSpec(OperationSpec):
    kind, category, label, output = "python", "External", "Python", "json"
    defaults: ClassVar[dict[str, Any]] = {
        "code": 'print("Running Python")\nreturn inputs.get("value", True)',
        "returns": "json",
    }
    required = ("code",)
    fields: ClassVar[list[dict[str, Any]]] = [
        field("code", "Python statements", "code", advanced=True),
        field("returns", "Return type", "type"),
    ]


class BashSpec(OperationSpec):
    kind, category, label, output = "bash", "External", "Bash", "object"
    defaults: ClassVar[dict[str, Any]] = {"code": "printf 'Hello workflow\n'", "capture": "text"}
    required = ("code",)
    fields: ClassVar[list[dict[str, Any]]] = [
        field("code", "Bash script", "code", advanced=True),
        field("capture", "Capture", "select", options=["text", "json"]),
    ]


class ScriptSpec(OperationSpec):
    kind, category, label, output = "script", "External", "Script file", "object"
    defaults: ClassVar[dict[str, Any]] = {
        "language": "python",
        "path": "",
        "arguments": [],
        "capture": "text",
    }
    required = ("path",)
    fields: ClassVar[list[dict[str, Any]]] = [
        field("language", "Language", "select", options=["python", "bash"]),
        field("path", "Script path"),
        field("arguments", "Arguments", "json", advanced=True),
        field("capture", "Capture", "select", options=["text", "json"], advanced=True),
    ]


class ProgramSpec(OperationSpec):
    kind, category, label, output = "program", "External", "Program", "object"
    defaults: ClassVar[dict[str, Any]] = {"argv": ["python3", "--version"], "capture": "text"}
    required = ("argv",)
    fields: ClassVar[list[dict[str, Any]]] = [
        field("argv", "Program and arguments", "json"),
        field("capture", "Capture", "select", options=["text", "json"], advanced=True),
    ]


class CheckPathSpec(OperationSpec):
    kind, category, label, output = "check_path", "I/O", "Check path", "boolean"
    defaults: ClassVar[dict[str, Any]] = {"path": ".", "type": "exists"}
    required = ("path",)
    fields: ClassVar[list[dict[str, Any]]] = [
        field("path", "Path"),
        field("type", "Check", "select", options=["exists", "file", "directory"]),
    ]


class ReadFileSpec(OperationSpec):
    kind, category, label, output = "read_file", "I/O", "Read file", "json"
    defaults: ClassVar[dict[str, Any]] = {"path": "", "format": "text"}
    required = ("path",)
    fields: ClassVar[list[dict[str, Any]]] = [
        field("path", "File path"),
        field("format", "Format", "select", options=["text", "json"]),
    ]


class WriteFileSpec(OperationSpec):
    kind, category, label, output = "write_file", "I/O", "Write file", "object"
    defaults: ClassVar[dict[str, Any]] = {
        "path": "",
        "format": "text",
        "value": "",
        "overwrite": False,
    }
    required = ("path",)
    fields: ClassVar[list[dict[str, Any]]] = [
        field("path", "File path"),
        field("format", "Format", "select", options=["text", "json"]),
        field("value", "Content", "json", advanced=True),
        field("overwrite", "Overwrite existing", "boolean", advanced=True),
    ]


class HttpSpec(OperationSpec):
    kind, category, label, output = "http", "I/O", "HTTP request", "object"
    defaults: ClassVar[dict[str, Any]] = {"method": "GET", "url": "", "headers": {}, "body": None}
    required = ("url",)
    fields: ClassVar[list[dict[str, Any]]] = [
        field(
            "method",
            "Method",
            "select",
            options=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD"],
        ),
        field("url", "URL"),
        field("headers", "Headers", "json", advanced=True),
        field("body", "JSON body", "json", advanced=True),
    ]


class WaitSpec(OperationSpec):
    kind, category, label = "wait", "Interventions", "Wait"
    defaults: ClassVar[dict[str, Any]] = {"seconds": 1}
    fields: ClassVar[list[dict[str, Any]]] = [field("seconds", "Seconds", "number")]


class PollSpec(OperationSpec):
    kind, category, label, output = "poll", "Interventions", "Poll until", "boolean"
    defaults: ClassVar[dict[str, Any]] = {"function": "", "interval": 1, "timeout": 1800}
    required = ("function",)
    fields: ClassVar[list[dict[str, Any]]] = [
        field("function", "Boolean probe", "function", returns="boolean"),
        field("interval", "Interval seconds", "number"),
        field("timeout", "Timeout (null = unlimited)", "json", advanced=True),
    ]


class ManualSpec(OperationSpec):
    kind, category, label, output = (
        "manual",
        "Interventions",
        "Manual decision / approval",
        "json",
    )
    defaults: ClassVar[dict[str, Any]] = {
        "mode": "decision",
        "instructions": "Record what you checked.",
    }
    fields: ClassVar[list[dict[str, Any]]] = [
        field("mode", "Mode", "select", options=["decision", "approval"]),
        field("instructions", "Instructions", "textarea"),
    ]


class CallSpec(OperationSpec):
    kind, category, label, output = "call", "Functions", "Call function", "json"
    defaults: ClassVar[dict[str, Any]] = {"function": ""}
    required = ("function",)
    fields: ClassVar[list[dict[str, Any]]] = [field("function", "Function", "function")]


class WorkspaceSpec(OperationSpec):
    kind, category, label, output = (
        "workspace",
        "Functions",
        "External workspace",
        "json",
    )
    defaults: ClassVar[dict[str, Any]] = {"path": "", "inputs": {}}
    required = ("path",)
    fields: ClassVar[list[dict[str, Any]]] = [
        field("path", "Workflow YAML path"),
        field("inputs", "Workflow inputs", "json", advanced=True),
    ]


SPEC_TYPES = (
    StartSpec,
    FinishSpec,
    ReturnSpec,
    IfSpec,
    LoopSpec,
    VariableSpec,
    CalculateSpec,
    BreakSpec,
    ContinueSpec,
    ParallelSpec,
    JoinSpec,
    TrySpec,
    PythonSpec,
    BashSpec,
    ScriptSpec,
    ProgramSpec,
    CheckPathSpec,
    ReadFileSpec,
    WriteFileSpec,
    HttpSpec,
    WaitSpec,
    PollSpec,
    ManualSpec,
    CallSpec,
    WorkspaceSpec,
)
REGISTRY: dict[str, CardSpec] = {spec.kind: spec() for spec in SPEC_TYPES}


def get_spec(kind: str) -> CardSpec:
    try:
        return REGISTRY[kind]
    except KeyError as error:
        raise ContractError(f"Unknown card type: {kind}") from error
