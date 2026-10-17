# Parallel branches and Join

Use Parallel for independent work such as lint and tests. Ordinary execution outputs have one next destination; connecting arbitrary fan-out wires is not the concurrency model.

## Build two branches

1. Add **Parallel**. Workbench adds its paired Join automatically.
2. Set unique Branch names, for example `["first", "second"]`.
3. Connect first → its Python card → an owned Return, selecting that card's result.
4. Do the same for second with its own Return.
5. Keep Parallel.Done → Join → Finish. Do not wire branch ends directly to Join instead of completing their regions.
6. Save and run the [Parallel example](../../examples/parallel.yaml).

![Parallel branch wiring and corresponding Join](../../assets/screenshots/card-parallel.png)

## Read the returned values

Join exposes named typed branch records. A string branch result appears under `first.value`, alongside its type `string`. Use Join's result source plus nested path when a later card needs one value. Select the complete Join result on Finish if the whole collection is useful.

The starter itself leaves Finish at Void while preserving branch/Join evidence. That is intentional: a successful workflow does not have to publish all intermediate data. Change Result source explicitly if you want an overall payload.

## Coordinate shared resources

Concurrent operations defaults to four. A budget of one serializes execution without changing branch structure. Put the same resource name on operations that share a device or fixture. Interactive operations also take the desktop resource; exclusive operations wait for other operations and block new ones while active.

Do not put resource locks on the structural Parallel card. Its children need slots; reserving resources on a waiting container is not how coordination works.

## Handle failures and state

A failed branch prevents Join success. Independent branches can finish collecting evidence, so inspect the entire run instead of assuming the first error cancelled everything. Stop all explicitly cancels outstanding work.

Global read/write or write/write conflicts across branches are rejected, including indirect calls. Return isolated outputs and combine them after Join. This avoids completion-order-dependent global state.

See [Parallel](../cards/parallel.md), [Join](../cards/join.md) and [settings](../settings.md) for exact fields and retry/resource rules.
