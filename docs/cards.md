# Card catalog and typed data

The Python card registry defines categories, defaults, form fields, required values, output contracts and execution ports. The browser loads that catalog; TypeScript workflow types are generated from the published schema. Every operation records a CardResult with execution status, typed value or Void, and evidence references.

| Category | Cards | Purpose |
|---|---|---|
| Layout | Dotted area, collapsible area, annotation | Arrange and label the canvas. Members and positions are separate metadata. |
| Control flows | If/Else; Loop (While/Repeat count); Variable (Get/Set/Update); Calculate; Break; Continue; Parallel; Join; Try/Catch/Finally | Choose paths, repeat bodies, exchange declared values and handle failures. |
| External | Python; Bash; Script file (Python/Bash); Program | Run trusted local automation. |
| I/O | Check path; Read file; Write file; HTTP request | Inspect files, exchange text/JSON, call services. |
| Interventions | Wait; Poll until; Manual decision/approval | Delay, retry a Boolean probe or request recorded human evidence. |
| Functions | Call function; External workspace; Return; Start/Finish markers | Reuse isolated flowcharts and publish results. |

## Values and bindings

Types are Boolean, number, string, array, object and null. `json` accepts dynamic JSON-compatible data; a typed consumer validates it. NaN, infinity, non-string object keys and non-JSON Python objects are rejected. **Void is not null**: Void has no payload; null is a legitimate JSON value. A Void output cannot supply a value connection.

Use Named inputs for visual selection. Constants use JSON syntax, so a string is `"hello"`, a Boolean is `true`, and an array is `[1, 2]`. Advanced YAML references use `{$ref: 'card:producer', path: 'nested.field'}`. Arrays use numeric path segments. Other sources are `input:name`, `env:NAME`, `loop` and `error`. Access globals with Variable cards; direct global references are rejected so conflicts remain visible to the compiler.

Execution wires have round ports and arrowheads. Value wires have square ports, a dashed line and a Value label. Value targets are `config:FIELD` or `input:NAME`. Connecting a value supplies data when the consumer executes. Config bindings are resolved before execution, and actual returned values appear in evidence.

## External cards

**Python** accepts ordinary function-body statements. Inputs arrive as a decoded dictionary. Set its return type. Child-process `print()` output remains logging; a separate structured file carries the return value. Never build code by interpolating inputs into strings. The adapter already serializes inputs.

**Bash**, **Script file** and **Program** return an object containing `exit_code`, bounded `stdout` and `stderr`. JSON capture adds `json` parsed from stdout; stdout must contain exactly one JSON value. Nonzero exit codes fail. Their stdin receives `{"inputs": {...}}`. Program arguments are a string array and do not run through a shell. Script files use Python or Bash explicitly. Bash cards require Bash installed locally.

## I/O and HTTP

File checks support exists/file/directory and return Boolean. Read returns UTF-8 text or decoded JSON. Write accepts text or JSON, creates parent directories and refuses overwrites by default; enable overwrite explicitly for atomic replacement. File operations and configured cwd remain inside the workflow directory, including resolved symlink targets. Capture/read/write is bounded at 1 MiB.

HTTP supports GET/POST/PUT/PATCH/DELETE/HEAD, JSON request bodies, headers and explicit timeouts. The result contains status, headers, text and decoded `json` (null when the response is not JSON). Non-2xx responses fail. HTTP(S) only; cross-origin redirects require an explicit destination request. Use environment references for sensitive headers, declare secret environment names, and inspect redacted evidence. HTTP runs in a cancellable child process.

## Variables and Calculate

Declare a global's type and initial value in Workflow settings. Get returns a copy. Set validates the new value. Update supports arithmetic and array append. Globals reset for each new run and are shared by called functions in that run; function arguments and intermediate results are isolated.

Calculate supports add/subtract/multiply/divide, numeric comparisons, strict equality/inequality and Boolean and/or/not. Boolean operators require Booleans; comparisons never coerce strings or treat 0 as false. Use Python when an operation needs more general computation.

## Interventions

Wait is a cancellable duration. Poll until re-invokes a Boolean function each time, sleeping for the configured interval. Its timeout may explicitly be null for unlimited waiting. It never reuses a previous result. Manual decision returns a Boolean selected by the user plus evidence notes; approval records notes and returns Void. Each invocation, including repeated loop prompts, needs its own answer. Unattended CLI runs block rather than inventing approval.
