# Visual control flow (workflow schema v2)

Use **While** when you want to repeat two, three or more cards while a condition is true. You do not need to create a separate YAML file or draw a connection back to an earlier card.

## Build a While loop

1. Create a **Declare variable** card before the group. Name it `count` and set its Number value to `0`.
2. Add **While**, or Shift-select existing cards and choose **Wrap in group → while**. The wrapper preserves internal connections. Add a join or expand the selection if it has multiple external exit cards.
3. In the group's settings, choose **Compare a value → Variable: count → Less than → 3**.
4. In its **Body** region, add **Update variable**, choose `count`, operation Add, value `1`. Add a Wait or any other operation and connect it after the update.
5. Connect the preceding declaration to the group's Input. Connect Done to the work that should happen after the loop.
6. Save and run. The condition is checked before every iteration. This example runs the body three times. A false initial condition runs it zero times.

The **While group with scoped counter** starter creates this example. Each group has a white header, named regions, resize handles when selected, and a collapse control. List view offers the same nested cards and scope/region selectors. Add cards inside a region with its Add card button; add another dependency from the same source to create parallel work.

## Choose the correct repetition

| Card | When the condition is checked | Completion |
| --- | --- | --- |
| While | Before the body, including the first iteration | Condition becomes false |
| Repeat until | After the body | Condition becomes true |
| Repeat count | Fixed count | Requested count completes |
| For each | Once for each array item | All selected items complete |
| Poll until | Before each probe result is accepted | Probe returns true |

New loops default to 100 iterations and 1,800 seconds. **Unlimited iterations** and **No time limit** remove those bounds explicitly. Configured exhaustion is a failure, not a successful exit. A false While condition or true Until condition exits normally. Stop remains available for unlimited work. Waiting, probes and executable processes obey cancellation and configured timeouts.

For each exposes `loop.item`, zero-based `loop.index` and one-based `loop.iteration`. It runs sequentially by default. Set Parallel iterations to process independent items concurrently; they share the workflow concurrency budget and resources. Per-item published outputs are returned in `result.json.items` in input order. Use a sequential For each if Break is required.

### Conditions can run programs

Choose **Run commands / Python / SSH** to execute a probe. It must exit successfully and print JSON `true` or `false` to stdout. Diagnostics belong on stderr. Invalid output fails the check instead of silently selecting False.

Alternatively, put cards in a While/Until **Condition** region and select a Boolean result from those cards. The entire Condition region executes again at each check. Use argv or environment bindings for dynamic values in shell commands; do not interpolate returned data into shell source.

## Variables and group boundaries

Declare creates a named JSON-compatible value. Assign replaces it. Update adds, subtracts, multiplies or appends an item. The value picker supports constants, previous results, variables, loop values and caught error details. Complex arrays/objects can be entered as JSON.

Loop-local variables persist between iterations. Each parallel branch starts with isolated state; conflicting changes do not become shared global variables. Connect sequential updates when they must observe each other. Use **Merge outputs** for explicit objects; duplicate keys fail unless Keep first or Keep last is selected.

Groups have **Group inputs** bindings and **Published outputs** bindings. Use names and value pickers to configure these. The group publishes only the selected output values. Internal iteration results do not silently become outer variables. A published `count` is available as `steps.GROUP.result.json.count`.

Ordinary dependency connections stay within one group region. Cross boundaries through Input/Done and named data bindings. The canvas remains acyclic. Group membership is separate from dependency connections and supports up to 16 nesting levels.

### Break and Continue

Put these cards on a chosen If or Switch branch inside a loop:

- **Break** completes the nearest enclosing loop and continues from Done.
- **Continue** skips remaining work in that iteration and checks the condition or advances to the next item.

Active parallel work in that iteration is cancelled and cleaned up. Already completed external side effects are not undone. Nested loops handle their own Break/Continue. Finally regions still run during these normal control-flow exits.

## Branching and recovery

**If** selects True or False. **Switch** checks cases in their listed order and selects the first match; its default output handles no match. Connect each labelled output to the appropriate cards and use an explicit join afterward.

**Try / Catch / Finally** has three regions:

1. Try executes the body.
2. A failure enters Catch with `error.message`. Add recovery operations, then **Handle error** to explicitly accept the recovery. Without that card, the group remains failed.
3. Finally executes after normal completion, handled/unhandled failure, Break or Continue. A failed Finally fails the group. **Stop does not launch new cleanup commands**; process cleanup still occurs.

Failed attempts remain red in detailed evidence even when Catch handles the failure and the enclosing group succeeds. Recovery does not rewrite history.

### Retries, Wait and Poll

Executable cards have **Retry on failure** settings: attempts, delay, backoff multiplier and optional exit-code matching. One attempt means retries are disabled. Cancellation and manual evidence gates are never retried automatically. Repeating an operation repeats its real effects; choose retries deliberately.

Wait pauses for a cancellable delay. Poll until repeatedly runs a Boolean probe at its configured interval. These are useful for readiness checks; a failed probe is distinct from a successful `false` result.

## Running, evidence and compatibility

All v2 group leaves and v2 child-workflow calls use one concurrency/resource coordinator. Put resources, desktop mode and exclusive execution on executable cards inside containers. Container-level locks are rejected rather than creating nested deadlocks. Existing v1 workflows retain the legacy scheduler.

Manual gates inside visual groups prompt in the browser for the specific execution. Repeated/parallel gates retain distinct evidence paths. Noninteractive CLI execution exits blocked instead of waiting forever for a human.

The run view shows the active scope, iteration, condition decision, elapsed time and live leaf output. Condition-dependent work has indeterminate progress and no invented ETA. Reports include hierarchical executions, logs, variable transitions, condition evaluations and handled failures. Secrets declared through secret environment names are masked in saved evidence.

Resume retains completed evidence. Interrupted work needs explicit retry (Run selected/enclosing group) or a new run. Retrying a selected group keeps successful upstream prerequisites; it does not imply rollback or exactly-once external side effects. Source/configuration changes require a new run.

### Existing Loop cards

Legacy Loop still repeats a separate child workflow with its original count/until behavior. Its default fill is now white. Use **Convert to canvas group** to produce a v2 draft; inspect and save it explicitly. Conversion preserves count/until limits and retains the original child file. Conflicting IDs, unresolved inputs and unsupported approval/output/group conversions are rejected before saving.

### YAML representation

Schema v2 keeps cards in a single `steps` list. `scope` identifies the containing group; `region` identifies body, condition, catch or finally. `needs` remains the dependency list within that region. Layout positions are relative to the containing group. `control` stores typed settings and named bindings; `retry` stores executable retry policy. Canvas, forms, List, YAML and CLI use this same representation. Both versions are described by `/api/schema` and the packaged JSON Schema.

```yaml
version: 2
name: Count to three
steps:
  - id: count
    name: Initialize count
    kind: declare
    control: {name: count, value: 0}
  - id: repeat
    name: While count is below three
    kind: while
    needs: [count]
    control:
      test: {source: vars.count, operator: less_than, value: 3}
      limit: 100
      timeout: 1800
      outputs: {count: '${vars.count}'}
  - id: increment
    name: Increment count
    kind: update
    scope: repeat
    region: body
    control: {name: count, operator: add, value: 1}
```

## Free starter commands

```sh
release-workbench init --template visual-while --name "While demo" --config release-workbench.yaml
release-workbench validate
release-workbench run --non-interactive
```

Other templates: `visual-foreach`, `visual-poll`, `visual-retry`, `visual-recovery`. The same starters appear in Home. No paid service is required. Native Windows behavior for these additions remains unverified until the Windows test matrix runs.
