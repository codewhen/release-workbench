# Running and evidence

## The shared coordinator

One coordinator manages slots, pause state, resource locks, exclusive operations and cancellation across every frame and external workspace. Structural containers do not reserve a slot while waiting on children. This prevents nested Parallel/functions from deadlocking a one-slot workflow. The runtime keeps intermediate results per invocation and explicit branch ownership; layout never enters scheduling.

Run all begins from Start using the saved revision. Stop all cancels pending and active work, including subprocesses and nested workflows. Stop this job targets its execution subtree. A cancellation remains cancelled, distinct from a failed assertion or command. Pause scheduling prevents new cards/operations from starting; it does not suspend an already running process.

The process adapter kills the POSIX process group and tracked descendants; Windows uses descendant process termination. Commands remain trusted local programs and may produce side effects before cancellation. Truly detached processes that reparent and leave the process group before they can be observed are outside the cleanup guarantee. Native Windows cleanup has not yet passed its native acceptance suite.

## Progress and inspection

Overall run shows passed/failed/active counts and active execution paths. Select a card to see its returned type/value, elapsed time, attempts, log and failures. Selecting/dragging away disables follow-active; Overall run enables it. Main-canvas loops show iteration paths and repeated condition evaluations. Functions open in their own flowchart. Skipped branches are grey; passed cards green; failed cards red; running cards have a green animated border respecting reduced-motion preferences.

A command may emit newline-terminated structured progress:

```text
::workbench::{"done":3,"total":10,"stage":"Checking packages"}
```

Measured progress is labelled measured. An explicit expected_seconds estimate is labelled estimated and capped before completion. Loops and polling do not invent overall percentages/ETAs. Their evidence retains elapsed time and iteration/probe counts.

## Reports and history

Preview storage is separate, default `.workbench-preview/`:

```text
library.json
runs/RUN_ID/
  summary.json
  events.jsonl
  report.html
  HASH.log
  children/CHILD_RUN_ID/...
```

Summary includes source/config/input fingerprint, status, attempts, outcomes, declared global transitions and hierarchical execution IDs. Events retain every condition evaluation and attempt. HTML is script-free and escapes results/log links. Open saved reports from the run panel or Home's preview history. Report serving is restricted to preview evidence storage.

Declare secret environment names. Literal values are masked in persisted logs, event data and reports, including secret strings split across output chunks. Do not store credentials in workflow YAML. Redacted results cannot safely be reused as computation values on resume; the runner blocks and asks for a new run.

## Resume deliberately

```bash
workflow-workbench run --resume RUN_ID --non-interactive
workflow-workbench run --resume RUN_ID --retry-interrupted --non-interactive
```

A matching run can replay successful saved results and declared global transitions without re-executing successful side effects. Configuration, declared source files or input changes require a new run. Layout changes are ignored by execution fingerprints. Interrupted/failed cards require the explicit retry option. The original attempt remains in evidence. Manual gates are never automatically approved in CI. Supply the same required inputs when resuming.

Run all always starts a fresh run and resets globals. Distinguish that deliberate rerun from resume; externally visible operations may execute again.
