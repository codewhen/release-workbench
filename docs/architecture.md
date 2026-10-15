# Architecture and contribution guide

The redesign contains one v3 contract and one graph interpreter. No legacy engine, schema adapter or implicit conversion remains on this preview branch. Previous versions stay available through their release artifacts.

```text
src/release_workbench/
  domain/             # values, immutable graph models, CardResult, CardSpec registry
  application/        # compiler, interpreter, invocation frames, executors, coordinator, ports
  infrastructure/     # subprocess/HTTP/file adapters, YAML, evidence, library persistence
  interfaces/         # CLI and localhost HTTP handlers
  schema.json         # published v3 contract
  static/             # compiled offline frontend, bundled in wheel
frontend/src/
  shared/             # generated workflow types, API client and run contracts
  editor/             # immutable editor commands, history, canvas/layout rendering
  cards/              # typed ports, registry-driven fields, bindings and connections
  components/         # accessible local primitives
  run/                # live evidence views
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
