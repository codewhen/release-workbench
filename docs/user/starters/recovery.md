# Failure recovery and cleanup

The Starter project contains this complete example. Work on a copy in your own folder if you want to preserve a fresh reference. Startup never overwrites an edited Starter file.

## What it demonstrates

**Execution:** Start → Recover → Finish, with Body/Catch/Finally regions.

Body intentionally fails. Catch Return publishes Recovered with handled enabled. Finally waits briefly.

## Open and run

1. Choose **Home → Starter** and open **Failure recovery and cleanup**. Or download [the standalone YAML](../../examples/starter-recovery.yaml) into a dedicated folder and register it.
2. Choose **Edit** and inspect the execution wires and selected card fields. Open any function through its selector or Workflow settings.
3. Inspect the original failed attempt, the Catch Return acknowledgement and Finally ordering. Disable handled for a deliberate failure demonstration.
4. Save, Validate & review, then Run all. Review declared inputs/manual evidence when prompted.
5. Select operations and completion markers to inspect typed values, logs and event paths. Use Overall run to return to the overview.

## Expected result

Passed after handled recovery, with the original failure retained in evidence.

![Failure recovery and cleanup starter in the Workbench editor](../../assets/screenshots/starter-recovery.png)

*Captured from the documented downloadable Starter workflow using synthetic data.*

## Terminal use

```bash
workbench validate --config starter-recovery.yaml
workbench run --non-interactive --config starter-recovery.yaml --storage ./evidence
```

For manual, the second command intentionally blocks; use the browser. For poll, prepare ready.txt before a passing noninteractive run, or expect the documented timeout. These examples run in the YAML directory and can write local generated output; keep them isolated.

## Change one thing

Try one small edit, validate it, then compare evidence. A new Run all resets globals and repeats operations; it does not resume a previous run. Reconnect both execution and value sources when changing producers. See [completion markers](../tutorials/completion.md), [values](../values.md), and the [card reference](../cards/index.md) for complete field descriptions.
