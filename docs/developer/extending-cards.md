# Extend a card responsibly

A card's public promise includes its fields, ports, result contract, scheduler policy, browser behavior, examples and documentation. Add it to the catalog only when all of these agree.

## Backend responsibilities

1. Add a specification module under domain/cards, inheriting CardSpec or the relevant OperationSpec/TerminalSpec. Declare kind/category/label, immutable class metadata, defaults, fields, required values, output, scheduling/retry policies and execution ports. Refine result_type when it depends on configuration/declarations.
2. Add its asynchronous executor under application/executors, inheriting CardExecutor/OperationExecutor. Use the ExecutionContext contracts rather than importing filesystem/browser/process adapters into the domain/application layers.
3. For an external effect, add an infrastructure/operations handler inheriting OperationHandler. Consume injected process/services; use workspace_path for bounded project paths and existing evidence/cancellation mechanisms.
4. Register the concrete classes explicitly. Do not add a second scheduler or duplicate hardcoded card lists across services.

## Schema and editor

Update the published JSON Schema and regenerate TypeScript types with `npm --prefix frontend run generate`. Metadata-driven fields should cover normal forms; add a specialized renderer only for a genuine interaction difference. Preserve execution/value separation, immutable editor commands, undo/redo and result bindings.

The inspector's guide link follows `/docs/user/cards/KIND.html`. Add the corresponding page and coverage entry. Record every field/mode, prerequisites, ports, examples, errors and screenshots. Layout-only tools belong to layout metadata rather than executable schemas.

## Required checks

Test ports/required fields/default isolation/result types, runtime success/failure/cancellation, and compiler scope/order rules. Test external effects in temporary projects with synthetic values. Add frontend form/wiring checks where behavior changes. Ensure schema/spec/executor/handler registries and documentation coverage agree.

No workflow should gain a retry or resource policy that its runtime ignores. Never describe future behavior as supported merely because a UI field exists. Read [architecture](architecture.md), [schema](schema.md) and [documentation maintenance](documentation.md).
