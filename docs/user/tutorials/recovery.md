# Errors, retries and cleanup

Workbench distinguishes a False value, an execution failure and cancellation. Return False when a condition is false. Raise/exit nonzero when an operation failed. Stop produces cancelled status; it is never automatically retried or converted into approval.

## Retry a transient operation

Expand a supported operation's **Advanced execution settings** and enter the JSON policy, for example:

```json
{"retry":{"attempts":3,"delay":1,"backoff":2,"errors_contain":["temporarily unavailable"]}}
```

There are at most three attempts total. The initial retry delay is one second, later multiplied by two; only matching failures retry in this policy. The default is off. Python/Bash/Script/Program/HTTP/Check path/Read/Write support it; structural/manual cards do not.

Retries can repeat side effects. Use safe/idempotent operations and inspect attempts rather than assuming a request was not received when its response timed out. Validation and good inputs are preferable to retrying a permanently broken command.

[Download a complete bounded-retry workflow](../../examples/retry.yaml). In a fresh project it writes an attempt counter under output/, fails once, then returns number 2 on its second attempt. It deliberately uses local state to make the retry visible; inspect both attempts in evidence. Clear the generated output before repeating that exact demonstration.

## Try/Catch/Finally walkthrough

Open [Recovery starter](../starters/recovery.md). Its Body Python raises Demonstration failure. Catch completes with Recovered and **Error handled** enabled. Finally executes a short Wait and completes. Done then reaches Finish.

![Recovery regions with explicit completion markers](../../assets/screenshots/card-try.png)

Every connected region needs an owned completion Return or a legal loop-control exit. Catch can read `error.message` and `error.type` through named bindings. A successful Catch path alone does not acknowledge recovery: enable Error handled on its completion Return. Turn that off to see the original error propagate despite successful cleanup.

Finally runs after normal completion, handled/unhandled failure and Break/Continue. A failure in Finally also fails the group. Stop does not launch new user cleanup commands and does not undo completed work. Build external cleanup to be repeatable and callable separately if it is operationally important.

## Preserve evidence

An overall passed recovery can contain an original failed card attempt. Reports retain it intentionally. Inspect the parent Try, child events, error details and final stop reason. Do not erase evidence just to make every card appear green.

Resume can reuse matching successful evidence without repeating completed side effects, but failed/interrupted work requires explicit retry. A fresh Run all resets the run and deliberately executes again. See [running/resume](../running.md) before using either on real systems.
