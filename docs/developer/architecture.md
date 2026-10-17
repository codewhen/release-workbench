# Architecture and contribution guide

The redesign contains one v3 contract and one graph interpreter. No legacy engine, schema adapter or implicit conversion remains on this preview branch. Previous versions stay available through their release artifacts.

```text
src/release_workbench/
  domain/             # values, graph models, calculations
    cards/            # base classes + one specification per card + explicit registry
  application/        # compiler, interpreter, frames, coordinator, ports, progress
    executors/        # one inherited executor per card + shared operation executor
  infrastructure/     # process adapter, YAML, evidence, library persistence
    operations/       # abstract handler + one adapter per external tool
  interfaces/         # CLI and localhost HTTP handlers
  schema.json         # published v3 contract
  static/             # compiled offline frontend, bundled in wheel
frontend/src/
  shared/             # generated workflow types, API client and run contracts
  editor/             # immutable editor commands, history, canvas/layout rendering
  cards/              # inspector, typed ports, registry-driven fields, bindings and connections
  components/         # accessible local primitives
  run/                # live evidence views + cancellable sequential polling
  Home.tsx            # multi-project library
  Editor.tsx          # editor composition
```

## Dependency rules

Domain imports no browser, filesystem, subprocess, HTTP or application adapters. Application depends on domain and its own interfaces. LocalServices wires infrastructure into the runtime via Services, Clock, Evidence and Masker protocols. CLI and server instantiate adapters; neither implements an alternate scheduler.

CardSpec is an inherited abstract definition. Concrete specs register kind, defaults, form fields and ports. CardExecutor is an inherited abstract executor. Concrete control-flow executors return Outcome; the run records a typed CardResult and evidence. External effects dispatch through inherited OperationHandler implementations. Adding a card requires its specification, executor/adapter, schema enum, contracts and browser tests. Do not add another card-type conditional to an unrelated service.

The compiler validates flow cycles, explicit loop ownership, functions/returns, value availability and parallel global access before execution. Runtime type checks handle dynamic JSON. Function graphs use independent Frame instances. Loop regions copy available parent results each iteration; they never reuse old condition results. External workspaces share a coordinator and cancellation but initialize independent globals.

## Frontend contract

Workflow types are generated from schema.json using json-schema-to-typescript. The live catalog supplies form metadata and execution ports. Editor commands are immutable and tested independently from React; undo/redo stores drafts. Positions and areas are separate layout data. Strict TypeScript is required. Code editors/bindings/advanced settings live in the details panel while primary fields remain on cards.

Use small modules, explicit types and readable formatting. Prefer injected dependencies to monkey-patched global effects. Keep provider-specific applications, device IDs, signing, credentials and real logs out of this public repository. All generic tooling remains free and self-hosted.

## Contributions

MIT applies to this project. Open a pull request with a focused problem statement, tests and any schema/behavior changes documented. Run the checks in testing.md. Report Windows support as unverified until native acceptance passes. Do not silently migrate users' old workflows or publish a stable release from an unverified preview.


## Extension and validation rules

Each of the 25 built-in cards has its own specification file under `domain/cards/` and concrete executor file under `application/executors/`. Specifications inherit `CardSpec` through operation/terminal bases or directly. Executors inherit `CardExecutor`, with external operations sharing `OperationExecutor`. Each external tool adapter has its own file and inherits `OperationHandler`; Bash and script handlers specialize `ProgramHandler`.

Scheduling-slot and retry eligibility live on the specification, so the compiler and invocation frame use the same policy. Dynamic result types are resolved by specification methods, rather than repeated card-kind switches. Pure arithmetic and recursive typed JSON comparison live in `domain/calculations.py`. Inherited helpers have real shared behavior; there are no empty file/HTTP executor aliases.

The editor composes `EditorToolbar`, `CardInspector`, canvas, run panel and dialogs. Immutable configuration changes live in `editor/cardCommands.ts`, effective binding readers in `shared/valueBindings.ts`, and result types in `shared/cards.ts`. React components use composition; Python card implementation classes use inheritance. Do not introduce class-based React components just to mimic backend inheritance.

`run/useRunState.ts` owns polling. It issues one cancellable request at a time and invalidates pre-start responses when a newer run state is adopted. UI initialization and validation remain explicit: background polling does not validate a draft.

Architecture tests recursively check layer imports and verify schema/catalog/executor agreement, concrete inheritance and separate implementation modules. New cards must update their public schema contract and explicit registry; registration through incidental import side effects is intentionally avoided.
