# Preview acceptance

Version **0.18.0a1**, schema v3. Verified locally on macOS on 15 October 2026. This is a breaking preview and does not replace the stable installation.

| Check | Result |
|---|---|
| Python unittest | 61 passed |
| Ruff lint and format | Passed |
| mypy source checks | Passed, no untyped definitions |
| Strict TypeScript with unused-code checks | Passed |
| Vitest immutable editor commands | 10 passed |
| Playwright Chromium | 7 passed |
| Browser-only ten-step creation, wiring, save/reload/run | Passed |
| Function navigation, manual True/False across runs, Stop | Passed |
| Context actions, undo/redo, layout collapse, mobile List/dropdowns | Passed |
| Desktop/mobile visual review and Impeccable detector | Completed |
| Wheel and source archive build | Passed |
| Clean wheel install outside checkout, no Node/PYTHONPATH | Python/file, While, Parallel and recovery passed |
| Existing installation and application workflows | Left separate and unchanged |
| Native Windows | Unverified; manual acceptance workflow supplied |

Backend coverage includes zero/count/nested loops, changing Boolean functions, Break/Continue and Finally, limits/unlimited cancellation, isolated function inputs, global resets and parallel conflicts through calls, named Join results, shared external-workspace concurrency and isolated globals, child-source fingerprints, separate Python logs/returns, scripts and programs, file/HTTP failures/timeouts/cancellation, manual evidence, retry filtering, explicit resume and process cleanup. Reports are escaped, report paths restricted, and saves require a local token/revision.

## Practical limits

Commands are trusted local configuration, not sandboxed untrusted code. Bash requires a local Bash installation. POSIX process groups and tracked detached descendants are cleaned up; a process that deliberately escapes and reparents before observation cannot be guaranteed. Environment/service state and undeclared source files are not a reproducibility guarantee: declare source_paths and avoid including generated outputs in source globs. Redacted outputs block resume rather than being reused as real values.

For-each, Switch, Repeat-until, recursion, arbitrary Go To, remote agents, schedules, database connectors and multiplayer editing are outside this initial catalog. Use functions and Python where appropriate. Native Windows support must remain unverified until its acceptance suite actually passes.
