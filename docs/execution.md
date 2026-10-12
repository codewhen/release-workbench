# Execution, CI and cancellation

A workflow is a dependency graph. Roots are eligible immediately. A step waits until all prerequisites pass or have recorded manual evidence; failed, cancelled or disabled prerequisites block dependents. Independent branches continue collecting results after a failure. Named resources and the concurrency limit decide which eligible jobs can start together.

Use `resources` when jobs share build trees, hardware, ports or mutable test data. Interactive jobs reserve the local `desktop` lock automatically. This prevents two interactive jobs overlapping, but it does not stop a person using the computer. Actual OS input tests still require an untouched desktop. Use `exclusive:true` for controlled performance measurements so unrelated builds/tests cannot skew results.

## Selection

```bash
release-workbench run --profile background --non-interactive
release-workbench run --step package --non-interactive
release-workbench run --profile nightly --non-interactive
```

Run selected includes unmet ancestors. Rerunning a selected step (`--rerun`) invalidates downstream results and manual attestations. Background selection includes only background command steps whose prerequisites are background-compatible or already completed; excluded manual/device work stays pending. Named profiles include their dependencies and do not certify the complete release.

CLI never automatically attests manual gates, including without `--non-interactive`; use the browser to record evidence. The flag documents CI intent. Exit codes are `0` selected work passed, `1` failed, `2` invalid or blocked, and `130` cancelled.

Pass typed values with `--input serial=USB_EXAMPLE`. JSON booleans/numbers are accepted, otherwise values are strings. Upload the `.workbench/<run>/` directory as CI evidence; review it for private information before making it public. No hosted runner subscription is required.

## Stop and pause

**Pause scheduling** allows running jobs to finish and keeps queued work waiting. **Resume scheduling** continues that queue. **Stop selected job** interrupts one running job or cancels a queued job; independent branches continue. **Stop all** also stops queued work from starting.

On POSIX systems the supervisor discovers descendants (including separate sessions), sends SIGINT and allows up to 30 seconds for cleanup, then kills remaining processes. Device runners must implement their own finally handlers to restore settings. Windows currently uses forced `taskkill /T /F`; check device/network settings afterward. Native Windows behavior remains unverified until tested on a Windows host.

Cancelled jobs retain their logs and partial attempts. Timeout is a failure, not a cancellation. Stopping does not roll back completed installs or other command side effects. Arbitrary configured commands run with the operator's account, not inside an OS sandbox.

## Reports and history

Run summaries contain source/workflow fingerprints, selected IDs, statuses, attempts, commands, inputs/outputs, durations and report hashes. HTML reports can be opened directly after the server stops. Browser-served HTML evidence is sandboxed with scripts disabled. File access is limited to the output directory and configured workspace report locations.

Changing source or workflow creates a new run. Resume requires matching fingerprints and platform. Prior running/queued steps become cancelled on restart; inspect lingering processes before retrying. Schema version 1 runs are the supported format; application-specific legacy reports remain historical evidence rather than inherited passes.

## Verification matrix for 0.1.0

| Environment | Evidence |
|---|---|
| macOS / Python 3.14 | Actual engine/API/process tests, wheel install and browser acceptance checks |
| Windows | Native command selection and taskkill invocation tested as plans; native runtime not executed |
| Linux | POSIX implementation present; native runtime not executed |

Run the contributor test commands on each target host before relying on its release evidence. This first release does not claim native Windows or Linux certification.
