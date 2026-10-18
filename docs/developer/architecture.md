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

## Library organization

`domain/library_folders.py` validates logical folder creation, subtree relocation and removal without filesystem dependencies. `Library.organize` atomically saves the validated metadata replacement; HTTP handlers delegate to it. Folder paths in library.json use `/` as hierarchy, independently of OS project paths. Existing top-level labels remain unchanged. No folder operation rewrites workflow YAML or execution evidence.

The Home shell owns dialogs and API mutations; `home/LibraryBrowser.tsx` renders the responsive folder/workflow grids, breadcrumbs and keyboard/context navigation. `home/folders.ts` owns shared path relationships. Starter registration assigns only newly discovered entries, preserving user organization across restarts.

## Browser locations

`navigation/location.ts` owns URL parsing, typed query patches, History API notifications and guarded navigation. Home filters and editor location use the same external location store; `navigation/useEditorLocation.ts` validates graph/selection against the loaded workflow. UI navigation pushes history, search and automatic active-card tracking replace it. Back/Forward traversals leaving a dirty workflow are reversed until an explicit in-page confirmation permits them; graph edits stay in the editor state rather than URLs. Readable `/workspace`, `/folders/...` and `/workflows/...` paths are canonical; legacy query links are normalized with replaceState. `interfaces/application_routes.py` recognizes only supported application paths for HTML-shell fallback, leaving unknown API/file/report paths and traversal attempts as real 404s. The same origin/token checks protect mutation endpoints on every page.

## Child workflow navigation

The protected `open-workspace` mutation resolves a selected workspace card through `interfaces/workspace_navigation.py`, validates the child document and reuses its library registration. It accepts the current schema-valid draft without saving it. Runtime evidence records `child_source`, allowing Run navigation to select the executed file for dynamic paths. The shared `cards/WorkspaceLink.tsx` opens the definition in Edit mode or the exact nested execution in Run mode. A `run` URL selector identifies the child invocation, not an alias in the workflow-ID map. The server resolves it through retained root run trees, validates its source against the registered workflow, and serves the executed configuration snapshot. State, manual evidence, cancellation and report links target that same invocation. Child execution activity is tracked independently of dedicated root threads. Live contexts last for the server session; persisted reports remain the historical fallback.

### Partial execution

`Run from here` uses the existing graph interpreter with an explicit starting card, not a second scheduler. `application/start_context.py` restores only compatible, passed, non-redacted ancestor results and per-card global changes into the invocation frame. Reached cards execute afresh through the normal executor registry. `infrastructure/run_checkpoints.py` locates compatible completed evidence after restart; an explicitly selected live context takes precedence. Evidence records the start scope, base fingerprint and reused source run. Controlled-body entry requires its enclosing container; main graphs must reach Finish, function graphs Return.
