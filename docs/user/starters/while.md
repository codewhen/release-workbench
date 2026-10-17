# While with a Boolean function

The Starter project contains this complete example. Work on a copy in your own folder if you want to preserve a fresh reference. Startup never overwrites an edited Starter file.

## What it demonstrates

**Execution:** Start → Repeat; Body → Increment → Next iteration; Done → Finish.

Numeric global count starts at 0. Function Count below three reads it and returns a Boolean comparison.

## Open and run

1. Choose **Home → Starter** and open **While with a Boolean function**. Or download [the standalone YAML](../../examples/starter-while.yaml) into a dedicated folder and register it.
2. Choose **Edit** and inspect the execution wires and selected card fields. Open any function through its selector or Workflow settings.
3. Open the condition function and choose Get Count as Compare’s first source, then Return selects Compare. Run and inspect the repeated condition paths.
4. Save, Validate & review, then Run all. Review declared inputs/manual evidence when prompted.
5. Select operations and completion markers to inspect typed values, logs and event paths. Use Overall run to return to the overview.

## Expected result

Passed; count reaches 3, three body iterations and four condition evaluations.

![While with a Boolean function starter in the Workbench editor](../../assets/screenshots/starter-while.png)

*Captured from the documented downloadable Starter workflow using synthetic data.*

## Terminal use

```bash
workbench validate --config starter-while.yaml
workbench run --non-interactive --config starter-while.yaml --storage ./evidence
```

For manual, the second command intentionally blocks; use the browser. For poll, prepare ready.txt before a passing noninteractive run, or expect the documented timeout. These examples run in the YAML directory and can write local generated output; keep them isolated.

## Change one thing

Try one small edit, validate it, then compare evidence. A new Run all resets globals and repeats operations; it does not resume a previous run. Reconnect both execution and value sources when changing producers. See [completion markers](../tutorials/completion.md), [values](../values.md), and the [card reference](../cards/index.md) for complete field descriptions.
