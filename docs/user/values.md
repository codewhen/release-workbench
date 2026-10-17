# Connections and typed values

A workflow answers two different questions: **what runs next?** and **what data does that card receive?** Workbench represents them separately.

## Execution versus value wires

| Connection | Appearance | Effect |
|---|---|---|
| Execution | Round port; arrowed line | Starts the next card after the source completes |
| Value | Square port; dashed Value line | Supplies a field/input when the destination executes |

An execution wire from Python to Finish does not return Python's value automatically. Select that producer in Finish's **Result source** or connect a square value output to its result field. Conversely, wiring Python's value to another card does not cause Python or that destination to execute.

The producer must run before the consumer on every path. A value from an unchosen If branch, future card or another function invocation is unavailable. The compiler rejects known ordering/scope issues; dynamic JSON is checked at consumption time.

## Choose a source without writing reference syntax

JSON value fields such as Calculate's First value have a source picker. Choose **Type a value**, **Result of “Get Count”**, another preceding card, or a declared workflow/function input. A nested field path selects a part of a returned object or array. For example, path `json.ok` reads HTTP's parsed Boolean; `first.value` reads a Join branch value; `items.0.name` reads an array element.

![A comparison using Get Count by name instead of raw reference JSON](../assets/screenshots/compare-source.png)

A configured square wire supplies that field when the consumer runs. Choosing a new source in the editor replaces the previous field wire, avoiding a hidden stale connection. Raw references remain under advanced controls/YAML for people who need them.

## Types and literal values

| Type | Example | Meaning |
|---|---|---|
| boolean | `true`, `false` | A genuine yes/no result; not quoted text |
| number | `3`, `0.5` | Finite integer or fractional JSON number |
| string | `"hello"` | Text, quoted in JSON fields |
| array | `[1, 2]` | Ordered JSON values |
| object | `{"count":3}` | String-keyed JSON properties |
| null | `null` | An intentional JSON null value |
| json | Any of the JSON values above | Dynamic data, validated by typed consumers |
| void | No payload | Operation completed without returned data |

Void and null are different. Wait/approval can succeed with Void; an HTTP `json` property may legitimately be null when the response is not JSON. NaN, infinity, sets, bytes and arbitrary Python objects are not supported results. Boolean false is a successful result: only raised errors/failed contracts/nonzero command statuses are failures.

## Named inputs and declarations

Declare workflow/function inputs with a name, type, optional description and optional default. Use **Required without default** to make an input mandatory; otherwise edit its **Default value**. Descriptions are supported in YAML. Input names must be unique; the declaration form accepts names beginning with a letter/underscore and then letters, digits, underscores or hyphens. No default means required. Browser Run all presents declared inputs for review; terminal callers supply `--input NAME=JSON_OR_TEXT`; External workspace passes an explicit input object.

A declaration does not automatically pass an argument to every Python/Call card. Select the receiving card, use **Named inputs**, add a name and select its source. Python sees `inputs["name"]`. A function call passes those names to its declaration. Script/Program/Bash receive serialized named inputs through stdin; their command-line argument arrays are separate.

## Advanced reference forms

```yaml
inputs:
  count: {$ref: 'card:get-count'}
  ready: {$ref: 'card:request', path: json.ok}
  message: {$ref: 'input:message'}
  token: {$ref: 'env:DEMO_TOKEN'}
  iteration: {$ref: loop, path: iteration}
  failure: {$ref: error, path: message}
```

`card:` references are local to the current graph invocation. `input:` is that graph's declared input. `env:` reads the run/card environment; declare secret environment names for masking. `loop` and `error` only work in the appropriate execution context. Use Variable Get to access globals rather than unsupported direct global references.

Continue with [completion markers](tutorials/completion.md), [functions](tutorials/functions.md) and [variables](tutorials/variables.md).
