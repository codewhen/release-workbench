# What Workbench can do

Workbench is a local visual automation tool. You connect cards into a flowchart instead of writing a script to coordinate every operation. An operation can still run Python, Bash, a script, an executable or an HTTP request when code is the clearest way to do the task.

Use it for repeatable test workflows, generated files, local service checks, staged tasks, parallel quality checks, retry/recovery paths and recorded human decisions. It is not an application builder or a replacement for a programming language.

## The things you work with

| Term | Meaning | Example |
|---|---|---|
| Project | A directory containing YAML, scripts and files | A test-tools folder |
| Workflow | A schema-v3 YAML describing graphs, functions, declarations and layout | workflow-workbench.yaml |
| Library | Registered projects/workflow entries on Home | Several projects in one dashboard |
| Folder | Organization inside the library; normally does not move disk files | Release checks |
| Card | One operation or control-flow construct | Python or If / Else |
| Graph | Connected cards in main or a function | A condition function |
| Function | A reusable graph with declared inputs and return type | File is ready |
| Run | One execution with fresh globals and its own evidence | A test attempt |
| Result | Typed data returned successfully by a card | Boolean false or a JSON object |

## Capabilities at a glance

- Sequential operations, Boolean If/Else, While/Repeat count loops, Break and Continue.
- Explicit Parallel/Join, shared concurrency limits, resource locks and exclusive operations.
- Reusable typed functions, declared run globals and isolated external workspace workflows.
- Python, Bash, script files and programs, plus local file operations and HTTP.
- Cancellable Wait, Poll until, manual decisions and evidence-only approvals.
- Try/Catch/Finally, eligible-operation retries, timeouts and deliberate resume.
- Canvas, keyboard-friendly List, YAML editing, draft saving and validation navigation.
- Live logs, typed returned values, event trails, manual prompts and saved HTML/JSON reports.
- Multiple projects, local folder selection, workflow import, library folders and Starter examples.

## What to understand before automation

Round ports carry execution; square ports supply values. Drawing a dotted area does not create execution scope. If/While/Poll conditions are Boolean functions, not arbitrary implicit truthiness. Functions end with Return; the main workflow ends with Finish. A successful false result is data, not an error.

## Requirements and limits

Python 3.11+ runs the engine. Node is not required for an installed Python wheel. The optional npm launcher needs Node 18+ and Python; first setup downloads Python dependencies. Bash cards require Bash. Executables and libraries used by a workflow must be installed on its host.

The application and bundled documentation run locally. Commands have your local permissions; this is not a sandbox for hostile scripts. Stop does not undo completed writes or requests. Capture and built-in file payloads are limited to 1 MiB. Native Windows acceptance is unverified; Windows instructions are reviewed guidance, not a statement that all native scenarios passed.

The current schema is version 3. Unsupported older YAML is rejected without conversion. Arbitrary Go To cycles, recursive functions/workspaces, For each, Switch, Repeat until, remote agents, schedules, multiplayer editing and dedicated SSH/database cards are not available. Use supported external commands deliberately for operations beyond the built-in catalog.

Continue with [installation](installation.md) and [the first workflow](first-workflow.md).
