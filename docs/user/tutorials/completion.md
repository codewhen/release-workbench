# Start, Finish and Return

Use this rule first: **main Start → work → Finish**; **function Start → work → Return**. A Parallel/Try owned region also ends with Return, while a loop body normally connects back to Next iteration or uses Break/Continue.

## Choose the right completion

| Location | Begin | Complete | What happens next |
|---|---|---|---|
| Main workflow | Its single Start | Finish | Entire main workflow succeeds |
| Function | Its single Start | Return | Calling card receives the function result |
| Parallel branch | Parallel's named output | Owned Return | Parallel collects that branch output |
| Try Body/Catch/Finally | The matching Try region output | Owned Return | Try coordinates recovery/cleanup |
| Loop body | Loop.Body | Next iteration / Continue / Break | Recheck/repeat or exit via Done |

You do not add another Start inside each branch or loop. These regions already have an entry from their structural card. Layout boundaries never substitute for execution ownership.

## A Python result needs two decisions

1. Wire execution: Start → Python → Finish (or Return inside a function).
2. Select data: on Finish/Return, choose **Result of “Python”** in **Result source**.

The first wire means Python completes before the marker runs. The source selection means the marker publishes Python's returned data. A square Value wire is an alternative to source selection, but cannot replace the round execution wire.

![Completion marker selecting a returned value](../../assets/screenshots/returning-values.png)

## Main example: successful False

Open [Finish example](../../examples/finish.yaml). Python contains `return False` with Boolean return type. Finish selects that result and returns Boolean false. The workflow status is passed. This is how data and status remain distinct.

For a workflow that only writes a file, set Finish to **No result (Void)**. Do not demand Boolean/object data if there is no producer. JSON null is an actual value; Void has no value payload.

## Function example

Open [Return example](../../examples/return.yaml). Main calls Compose greeting with name Reader. Inside the function, Python returns a string and Return selects it. Return hands the string to Call function; main Finish may publish it to an external caller.

All successful function paths need compatible Returns, even when an If chooses only one path at runtime. A function declared Boolean must return true/false. Printing true, returning the string `"true"`, or returning no value is not compatible.

## Common repair sequence

If an error says Finish belongs outside controlled branches, replace it with Return in the relevant function/region. If it says Expected boolean; received null, select the actual Boolean producer or change the deliberately chosen output contract. If it says no execution connection, wire the producer's next output to the completion marker as well.

Read the separate [Start](../cards/start.md), [Finish](../cards/finish.md) and [Return](../cards/return.md) references for exact defaults and fields.
