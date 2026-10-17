# Python

Run ordinary Python statements in a child process and return structured typed data.

## Before you start

Work in **Edit** view in a saved project folder. Start with the downloadable example in its own directory; it includes the surrounding wiring needed for this card. See [connections and values](../values.md) if ports or result sources are unfamiliar.

## Behavior and ports

Enter function-body statements in advanced **Python statements**. The engine wraps them in a function, so `return` works without defining your own function. Access named arguments through the `inputs` dictionary. Set **Return type** to the result you intend to produce.

`print()` writes logs; `return` publishes data through a separate structured channel. `return False` is a successful Boolean; raising an exception fails the card. A missing return yields Python None: use `null`/dynamic JSON if intended, rather than claiming another type. Return only JSON-compatible values, not sets, bytes, class instances, NaN or infinity. Use `void` only when no return payload is needed.

The worker uses the installed Workbench Python interpreter. Third-party imports must be available to that interpreter; a Script/Program card can deliberately use a project-specific environment instead. **Working directory** defaults to the workflow folder and must remain inside it.

**Execution outputs:** `next`. **Catalog value contract:** `json`; configuration, declared variables/functions and runtime validation refine the actual type as described above. Inspect the typed return value after running.

## Fields and defaults

| UI field | YAML key | Default | Rules and visibility |
|---|---|---|---|
| Python statements | `code` | `"print(\"Running Python\")\nreturn inputs.get(\"value\", True)"` | Advanced; Required |
| Return type | `returns` | `"json"` | Primary setting |

This operation supports resource locks, interactive/exclusive scheduling and a configured timeout. Retry is supported but off by default. Use it only when repeating the operation is safe. See [common execution settings](../settings.md) for field-by-field configuration, cancellation and evidence.

## Configure it in the browser

1. Add Python, select it, and expand its advanced fields in the details panel.
2. Enter `print("Preparing greeting")` followed by `return {"message": "Hello workflow", "count": 3}`.
3. Select return type `object`.
4. Connect Start → Python → Finish. Choose Python in Finish's Result source.
5. Save and run. The log shows Preparing greeting; the result is an object, not that log text.
6. Add a Named input such as `name`, then read it as `inputs["name"]` without inserting it into source code.

## Configured example

![Python configured in Workbench with its details panel and flowchart](../../assets/screenshots/card-python.png)

*Actual Workbench screenshot from a disposable documentation project. Select the image to enlarge it in the documentation site.*

[Download the complete runnable workflow](../../examples/python.yaml). Place it in a dedicated folder, add any companion files described above, then use **Home → Add project or file** to open it. It is configured for the current schema; it is not a screenshot-only mockup.

This is the selected card's YAML configuration. The download also includes its Start, completion markers, graph declarations and execution connections:

```yaml
id: operation
kind: python
name: Operation
config:
  code: "print(\"Preparing greeting\")\nreturn {\"message\": \"Hello workflow\", \"\
    count\": 3}"
  returns: object
```

Bindings such as `$ref` in this YAML are represented by named value choices in the browser. They supply values and never start execution. Save your own edits, validate, and compare **Run** evidence with the behavior described above.

## Common mistakes and recovery

Indent ordinary blocks correctly; do not indent the whole script for the generated wrapper. A print-only script does not return printed text. Missing modules must be installed into the appropriate environment. Capture is bounded; excessive output fails rather than growing indefinitely.

If validation reports an issue, click that issue to locate the card on its flowchart. Correct its fields, scope or connections, then Validate again. Check the selected execution's log, attempts and typed result for runtime errors before deliberately rerunning side effects.

## Next example

Return Boolean from Python in a condition function, or return an object and feed it to Write file.

Continue with [the control-flow tutorials](../tutorials/completion.md), [running and evidence](../running.md), or the [card catalog](index.md).
