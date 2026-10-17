# Poll for a file

The Starter project contains this complete example. Work on a copy in your own folder if you want to preserve a fresh reference. Startup never overwrites an edited Starter file.

## What it demonstrates

**Execution:** Start → Poll → Finish.

Function File is ready checks ready.txt as a file. Probe interval is 0.2 seconds, timeout 10.

## Open and run

1. Choose **Home → Starter** and open **Poll for a file**. Or download [the standalone YAML](../../examples/starter-poll.yaml) into a dedicated folder and register it.
2. Choose **Edit** and inspect the execution wires and selected card fields. Open any function through its selector or Workflow settings.
3. Run in the browser, then create ready.txt in the YAML directory before the ten-second limit. Delete it before another waiting demonstration.
4. Save, Validate & review, then Run all. Review declared inputs/manual evidence when prompted.
5. Select operations and completion markers to inspect typed values, logs and event paths. Use Overall run to return to the overview.

## Expected result

Passed after true; missing marker until timeout fails. if the file already exists, it passes immediately.

![Poll for a file starter in the Workbench editor](../../assets/screenshots/starter-poll.png)

*Captured from the documented downloadable Starter workflow using synthetic data.*

## Terminal use

```bash
workbench validate --config starter-poll.yaml
workbench run --non-interactive --config starter-poll.yaml --storage ./evidence
```

For manual, the second command intentionally blocks; use the browser. For poll, prepare ready.txt before a passing noninteractive run, or expect the documented timeout. These examples run in the YAML directory and can write local generated output; keep them isolated.

## Change one thing

Try one small edit, validate it, then compare evidence. A new Run all resets globals and repeats operations; it does not resume a previous run. Reconnect both execution and value sources when changing producers. See [completion markers](../tutorials/completion.md), [values](../values.md), and the [card reference](../cards/index.md) for complete field descriptions.
