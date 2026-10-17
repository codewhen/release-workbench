# Wire loops correctly

A Loop repeats connected cards on the main canvas. Moving cards inside a drawn area does not make a loop; the structural owner and round execution wires do.

## The four ports

| Port | Connect it to | Purpose |
|---|---|---|
| Entry | The previous operation | Start the loop once |
| Body | First operation in the loop | Begin one iteration |
| Next iteration | Final body's round output | Complete this iteration and repeat/recheck |
| Done | Next operation outside the loop | Continue once after exit |

![A configured While loop and its owned body](../../assets/screenshots/starter-while.png)

## Repeat count

Open [Repeat count example](../../examples/repeat-count.yaml). It connects Start → Loop.Entry; Loop.Body → Wait → Loop.Next iteration; Loop.Done → Finish. Mode count is 3, so Wait runs three times. Change it to zero to verify the body is skipped successfully. The count must be a nonnegative integer, not a fractional number or quoted text.

## While

The [While starter](../starters/while.md) declares count at zero. Its Boolean function returns count less than three. Main Body updates count by add one and then connects to Next iteration.

The function is reevaluated before each body invocation. Answers are True at counts zero, one and two, then False at three. Thus there are three body executions and four checks. If the first condition is False, no body work runs. Returning a saved old command result instead of recomputing meaningful state is not a changing condition.

## Break, Continue and nesting

Break exits the nearest loop successfully and uses Done. Continue skips the rest of that iteration and rechecks/advances. Their cards have no next output. In a While loop, a Continue path that bypasses the increment can keep the condition True forever. Keep updates on the correct paths.

Nested loops have independent iteration paths and counters. The current loop context exposes index (zero-based) and iteration (one-based). A called function cannot target the caller's loop with Break/Continue. Legal control exits still pass through Try/Finally cleanup unless cancellation stops the run.

## Bounds and results

Default maximum iterations is 100 and duration is 1,800 seconds. The advanced fields accept JSON null for unlimited; do not enter the quoted string `"null"`. A configured bound being hit is a failure, not a normal condition exit. Stop remains available for unlimited work.

The Loop result is an object containing iterations. Body-local results do not become external parent values automatically. Use deliberately declared globals for state, or publish a separate result after Done. Condition-dependent repetition displays elapsed time/counts instead of fabricated progress.

Use [Break](../cards/break.md), [Continue](../cards/continue.md) and [Poll until](../cards/poll.md) when choosing among early exit, skipped iteration or readiness waiting.
