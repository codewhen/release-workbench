# Troubleshooting

Start with the card name, graph and execution path in the error. Save a draft, choose **Validate & review**, and click an issue to locate the card. Runtime failures also have logs, attempts and typed results in Run view.

| Symptom | Likely cause | Action |
|---|---|---|
| Finish is connected but asks for a result | Execution and data are separate | Select Result source, or No result (Void) |
| Expected boolean; received null | Condition/Return has no Boolean result | Return a Python/Calculate/Manual Boolean and select it on Return |
| Cannot use Finish in this location | Marker is in function/owned region | Use Return; keep Finish for main |
| Printed true but condition fails | Logs are not return values | Python: `return True`, Boolean type; Return selects its result |
| “connect exactly one next” | Missing/ambiguous execution continuation | Wire one destination per output; use Parallel for concurrent work |
| An If branch never runs | Only one Boolean route is selected | Check function result; wire both paths for validation |
| Loop never exits | Condition state never changes or Continue skips update | Inspect globals/condition results; keep deliberate bounds |
| Loop body connection rejected | Ownership/loop-back is invalid | Connect Body to owned cards; final wire to Next iteration |
| Global variable missing | Get/Set/Update does not declare it | Add type and initial value in Workflow settings |
| Parallel reports global conflict | Branches read/write overlapping state | Sequence work or return isolated values through Join |
| Returned value unavailable | Producer did not execute on every path | Move it earlier, pass function arguments, or use Join outputs |
| File not found in poll/read | Wrong project folder or missing companion | Check the resolved `workspace`; download scripts/child files too |
| Write fails on second run | Overwrite existing defaults false | Enable only for intended generated replacements |
| Program cannot be found | Executable/PATH mismatch | Separate executable/arguments; select installed interpreter |
| Program JSON capture fails | Stdout is not one JSON value | Use text capture, or emit only JSON and log to stderr |
| HTTP connection refused | Local fixture/service not started | Start fixture and check URL/port |
| Noninteractive workflow blocks | Manual evidence required | Use browser to record it; do not invent approval |
| Pause did not freeze a command | Pause only stops new scheduling | Use Stop to cancel active work |
| Finally did not run after Stop | Cancellation does not launch cleanup | Design idempotent operations; do not rely on Stop rollback |
| Save reports revision conflict | YAML changed outside browser | Save/copy intended changes, reload and reconcile |
| Old error list persists after repairs | Last explicit check described old draft | Edit clears stale issues; run Validate again |
| Invalid local request token/origin | Stale/incorrect local session or origin | Use the printed localhost URL; preserve session file, save/recover drafts before reload |
| Native folder picker unavailable | Headless host/missing Linux picker | Paste absolute path instead |
| npm install reports ETARGET | Requested registry version/tag is unavailable | Check `npm view @codewhen/workbench dist-tags versions --json` and select the intended release |
| npm launcher needs Python | npm wrapper still uses Python engine | Install Python 3.11+ or set WORKBENCH_PYTHON |
| Runtime setup already running | Concurrent bootstrap or interrupted lock | Wait; only remove the named lock after confirming setup stopped |
| Same-name workflows on Home | Different project paths/Starter copy | Filter by project/folder and inspect full path |
| Old YAML version rejected | Only schema v3 supported | Preserve old file; rebuild with supported cards rather than silently converting |

## Diagnose without repeating side effects

Do not repeatedly Run all just to inspect a failure. Read saved evidence first. Fix configuration in Edit, validate, and decide between a fresh run and explicit resume. Failed attempts remain in reports even when Catch marks recovery handled.

When reporting an issue, include the Workbench version, operating system, relevant card/field names, a minimal synthetic workflow and a redacted error/log excerpt. Do not share browser session tokens, credentials or an entire personal storage directory. Native Windows behavior is still unverified; say which commands actually ran there.
