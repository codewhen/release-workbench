import ast
import copy
import json
import unittest
from pathlib import Path

from release_workbench.application.compiler import CompilationError
from release_workbench.application.executors import EXECUTORS, calculate
from release_workbench.application.starters import TEMPLATES, card, edge, ref, starter
from release_workbench.domain.cards import REGISTRY, CardSpec
from release_workbench.domain.models import Card, CardResult, Outcome
from release_workbench.domain.values import VOID, ContractError, TypedValue
from release_workbench.infrastructure.documents import SCHEMA, compile_document, parse_document
from tests.support import by_id, sequence


class Contracts(unittest.TestCase):
    def test_registry_schema_executor_contract(self):
        kinds = SCHEMA["$defs"]["card"]["properties"]["kind"]["enum"]
        self.assertEqual(set(kinds), set(REGISTRY))
        self.assertEqual(set(kinds), set(EXECUTORS))
        for kind, spec in REGISTRY.items():
            with self.subTest(kind=kind):
                self.assertIsInstance(spec, CardSpec)
                self.assertEqual(spec.metadata()["kind"], kind)
                self.assertIsInstance(
                    spec.flow_outputs(Card("x", kind, kind, copy.deepcopy(spec.defaults))), tuple
                )
                json.dumps(spec.metadata())

    def test_typed_values(self):
        for value, kind in [
            (False, "boolean"),
            (0, "number"),
            (None, "null"),
            ([], "array"),
            ({}, "object"),
            ("s", "string"),
        ]:
            with self.subTest(kind=kind):
                self.assertEqual(TypedValue.checked(value, kind).type.value, kind)
        self.assertNotEqual(VOID, TypedValue.checked(None))
        self.assertNotIn("value", VOID.to_dict())
        for value, kind in [
            (0, "boolean"),
            (True, "number"),
            ([], "object"),
            (float("nan"), "number"),
            ({1: "a"}, "json"),
        ]:
            with self.subTest(value=value):
                with self.assertRaises(ContractError):
                    TypedValue.checked(value, kind)
        result = CardResult("passed", Outcome(TypedValue.checked(False)), ("log",)).to_dict()
        self.assertEqual(result["outcome"]["value"]["value"], False)

    def test_starters_compile(self):
        for name in TEMPLATES:
            with self.subTest(name=name):
                compile_document(starter(name, name))

    def test_old_schema_rejected(self):
        for version in (1, 2):
            with self.assertRaisesRegex(CompilationError, "Unsupported workflow version"):
                compile_document({"version": version})

    def test_domain_has_no_effect_adapters(self):
        base = Path(__file__).parents[1] / "src/release_workbench"
        for layer in ("domain", "application"):
            for file in (base / layer).glob("*.py"):
                for node in ast.walk(ast.parse(file.read_text())):
                    if isinstance(node, ast.ImportFrom):
                        self.assertNotIn("infrastructure", node.module or "", str(file))
                        if layer == "domain":
                            self.assertNotIn(
                                (node.module or "").split(".")[0],
                                ("os", "pathlib", "subprocess", "asyncio", "http"),
                            )

    def test_bad_defaults_and_fields(self):
        invalid = [
            card("bad", "wait", {"seconds": -1}),
            card("bad", "loop", {"count": -1}),
            card("bad", "python", {"returns": "wat"}),
            card("bad", "bash", {"capture": "xml"}),
            card("bad", "program", {"argv": [1]}),
        ]
        for operation in invalid:
            with self.subTest(kind=operation["kind"]):
                with self.assertRaises(CompilationError):
                    compile_document(sequence(operation))
        raw = starter("Bad")
        raw["inputs"] = {"x": {"type": "boolean", "default": 0}}
        with self.assertRaises(CompilationError):
            compile_document(raw)

    def test_strict_boolean_calculation(self):
        self.assertIs(calculate("equals", False, 0), False)
        self.assertIs(calculate("not", False, None), True)
        with self.assertRaises(ContractError):
            calculate("and", 1, True)

    def test_cycles_and_unreachable_rejected(self):
        raw = sequence(card("work", "wait", {"seconds": 0}))
        raw["graphs"]["main"]["edges"][-1] = edge("work", "work")
        with self.assertRaisesRegex(CompilationError, "cycle"):
            compile_document(raw)
        raw = starter("Bad")
        raw["graphs"]["main"]["cards"].append(card("orphan", "finish"))
        with self.assertRaisesRegex(CompilationError, "unreachable"):
            compile_document(raw)

    def test_functions_require_boolean_and_returns(self):
        raw = starter("Bad", "manual")
        raw["functions"]["approved"]["returns"] = "number"
        with self.assertRaisesRegex(CompilationError, "Boolean"):
            compile_document(raw)
        raw = starter("Bad", "manual")
        by_id(raw, "return", "approval")["config"] = {"value": "yes"}
        with self.assertRaises(CompilationError):
            compile_document(raw)

    def test_recursive_functions_rejected(self):
        raw = starter("Bad", "manual")
        g = raw["graphs"]["approval"]
        g["cards"].insert(1, card("again", "call", {"function": "approved"}))
        g["edges"][0] = edge("start", "again")
        g["edges"].append(edge("again", "ask"))
        with self.assertRaisesRegex(CompilationError, "Recursive"):
            compile_document(raw)

    def test_function_cannot_break_caller_loop(self):
        raw = starter("Bad", "while")
        by_id(raw, "return", "condition")["kind"] = "break"
        with self.assertRaisesRegex(CompilationError, "cannot target a caller"):
            compile_document(raw)

    def test_branch_values_must_be_joined(self):
        raw = starter("Bad", "parallel")
        by_id(raw, "finish")["config"] = {"returns": "json", "value": ref("first")}
        with self.assertRaisesRegex(CompilationError, "not guaranteed"):
            compile_document(raw)

    def test_value_connection_type_mismatch(self):
        raw = sequence(
            card("n", "python", {"code": "return 1", "returns": "number"}),
            card("use", "call", {"function": "boolean-fn"}),
        )
        raw["functions"] = {
            "boolean-fn": {
                "graph": "fn",
                "returns": "boolean",
                "inputs": {"a": {"type": "boolean"}},
            }
        }
        raw["graphs"]["fn"] = {
            "cards": [card("start", "start"), card("return", "return", {"value": True})],
            "edges": [edge("start", "return")],
        }
        raw["graphs"]["main"]["edges"].append(
            {
                "id": "value",
                "kind": "value",
                "source": "n",
                "target": "use",
                "source_port": "value",
                "target_port": "input:a",
            }
        )
        with self.assertRaisesRegex(CompilationError, "incompatible"):
            compile_document(raw)

    def test_yaml_alias_and_tags_rejected(self):
        for text in ("a: &x [1]\nb: *x", "a: !something x"):
            with self.assertRaises(ValueError):
                parse_document(text)

    def test_finish_output_contract_is_checked_before_running(self):
        raw = starter("Output")
        by_id(raw, "finish")["config"] = {"returns": "boolean", "value": None}
        with self.assertRaisesRegex(CompilationError, "Expected boolean"):
            compile_document(raw)
