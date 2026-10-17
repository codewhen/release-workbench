"""Deterministic documentation examples; never reads the user's projects."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from release_workbench.application.starters import TEMPLATES, card, edge, ref, starter
from release_workbench.domain.cards import REGISTRY
from release_workbench.infrastructure.documents import compile_document, render_document

ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = ROOT / "docs" / "examples"


def sequence(
    name: str, operations: list[dict[str, Any]], result: str | None = None
) -> dict[str, Any]:
    raw = starter(name)
    end = (
        card("finish", "finish", {"returns": "json", "value": ref(result)})
        if result
        else card("finish", "finish")
    )
    cards = [card("start", "start"), *operations, end]
    raw["graphs"]["main"] = {
        "cards": cards,
        "edges": [edge(a["id"], b["id"]) for a, b in zip(cards, cards[1:], strict=False)],
    }
    return raw


def all_examples() -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, str]]]:
    examples = {
        "starter-" + key: starter("Starter: " + title, key) for key, title in TEMPLATES.items()
    }
    config = {
        "python": {
            "code": 'print("Preparing greeting")\nreturn {"message": "Hello workflow", "count": 3}',
            "returns": "object",
        },
        "bash": {"code": 'printf \'{"message":"Hello Bash"}\\n\'', "capture": "json"},
        "script": {
            "language": "python",
            "path": "demo_script.py",
            "arguments": ["reader"],
            "capture": "json",
        },
        "program": {
            "argv": [
                "python3",
                "-c",
                'import json; print(json.dumps({"message": "Hello program"}))',
            ],
            "capture": "json",
        },
        "calculate": {"operator": "less_than", "left": 2, "right": 3},
        "check_path": {"path": "missing.txt", "type": "exists"},
        "write_file": {
            "path": "output/message.json",
            "format": "json",
            "value": {"message": "Hello"},
            "overwrite": True,
        },
        "wait": {"seconds": 0.1},
        "http": {"method": "GET", "url": {"$ref": "input:url"}, "headers": {}, "body": None},
        "variable": {"operation": "update", "name": "count", "operator": "add", "value": 1},
        "workspace": {"path": "child.yaml", "inputs": {"message": "Hello child"}},
    }
    for kind, value in config.items():
        raw = sequence(
            "Card: " + REGISTRY[kind].label,
            [card("operation", kind, value)],
            None if kind == "wait" else "operation",
        )
        if kind == "variable":
            raw["globals"] = {"count": {"type": "number", "initial": 0}}
        if kind == "http":
            raw["inputs"] = {"url": {"type": "string", "default": "http://127.0.0.1:8765/health"}}
        examples[kind] = raw
    examples["read_file"] = sequence(
        "Card: Read file",
        [
            card(
                "prepare",
                "write_file",
                {
                    "path": "output/data.json",
                    "format": "json",
                    "value": {"count": 3},
                    "overwrite": True,
                },
            ),
            card("operation", "read_file", {"path": "output/data.json", "format": "json"}),
        ],
        "operation",
    )
    examples["child"] = sequence(
        "Example child workflow",
        [
            {
                **card(
                    "greet",
                    "python",
                    {"code": 'return {"greeting": inputs["message"]}', "returns": "object"},
                ),
                "inputs": {"message": {"$ref": "input:message"}},
            },
        ],
        "greet",
    )
    examples["child"]["inputs"] = {"message": {"type": "string", "default": "Hello"}}
    examples["finish"] = sequence(
        "Card: Finish",
        [card("answer", "python", {"code": "return False", "returns": "boolean"})],
        "answer",
    )
    examples["finish"]["graphs"]["main"]["cards"][-1]["config"]["returns"] = "boolean"
    examples["start"] = starter("Card: Start")
    examples["if"] = starter("Card: If / Else", "manual")
    examples["if"]["graphs"]["approval"]["cards"][1] = card(
        "ask", "python", {"code": "return True", "returns": "boolean"}
    )
    examples["manual"] = starter("Card: Manual decision / approval", "manual")
    examples["loop"] = starter("Card: Loop", "while")
    examples["poll"] = starter("Card: Poll until", "poll")
    examples["parallel"] = starter("Card: Parallel", "parallel")
    examples["join"] = starter("Card: Join", "parallel")
    examples["try"] = starter("Card: Try / Catch / Finally", "recovery")
    for kind in ("break", "continue"):
        raw = starter("Card: " + REGISTRY[kind].label)
        raw["graphs"]["main"] = {
            "cards": [
                card("start", "start"),
                card("loop", "loop", {"mode": "count", "count": 3}),
                card("operation", kind, owner=("loop", "body")),
                card("finish", "finish"),
            ],
            "edges": [
                edge("start", "loop"),
                edge("loop", "operation", "body"),
                edge("loop", "finish", "done"),
            ],
        }
        examples[kind] = raw
    for kind in ("call", "return"):
        raw = starter("Card: " + REGISTRY[kind].label)
        raw["functions"] = {
            "greet": {
                "name": "Compose greeting",
                "graph": "greeting",
                "inputs": {"name": {"type": "string"}},
                "returns": "string",
            }
        }
        raw["graphs"]["greeting"] = {
            "cards": [
                card("start", "start"),
                {
                    **card(
                        "compose",
                        "python",
                        {"code": 'return "Hello " + inputs["name"]', "returns": "string"},
                    ),
                    "inputs": {"name": {"$ref": "input:name"}},
                },
                card("return", "return", {"returns": "string", "value": ref("compose")}),
            ],
            "edges": [edge("start", "compose"), edge("compose", "return")],
        }
        raw["graphs"]["main"] = sequence(
            raw["name"],
            [{**card("operation", "call", {"function": "greet"}), "inputs": {"name": "Reader"}}],
            "operation",
        )["graphs"]["main"]
        examples[kind] = raw
    examples["repeat-count"] = starter("Repeat count: three iterations")
    examples["repeat-count"]["graphs"]["main"] = {
        "cards": [
            card("start", "start"),
            card("loop", "loop", {"mode": "count", "count": 3}),
            card("work", "wait", {"seconds": 0.05}, ("loop", "body")),
            card("finish", "finish"),
        ],
        "edges": [
            edge("start", "loop"),
            edge("loop", "work", "body"),
            edge("work", "loop", target_port="next_iteration"),
            edge("loop", "finish", "done"),
        ],
    }
    examples["http-io"] = sequence(
        "HTTP and file processing",
        [
            card("request", "http", {"url": {"$ref": "input:url"}, "method": "GET"}),
            card(
                "save",
                "write_file",
                {
                    "path": "output/health.json",
                    "format": "json",
                    "value": ref("request", "json"),
                    "overwrite": True,
                },
            ),
            card("read", "read_file", {"path": "output/health.json", "format": "json"}),
        ],
        "read",
    )
    examples["http-io"]["inputs"] = copy.deepcopy(examples["http"]["inputs"])
    examples["retry"] = sequence(
        "Bounded retry",
        [
            card(
                "attempt",
                "python",
                {
                    "code": 'from pathlib import Path\np = Path("output/attempt.txt")\np.parent.mkdir(exist_ok=True)\nn = int(p.read_text()) + 1 if p.exists() else 1\np.write_text(str(n))\nif n < 2: raise ValueError("temporarily unavailable")\nreturn n',
                    "returns": "number",
                },
            )
        ],
        "attempt",
    )
    examples["retry"]["graphs"]["main"]["cards"][1]["settings"] = {
        "retry": {
            "attempts": 3,
            "delay": 0.01,
            "backoff": 1,
            "errors_contain": ["temporarily unavailable"],
        }
    }
    locations = {}
    for key, raw in examples.items():
        for graph_id, graph in raw["graphs"].items():
            roots = [c for c in graph["cards"] if not c.get("owner")]
            positions = {c["id"]: {"x": i * 340, "y": 0} for i, c in enumerate(roots)}
            regions = {}
            for c in graph["cards"]:
                if not c.get("owner"):
                    continue
                owner = c["owner"]
                key = (owner["card"], owner["region"])
                if key not in regions:
                    regions[key] = len(regions)
                offset = sum(
                    1
                    for other in graph["cards"][: graph["cards"].index(c)]
                    if other.get("owner") == owner
                )
                positions[c["id"]] = {"x": 340 + offset * 340, "y": 380 * (regions[key] + 1)}
            raw["layout"][graph_id] = {"positions": positions, "areas": []}
        if key in REGISTRY:
            kind = key
            found = next(
                (graph_id, c)
                for graph_id, graph in raw["graphs"].items()
                for c in graph["cards"]
                if c["kind"] == kind
            )
            locations[kind] = {"example": key + ".yaml", "graph": found[0], "card": found[1]["id"]}
    for kind, name in [
        ("area", "Dotted area"),
        ("collapsible", "Collapsible area"),
        ("annotation", "Annotation"),
    ]:
        raw = starter("Layout: " + name)
        raw["layout"]["main"]["areas"] = [
            {
                "id": "notes",
                "kind": kind,
                "name": "Prepare the example",
                "position": {"x": -40, "y": -80},
                "width": 660,
                "height": 330,
                "members": ["start"],
                "collapsed": False,
            }
        ]
        examples[kind] = raw
    for raw in examples.values():
        compile_document(raw)
    return examples, locations


def write_examples() -> None:
    examples, locations = all_examples()
    EXAMPLES.mkdir(parents=True, exist_ok=True)
    for key, raw in examples.items():
        (EXAMPLES / (key + ".yaml")).write_text(render_document(raw), encoding="utf-8")
    (EXAMPLES / "demo_script.py").write_text(
        'import json, sys\npayload = json.load(sys.stdin)\nprint(json.dumps({"name": sys.argv[1], "inputs": payload["inputs"]}))\n',
        encoding="utf-8",
    )
    (ROOT / "docs-site" / "card-examples.json").write_text(json.dumps(locations, indent=2) + "\n")
    print(f"Wrote {len(examples)} validated documentation workflows.")


if __name__ == "__main__":
    write_examples()
