# Release Workbench

A local visual workflow builder and parallel test/release runner with a multi-project workflow home page. Configure steps in the browser canvas, YAML, or a terminal starter wizard. Runs stay on your own machine. MIT licensed; no subscriptions or hosted service required.

```bash
python -m pip install https://github.com/codewhen/release-workbench/releases/download/v0.3.0/release_workbench-0.3.0-py3-none-any.whl
release-workbench init
release-workbench serve
```

See [Getting started](docs/getting-started.md), [Configuration](docs/configuration.md), [Execution and CI](docs/execution.md), and [Contributing](CONTRIBUTING.md).

Commands configured in a workflow execute with your user account. Open trusted project configurations only. Remote agents, hosted scheduling and store submission integrations are outside this first version.

Engine and browser checks ran on macOS. Windows command plans are tested; native Windows and Linux execution still require verification on those hosts. See the execution guide for cancellation limitations.
