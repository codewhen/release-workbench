# Workflow Workbench — typed flowchart preview

A free, MIT-licensed local automation workbench. Build flowcharts in the browser, keep them in YAML, execute them with Python, and inspect live output and saved HTML/JSON evidence.

**0.18.0a4 is an intentionally breaking preview. It accepts schema v3 only.** Install it in a separate environment. Do not point it at an older installation's library or run storage. There is no automatic migration and existing files are never converted. The previous stable release remains available separately.

## Run the preview

Python 3.11 or newer is required. End users need neither Node nor a hosted service. Download the preview wheel from [GitHub Releases](https://github.com/codewhen/release-workbench/releases), verify its SHA-256 against `SHA256SUMS`, then:

```bash
python3 -m venv .venv-workbench-preview
.venv-workbench-preview/bin/python -m pip install ./release_workbench-0.18.0a4-py3-none-any.whl
.venv-workbench-preview/bin/workbench create --port 3105
```

On Windows use `.venv-workbench-preview\Scripts\python.exe` and `.venv-workbench-preview\Scripts\workbench.exe`. Native Windows acceptance is **unverified**. Bash cards additionally require Bash on any platform.

Open `http://127.0.0.1:3105/`. Add projects or existing v3 YAML files to Home. Opening a workflow shows Run view; commands execute only after Run all. Change to Edit to configure cards. Saving configuration does not run commands.

## Start here

- [First workflow: browser and CLI](docs/getting-started.md)
- [Card catalog and typed data](docs/cards.md)
- [Functions, main-canvas loops and recovery](docs/control-flow.md)
- [Schema v3 reference](docs/configuration.md)
- [Execution, cancellation, retries and evidence](docs/execution.md)
- [Architecture and contribution guide](docs/architecture.md)
- [Testing and preview release runbook](docs/testing.md)
- [Preview acceptance record and limits](docs/acceptance.md)

## CLI

```bash
workbench                  # Open the dashboard for the current folder
workbench serve            # Same dashboard
workbench run              # Same dashboard; does not execute cards automatically
workbench create           # Wizard: blank YAML here, then open it in the dashboard
workbench create --name "My project" --config my-workflow.yaml
```

`create` asks for a project name and YAML filename, writes a Start → Finish
workflow in the current directory, and opens that workflow. Existing files are
never overwritten. The default shared preview library is
`~/.workbench-preview-v3`, so projects opened from different terminal folders
appear together. Use `--storage PATH` to keep a separate library. `--port 3105`
and `--no-open` are available for dashboard commands. If a matching dashboard is
already running on that port, the CLI registers the project and reuses it.

Examples live in **Starter**, a separate project under
`<storage>/projects/starter`, and a Starter folder on Home. Startup installs
missing examples without replacing edited examples or writing sample YAML into
your project directory.

Advanced terminal tools remain available:

```bash
workbench init --template python --name "Write a result" # Create an example without serving
workbench validate --config workflow-workbench.yaml
workbench run --config workflow-workbench.yaml --non-interactive --input 'message="Hello"'
workbench report --storage ~/.workbench-preview-v3 --run RUN_ID
workbench run --resume RUN_ID --retry-interrupted --non-interactive
```

`workflow-workbench` and `release-workbench` remain aliases. **`run` opens the UI;
`run --non-interactive` executes YAML in the terminal.** Manual decisions require
the browser. Exit codes: **0** passed; **1** failed; **2** invalid or waiting for
evidence; **130** cancelled. A returned Boolean `false` is successful data.

### npm / npx

An optional launcher is prepared in [npm/workbench](npm/workbench/README.md).
It bundles the built wheel, verifies its checksum and installs it into an isolated
Python environment on first launch. Python 3.11+ is still required; npm does not
replace the Python engine. See its README for local `npm pack`, global installation
and npx commands. **It has not been published to npm.**

For a Python-only tool installation from a downloaded wheel:

```bash
uv tool install ./release_workbench-0.18.0a4-py3-none-any.whl
workbench
```

See [npm exec documentation](https://docs.npmjs.com/cli/commands/npm-exec/)
and [uv tool installation](https://docs.astral.sh/uv/guides/tools/).

## Build from source

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
npm --prefix frontend ci
npm --prefix frontend run build
.venv/bin/python -m unittest discover -v
.venv/bin/python -m build
```

See the testing runbook for Ruff, mypy, Vitest, Playwright and clean-wheel verification. Frontend tools are developer dependencies only; the wheel includes built assets. Seven generic starters cover blank flows, Python returns, While, Parallel/Join, manual decisions, polling and recovery.

## Scope

Round ports carry **execution**. Square ports carry **typed values** and never start a card. Explicit Parallel/Join controls concurrency. Functions isolate inputs and intermediate values; declared globals are shared within one run. Layout areas never change execution scope. Commands, scripts and HTTP requests run with the local user's permissions as trusted local configuration; this is not an untrusted-code sandbox.

No paid services, hosted server, remote agents, schedules or multiplayer editing are required. Repeat-until, For-each, Switch and arbitrary Go To are outside this initial catalog. Use functions, While/Repeat count and Python for those automation cases.
