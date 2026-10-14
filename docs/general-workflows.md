# Workflow Workbench: commands, decisions and reusable workflows

The workbench runs trusted local programs and shell scripts, connects their results, and saves evidence. Release testing is one use case. It also fits data preparation, backups, project maintenance, documentation builds, and local automation. No Node installation is needed for the packaged browser app.

## Start in the browser

1. Open Home and register your project folder.
2. Choose **New workflow**, enter a name, then choose a starter.
3. Choose **Add card** (or a typed card button) to add an independent card. Drag or click its output and another card’s input to connect them. Connect one output to several cards for parallel work. **Add next** remains a shortcut for a connected step. Click a connection and choose **Disconnect** to remove it; Undo/Redo restores changes. Save does not run anything.
4. Choose Run, inspect results and respond to manual gates when prompted.

The starters are shared with the CLI:

| Starter | What it does |
| --- | --- |
| `blank` | Empty workflow for your own steps |
| `tests` | Discover and run Python unittest tests; replace with your test command |
| `release` | Tests followed by a manual approval gate |
| `branching` | Python JSON result → If → True/False → join |
| `data-pipeline` | Create sample CSV, calculate a total, verify returned row count |
| `backup` | Create a demonstration file, copy it and verify identical bytes |
| `project-checks` | Inspect root Python files, check syntax when present, otherwise report absence |

```bash
workflow-workbench init --template branching --name "Process data" --config workflow-workbench-data.yaml
workflow-workbench serve --config workflow-workbench-data.yaml
workflow-workbench run --config workflow-workbench-data.yaml --non-interactive
```

`workflow-workbench` and `release-workbench` are compatible entry points to the same engine. The default filename remains `release-workbench.yaml` for existing users. Home discovers either prefix; any other YAML filename can be registered explicitly. Example artifacts are written under `.workbench/demo/`. Backup and data starters operate on demonstration files; edit paths and commands before adapting them to your own data. Project checks inspect this project; they do not replace its language-specific test suite.

## Capture a program's return

Any supported program or shell can produce the data: Python, Bash, PowerShell, a compiled binary, Node, or another installed interpreter. Use **Capture last command result** on a Command card:

- **Exit code only:** exposes `steps.ID.result.exit_code` after a successful command.
- **Text output:** also exposes `steps.ID.result.stdout`.
- **JSON output:** also exposes `steps.ID.result.json`, including nested fields and array indices.

The capture is the final command's combined stdout and stderr, limited to 1 MiB, with surrounding whitespace trimmed. JSON mode expects the entire captured output to be one valid JSON value. Keep diagnostic output in a separate file if you need JSON capture; use report patterns to retain that file. Larger payloads belong in workspace report files, not result capture. Saved results and logs use the existing declared-secret masking.

```yaml
- id: inspect
  name: Inspect input data
  kind: command
  capture: json
  commands:
    - argv: ['${python}', '-c', 'import json; print(json.dumps({"ready": True, "count": 3}))']
```

A shell script can print the same JSON object. On Windows use a platform command for PowerShell and `ConvertTo-Json -Compress`; these commands are examples, not native Windows verification.

Default successful exit codes are `[0]`. A probe that intentionally returns `1` for a normal negative result can declare `success_codes: [0, 1]` and branch on its exit code. Do not broaden successful codes on a build or test to hide failures. An unexpected exit code fails the step and blocks its dependents; it does not select False.

## Add an If card

Choose **Add If condition**. Set its prerequisite to the command returning data, then configure:

1. **Result source:** for example `steps.inspect.result.json.ready`, `steps.inspect.result.exit_code`, or `inputs.environment`.
2. **Operator:** Equals, Does not equal, Greater than, Less than, Contains, or Is true.
3. **Comparison type/value:** Boolean, Number, Text, or Null. Is true needs no comparison value.
4. **Add True branch** and **Add False branch**, or drag their labelled output handles to existing cards.

Sources must reference workflow inputs or ancestor step results. Comparisons read data; they do not evaluate code expressions. Boolean true differs from the number 1 or the text "true". Missing fields, invalid JSON and incompatible numeric comparisons fail visibly.

```yaml
- id: decide
  name: If data is ready
  kind: condition
  needs: [inspect]
  condition:
    source: steps.inspect.result.json.ready
    operator: is_true
- id: process
  name: Process ready data
  kind: command
  needs: [decide]
  when: {step: decide, equals: true}
  commands: [{argv: ['${python}', '-c', 'print("Process ready data")']}]
- id: defer
  name: Defer unavailable data
  kind: command
  needs: [decide]
  when: {step: decide, equals: false}
  commands: [{argv: ['${python}', '-c', 'print("Try again later")']}]
```

The untaken branch is **Skipped**, and that status propagates to descendants on that path. Skipped is distinct from Passed, Failed and Disabled. A run can complete with deliberately skipped branches; disabled required work still blocks its dependents. Input prompts for conditional steps wait until their branch is selected. Pre-run input requirements for a selected ancestor producer are handled normally.

## Bring branches together

Add a step depending on both branch endpoints. Choose **Join prerequisites → At least one path succeeds; others may be skipped** (`join: any`). The join waits for all prerequisites to become terminal, requires at least one successful prerequisite, and blocks if any prerequisite failed, was disabled or was cancelled. If every path is skipped, the join is skipped too.

The default `join: all` requires all paths to run successfully; a skipped prerequisite skips that dependent. Required approval gates cannot silently skip: put an explicit join before approval, keep all required checks in the approval's dependency ancestry, and record human evidence.

## Run another workflow from a branch

Choose **Add Run workflow** and enter an existing YAML filename in the same project root. A True or False branch can use this card to choose a different workflow. The child runs as a supervised local job; its CLI output streams into the parent log, and its reports stay under the parent run's `children/STEP/` folder. Failed or blocked children fail the parent card. Recursive child references are rejected; maximum nesting is 16 levels.

```yaml
- id: selected_workflow
  name: Run the ready-data workflow
  kind: workflow
  workflow: workflow-workbench-process.yaml
  needs: [decide]
  when: {step: decide, equals: true}
```

Child workflow cards can live in subfolders, declare the parent's workspace and receive typed workflow_inputs bindings. They do not open child manual gates in the parent browser; put human gates in the parent workflow. For another project workspace, use an explicit Command card. Each child obeys its own concurrency limit; the parent counts the child as one job, so use parent resource locks or exclusive mode to prevent unwanted overlap across children.

## Useful workflow patterns

- **Data pipeline:** inspect CSV → If rows exist → transform → validate → save report.
- **Documentation:** generate docs → check links → manual preview → package the site.
- **Backup:** copy files → compare hashes → If equal → retention review. Keep deletion behind an explicit manual gate until you have tested recovery.
- **Multi-language project checks:** detect language → choose the appropriate test workflow → join → aggregate evidence.
- **Local API health checks:** run your own Python or curl probe → capture JSON → If healthy → run dependent local work.
- **Release:** build/test branches → joins → package → manual approval. Full release readiness still needs the platform-specific evidence.

## Remaining capabilities to prioritize

The current engine supports commands, manual gates, conditions, child workflows, parallel jobs, input forms, resources, timeouts, cancellation, progress and reports. It remains a local, explicitly started DAG runner.

Useful next additions, rather than features already supported:

1. **Retries with backoff:** explicit transient-error rules; no automatic retry of irreversible steps.
2. **Foreach:** per-item collection iteration; fixed-count and Boolean-stop Loop cards are already supported.
3. **Scheduling and triggers:** local schedules, file changes, webhooks; define credential and network boundaries first.
4. **Richer data bindings:** typed step-output variables and child input mappings, beyond current conditions and JSON-to-input file outputs.
5. **Reusable connectors:** declarative HTTP, database and notification adapters. Existing command steps can call installed tools today; dedicated UI adapters are not included.
6. **History comparison and retention:** compare results and timing across runs, then explicitly manage archived evidence.
7. **Native Windows verification:** required before claiming parity for execution, cancellation and shell behavior.

Remote workers, hosted services, shared editing and paid integrations remain outside this version. The engine name and repository stay compatible while the browser presents Workflow Workbench.

For comparison with established engines, see the official [Kestra loop and subflow guide](https://kestra.io/docs/how-to-guides/loop) and [n8n flow-logic documentation](https://github.com/n8n-io/n8n-docs/blob/main/docs/build/flow-logic/README.md). Their documented loop/subflow patterns inform the roadmap above; they are not dependencies of this application.

## Organized child workflows

Set `workspace: ../..` in YAML stored two directories beneath the project root. Commands, child workflow paths, outputs and reports resolve beneath that declared workspace; configuration remains in its own file. The declaration may include parent directories but cannot be absolute. Only open trusted local configuration. Child workflows must declare the same workspace as the parent. `workflow_inputs` maps child input names to typed values or `${input.NAME}` / `${steps.ID.result.FIELD}` bindings. Parent browser inputs should declare required fields used by children. Child runs remain noninteractive: prepare devices through a parent manual gate and pass a preparation flag when children have conditional preparation gates. Manual gates reached inside a child still block its CLI run. Home discovers conventional workflow files beneath `workflows/` as well as the project root.

## Bounded Loop cards

Choose **Loop** from Add card/right-click. Point **Child workflow YAML** at the saved body workflow and set an iteration limit (1–1000). With no stop result it repeats exactly that many times. Set **Stop when body result is true**, for example `steps.check.result.json.ready`, to repeat until a strict Boolean becomes true. False repeats; missing/non-Boolean data, body failures and reaching the limit while false fail the loop and block dependents. It does not retry failed commands silently.

Loop is a structured alternative to Go To: the body can contain commands, scripts, tests, If branches and parallel joins without adding back-edges to ordinary cards or competing with a one-to-one If Entry port. Extract the steps to repeat into a child workflow; connect the Loop card's output to the next step. Ordinary graph cycles are still rejected.

Set a delay and the total timeout as needed. Each iteration gets a fresh run and separate report under the Loop attempt's child folder; partial evidence and a loop summary survive cancellation/failure. Stop cancels the current body through normal process supervision. Repeating a write/build/remote operation repeats its real side effects; cancellation does not undo completed iterations. Manual gates in a body block its noninteractive execution, so prepare through the parent first.

`WORKBENCH_LOOP_ITERATION` is a 1-based environment value available to body commands. Typed **Child workflow inputs** are passed on every iteration. The whole Loop holds its declared resource/exclusive settings; parallel body jobs use the body workflow's concurrency.

Home and CLI offer **Repeat a workflow three times** and **Loop until ready (bounded)**. They create both parent and body YAML files without overwriting existing files. CLI: `workflow-workbench init --template loop-until --name "Wait until ready" --config release-workbench-wait.yaml`. The example body reports ready on iteration 3. No paid tools are involved.
