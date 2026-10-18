# General-purpose integration and documentation audit

Reviewed the complete tracked/untracked source inventory, rather than only staged changes: Python domain/application/infrastructure/interfaces, frontend editor/Home/run/binding modules, schema and card registries, CLI/npm launcher, examples, tests, packaging and CI. Generated dependencies and build assets were assessed through their sources and builds, not treated as hand-written source to review. This is a general-purpose boundary/documentation review, not a security certification or native Windows acceptance.

## Findings and changes

- No consumer-specific device/IP/build behavior was found in the runtime or frontend. Inputs, discovery commands, runtime Python, workspace resolution, report attachments and nested workflow evidence are reusable contracts.
- The distribution verifier mentions a consuming application solely to reject accidental private workflow packaging. A historical review also mentions that scope. Neither is a runtime integration. Real consuming-project workflows remain outside this repository.
- Added a dedicated Run inputs/discovery guide, a synthetic read-only Python detector, a runnable YAML and a contributor integration-boundary page. Described defaults, required values, semantic validation, ambiguity, manual overrides, stdout protocol, timeout, environment, CLI/child behavior and trust limits.
- Corrected stale Program output-size guidance and propagated workspace semantics through CLI, storage, function, file and external-workflow references. Documented per-stream capture flags, runtime Python argument bindings and child evidence.
- Extended coverage to discovery schema subfields and input-discovery/streaming-output/nested-evidence feature groups. The example checker verifies the detector's actual typed candidates and the workflow's actual returned object.
- Documented relevant limitations: typed strings do not validate IP addresses; discovery is trusted local code; interpreter selection does not install project dependencies; one server permits one top-level run; run coordinators do not provide locks across separate processes; Windows remains unverified.

## Verification

- Documentation checker: 72 guide pages, all 25 executable cards, three layout tools, field/mode/settings inventories, examples, screenshots, links and heading anchors passed.
- All 40 downloadable workflows executed in disposable directories, including the real generic detector and its expected result.
- All 110 backend regression tests passed, including registry/schema/executor agreement, inheritance/layer checks, workspace/discovery/large-log/report/child evidence contracts.
- Ruff checks and formatting passed for modified Python documentation tools and the new detector.
- Local `/docs/` and GitHub Pages `/release-workbench/` builds passed.
- Browser acceptance passed for guide/download routes, search/empty results, copy, image keyboard access, responsive navigation, unknown/traversal paths and application help links preserving synthetic drafts/active runs.

No application runtime behavior, workflow schema or existing user workflows were changed by this documentation audit. No package was published.
