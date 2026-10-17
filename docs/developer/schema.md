# Schema v3 reference

The installed `release_workbench/schema.json` is the public JSON Schema. A running server exposes it at `/api/schema`. The browser, YAML editor and CLI validate the same document. Versions 1 and 2 produce an unsupported-version error without modification.

```yaml
version: 3
name: A typed flowchart
concurrency: 4
inputs:
  message: {type: string, default: Hello}
globals:
  attempts: {type: number, initial: 0}
functions: {}
graphs:
  main:
    cards:
      - {id: start, kind: start, name: Start}
      - id: compute
        kind: python
        name: Compose a greeting
        config:
          code: |
            print("Composing")
            return {"message": inputs["message"]}
          returns: object
        inputs:
          message: {$ref: 'input:message'}
      - id: finish
        kind: finish
        name: Finish
        config:
          returns: object
          value: {$ref: 'card:compute'}
    edges:
      - {id: start-compute, kind: flow, source: start, target: compute, source_port: next, target_port: entry}
      - {id: compute-finish, kind: flow, source: compute, target: finish, source_port: next, target_port: entry}
layout:
  main:
    positions:
      start: {x: 0, y: 0}
      compute: {x: 340, y: 0}
      finish: {x: 680, y: 0}
    areas: []
```

## Top-level fields

| Field | Meaning |
|---|---|
| version | Must be integer 3. |
| name | Human-readable workflow name. |
| concurrency | Shared operation slots, 1–64; default 4. |
| inputs | Named type declarations, optional default/description; missing default means required. |
| globals | Named type declarations and required initial values, reset per new run. |
| functions | Function IDs mapping to name, graph ID, inputs and returns. Each function has its own graph. |
| graphs | Main and function graphs; cards and edges. |
| layout | Optional positions and area metadata by graph. Never affects execution or the execution fingerprint. |
| environment | Explicit string environment overrides. Prefer environment references over stored credentials. |
| secrets | Environment names whose literal values must be masked in logs/reports. |
| source_paths | Relative source glob patterns included in run fingerprints. Add application source here when commands depend on it. |
| workspace | Execution root relative to this YAML directory; default `.`. Child YAML paths resolve from the parent root, then children resolve their own root. |
| input_detection | Optional `{argv: [...], timeout: 30}` command for the explicit Auto-detect inputs button; timeout maximum 120 seconds. |
| report_paths | Workspace-relative report globs; traversal and symlink escapes rejected. |

Card IDs are stable and unique within a graph. A card has kind, name, config, inputs, optional owner and settings. Connections have stable unique IDs, source/target, source_port/target_port, kind flow/value and optional value path. Main ordinary connections are acyclic; only a legal owned body → next_iteration loop-back closes a structured loop.

## Runtime bindings, discovery and report contracts

`{$ref: "runtime:python"}` resolves to the engine interpreter. Program argument arrays accept literal strings or references resolving to strings; values are not interpolated into shell source. Workflow inputs are typed declarations, not application-specific IP/device validation.

The [input guide](../user/inputs.md) documents the discovery JSON protocol and candidate selection, including omitted fields, ambiguity, defaults and CLI/child behavior. [Settings](../user/settings.md) documents report attachment bounds, log truncation flags and child evidence. These are reusable contracts: application detectors and release-specific validation belong in the consuming project.

## Execution settings

```yaml
settings:
  timeout: 60
  resources: [android-device]
  interactive: false
  exclusive: false
  cwd: .
  environment: {PYTHONUNBUFFERED: '1'}
  expected_seconds: 20
  retry:
    attempts: 3
    delay: 1
    backoff: 2
    errors_contain: [temporarily unavailable]
```

Retry is off by default. Attempts includes the first attempt. With errors_contain, retries occur only when at least one listed literal substring matches the failure. Cancellation and manual decisions never retry automatically. Interactive operations acquire the shared desktop resource. Exclusive operations wait for other operations to finish and block new operation scheduling. Put locks on actual operations, not structural containers that wait on children. A user-provided expected duration is labelled an estimate; structured progress remains measured.

## Preservation and safe saving

Browser edits remain drafts until Save. Validate shows the saved-to-draft diff. Saves validate the v3 document structure, preserve YAML comments where possible, write atomically and require the last revision. External changes produce a reload-required error; they are never silently overwritten. Incomplete execution graphs can be saved as drafts; Validate and Run enforce full execution contracts. Failed validation keeps a revision-matched draft recovery backup. Editing is disabled during active runs. Removing layout areas does not remove or re-scope executable cards.
