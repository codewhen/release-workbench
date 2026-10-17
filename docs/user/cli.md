# CLI reference

`workbench` is the primary executable. `workflow-workbench` and `release-workbench` remain aliases to the same CLI. Run `workbench --help` and `workbench COMMAND --help` for installed-version options.

## Everyday commands

| Command | Result |
|---|---|
| workbench | Open the dashboard for the current folder |
| workbench serve | Same dashboard behavior |
| workbench run | Open dashboard; no automatic card execution |
| workbench create | Ask for name/filename, create blank YAML here, open it |
| workbench --version | Show installed package version |

`serve` and dashboard `run` accept `--project PATH`, `--storage PATH`, `--port NUMBER` and `--no-open`. `create` always uses the current directory; pass `--name`/`--config` to skip its questions. It also supports storage/port/no-open. Default YAML filename is workflow-workbench.yaml, default storage is ~/.workbench-preview-v3, and default port is 3104.

Repeated launches reuse a matching dashboard on the chosen port. Another Workbench library on that port is rejected; choose another port or intentionally use its storage. Close the original serving terminal with Ctrl+C to stop it. A reuse-only CLI process exiting does not stop that server.

## Deliberate terminal execution

```bash
workbench run --non-interactive --config checks.yaml --storage ./evidence --input 'message="Hello"'
```

Inputs use NAME=JSON_OR_TEXT. JSON Booleans/numbers/objects keep their types; unparseable JSON is treated as text. Quote according to your shell. Pass required inputs again for resume. No browser is opened. Manual decisions/approvals block without recorded evidence.

Run resolves its workspace from the config YAML's parent directory. `--resume RUN_ID` selects saved evidence under the same storage; `--retry-interrupted` permits deliberate retry of unsuccessful/interrupted work. Read [running](running.md) before using it on side effects.

## Advanced utilities

```bash
workbench init --name "Count to three" --template while --config loop.yaml
workbench validate --config loop.yaml
workbench report --storage ./evidence --run RUN_ID
```

`init` writes a chosen Starter template without serving. It refuses to replace a file. Available templates are blank, python, while, parallel, manual, recovery and poll. `validate` checks schema/readiness without running commands. `report` prints a saved report path and only resolves inside the selected evidence storage.

## Exit codes

| Code | Meaning |
|---|---|
| 0 | Selected terminal work passed, or a CLI utility completed |
| 1 | Workflow execution failed |
| 2 | Invalid configuration/request or blocked required evidence |
| 130 | Cancelled/interrupted work |

Boolean False is not an exit-code failure. A dashboard's successful launch/reuse does not certify that any workflow passed; inspect its run evidence.

For locally packed npm usage and platform prerequisites see [installation](installation.md).
