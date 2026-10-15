# Functions and structured flow

## Sequential execution

Each graph has exactly one Start. Main paths finish at Finish; successful function paths finish at Return. Each execution output connects to exactly one next card. If has mutually exclusive True/False outputs. Parallel is the explicit way to execute concurrent work. Ordinary execution cycles are rejected.

Finish defaults to Void. To publish a result to an external caller, set Finish's Workflow return type and value. Functions declare their inputs and return type. Each invocation gets its own inputs and intermediate-value map; values from one invocation cannot leak into the next. Calls are nonrecursive in this preview. A function cannot Break or Continue its caller's loop.

## While and Repeat count

A compact Loop has four execution ports:

- **Entry** starts the loop after its previous card.
- **Body** starts connected cards on the same canvas.
- **Next iteration** accepts that body's final execution output.
- **Done** runs once after the loop exits.

For example: Start → Loop; Loop.Body → Calculate → Write file → Loop.Next iteration; Loop.Done → Finish. Body cards explicitly store `owner: {card: loop-id, region: body}`. The editor assigns ownership when wiring a branch. This is execution scope, unlike layout-area membership.

While invokes its Boolean condition function **before** every iteration. False exits immediately, including before iteration one. Repeat count runs the requested nonnegative integer count. Break exits the nearest enclosing loop successfully. Continue skips remaining body work and checks the condition/advances count. A function call cannot jump back into its caller.

New loops default to 100 iterations and 1,800 seconds. Set either advanced bound to JSON `null` to explicitly allow unlimited iterations or duration. A configured limit produces a failure with a reason, not a silent pass. Nested loops keep independent paths, indexes and evidence. `loop.index` is zero-based; `loop.iteration` starts at one. Loop results contain the completed iteration count. The body does not silently publish its intermediate values outside the loop.

## Parallel and Join

Adding Parallel creates its matching Join. Configure unique branch names. Connect each branch to its own cards and end it with an owned Return marker; that marker publishes the branch value. Parallel.Done connects to Join, then onward. Join returns an object of **named typed results**, such as `{"first":{"type":"number","value":3}}`. It does not merge globals.

The coordinator uses the configured shared concurrency budget (default four), resource locks and exclusivity across nested work and external workspace calls. The compiler rejects cross-branch read/write and write/write conflicts for globals, including reads/writes inside called functions. Read/read is safe. Sequence conflicting operations, or return independent branch values through Join. An independent branch may finish collecting evidence after another fails; Join does not pass until all branches succeed.

## Try, Catch and Finally

Try has Body, optional Catch, optional Finally and Done. Each connected region owns its cards and ends with an explicit Return marker (or legal loop-control exit). Body failures record their original failed attempts. Catch receives `error.message` and `error.type`. Enable **Error handled** on Catch's completion Return to acknowledge recovery. Without that acknowledgement, the Try fails even if Catch executes successfully.

Finally runs after success, handled/unhandled failure and Break/Continue from the controlled body. User Stop cancels the run and does **not** launch new cleanup commands. A failed cleanup also fails the group. Structure important cleanup with idempotent commands; cancellation cannot guarantee undo of prior side effects.

## External workspace workflow

Select a YAML path and pass explicit inputs. The child validates independently, uses its YAML directory as cwd, initializes its own globals and returns its Finish result. It shares cancellation and concurrency with the parent. Workspace recursion is rejected. Its reports remain nested beneath the parent's evidence. Child manual decisions appear in the parent's prompt surface. A workflow's layout never changes these rules.
