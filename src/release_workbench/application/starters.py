"""Portable generic starters for the CLI and browser; no application-specific paths."""

from __future__ import annotations

from typing import Any


def card(
    id: str,
    kind: str,
    config: dict[str, Any] | None = None,
    owner: tuple[str, str] | None = None,
) -> dict[str, Any]:
    return {
        "id": id,
        "kind": kind,
        "name": id.replace("-", " ").title(),
        "config": config or {},
        **({"owner": {"card": owner[0], "region": owner[1]}} if owner else {}),
    }


def edge(
    source: str, target: str, port: str = "next", target_port: str = "entry"
) -> dict[str, Any]:
    return {
        "id": source + ":" + port + ":" + target + ":" + target_port,
        "source": source,
        "target": target,
        "source_port": port,
        "target_port": target_port,
        "kind": "flow",
    }


def ref(id: str, path: str = "") -> dict[str, str]:
    return {"$ref": "card:" + id, **({"path": path} if path else {})}


TEMPLATES = {
    "blank": "Blank flowchart",
    "python": "Python return and file output",
    "while": "While with a Boolean function",
    "parallel": "Parallel tasks and typed Join",
    "manual": "Manual Boolean decision",
    "recovery": "Failure recovery and cleanup",
    "poll": "Poll for a file",
}


def starter(name: str, template: str = "blank") -> dict[str, Any]:
    if template not in TEMPLATES:
        raise ValueError("Unknown starter template.")
    main = {
        "cards": [card("start", "start"), card("finish", "finish")],
        "edges": [edge("start", "finish")],
    }
    workflow: dict[str, Any] = {
        "version": 3,
        "name": name,
        "concurrency": 4,
        "inputs": {},
        "globals": {},
        "functions": {},
        "graphs": {"main": main},
        "layout": {},
    }
    if template == "python":
        main["cards"] = [
            card("start", "start"),
            card(
                "compute",
                "python",
                {
                    "code": 'print("This is a log")\nreturn {"message": inputs["message"]}',
                    "returns": "object",
                },
            ),
            card(
                "write",
                "write_file",
                {
                    "path": "output/result.json",
                    "format": "json",
                    "value": ref("compute"),
                    "overwrite": True,
                },
            ),
            card("finish", "finish"),
        ]
        main["cards"][1]["inputs"] = {"message": {"$ref": "input:message"}}
        workflow["inputs"] = {"message": {"type": "string", "default": "Hello workflow"}}
        main["edges"] = [
            edge("start", "compute"),
            edge("compute", "write"),
            edge("write", "finish"),
        ]
    elif template == "while":
        workflow["globals"] = {"count": {"type": "number", "initial": 0}}
        workflow["functions"] = {
            "below-limit": {
                "name": "Count below three",
                "graph": "condition",
                "inputs": {},
                "returns": "boolean",
            }
        }
        workflow["graphs"]["condition"] = {
            "cards": [
                card("start", "start"),
                card("get-count", "variable", {"name": "count", "operation": "get"}),
                card(
                    "compare",
                    "calculate",
                    {"operator": "less_than", "left": ref("get-count"), "right": 3},
                ),
                card("return", "return", {"value": ref("compare")}),
            ],
            "edges": [
                edge("start", "get-count"),
                edge("get-count", "compare"),
                edge("compare", "return"),
            ],
        }
        main["cards"] = [
            card("start", "start"),
            card("repeat", "loop", {"mode": "while", "function": "below-limit"}),
            card(
                "increment",
                "variable",
                {"name": "count", "operation": "update", "operator": "add", "value": 1},
                ("repeat", "body"),
            ),
            card("finish", "finish"),
        ]
        main["edges"] = [
            edge("start", "repeat"),
            edge("repeat", "increment", "body"),
            edge("increment", "repeat", target_port="next_iteration"),
            edge("repeat", "finish", "done"),
        ]
    elif template == "parallel":
        main["cards"] = [
            card("start", "start"),
            card("parallel", "parallel", {"branches": ["first", "second"]}),
            card("join", "join", {"parallel": "parallel"}),
            card("finish", "finish"),
        ]
        main["edges"] = [
            edge("start", "parallel"),
            edge("parallel", "join", "done"),
            edge("join", "finish"),
        ]
        for branch in ("first", "second"):
            main["cards"] += [
                card(
                    branch,
                    "python",
                    {"code": f'return "{branch} completed"', "returns": "string"},
                    ("parallel", branch),
                ),
                card(
                    branch + "-return",
                    "return",
                    {"value": ref(branch)},
                    ("parallel", branch),
                ),
            ]
            main["edges"] += [
                edge("parallel", branch, branch),
                edge(branch, branch + "-return"),
            ]
    elif template == "manual":
        workflow["functions"] = {
            "approved": {
                "name": "Ask for approval",
                "graph": "approval",
                "inputs": {},
                "returns": "boolean",
            }
        }
        workflow["graphs"]["approval"] = {
            "cards": [
                card("start", "start"),
                card(
                    "ask",
                    "manual",
                    {
                        "mode": "decision",
                        "instructions": "Return True to continue, or False to finish.",
                    },
                ),
                card("return", "return", {"value": ref("ask")}),
            ],
            "edges": [edge("start", "ask"), edge("ask", "return")],
        }
        main["cards"] = [
            card("start", "start"),
            card("decision", "if", {"function": "approved"}),
            card("work", "wait", {"seconds": 0.1}),
            card("finish", "finish"),
        ]
        main["edges"] = [
            edge("start", "decision"),
            edge("decision", "work", "true"),
            edge("decision", "finish", "false"),
            edge("work", "finish"),
        ]
    elif template == "recovery":
        main["cards"] = [
            card("start", "start"),
            card("recover", "try"),
            card(
                "failure",
                "python",
                {"code": 'raise ValueError("Demonstration failure")'},
                ("recover", "body"),
            ),
            card("body-end", "return", {}, ("recover", "body")),
            card(
                "catch-end",
                "return",
                {"value": "Recovered", "handled": True},
                ("recover", "catch"),
            ),
            card("cleanup", "wait", {"seconds": 0.1}, ("recover", "finally")),
            card("finally-end", "return", {}, ("recover", "finally")),
            card("finish", "finish"),
        ]
        main["edges"] = [
            edge("start", "recover"),
            edge("recover", "failure", "body"),
            edge("failure", "body-end"),
            edge("recover", "catch-end", "catch"),
            edge("recover", "cleanup", "finally"),
            edge("cleanup", "finally-end"),
            edge("recover", "finish", "done"),
        ]
    elif template == "poll":
        workflow["functions"] = {
            "ready": {
                "name": "File is ready",
                "graph": "probe",
                "inputs": {},
                "returns": "boolean",
            }
        }
        workflow["graphs"]["probe"] = {
            "cards": [
                card("start", "start"),
                card("check", "check_path", {"path": "ready.txt", "type": "file"}),
                card("return", "return", {"value": ref("check")}),
            ],
            "edges": [edge("start", "check"), edge("check", "return")],
        }
        main["cards"] = [
            card("start", "start"),
            card("poll", "poll", {"function": "ready", "interval": 0.2, "timeout": 10}),
            card("finish", "finish"),
        ]
        main["edges"] = [edge("start", "poll"), edge("poll", "finish")]
    for graph_id, graph in workflow["graphs"].items():
        positions = {}
        roots = [item for item in graph["cards"] if not item.get("owner")]
        for index, item in enumerate(roots):
            positions[item["id"]] = {"x": index * 340, "y": 0}
        owned = [item for item in graph["cards"] if item.get("owner")]
        for index, item in enumerate(owned):
            positions[item["id"]] = {
                "x": (index % 3 + 1) * 340,
                "y": (index // 3 + 1) * 300,
            }
        workflow["layout"][graph_id] = {"positions": positions, "areas": []}
    return workflow
