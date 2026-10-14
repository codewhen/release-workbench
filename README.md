# Workflow Workbench

A local visual workflow builder and parallel test/release runner with a multi-project workflow home page. Configure steps in the browser canvas, YAML, or a terminal starter wizard. Runs stay on your own machine. MIT licensed; no subscriptions or hosted service required.

```bash
python -m pip install https://github.com/codewhen/release-workbench/releases/download/v0.11.0/release_workbench-0.11.0-py3-none-any.whl
release-workbench init
release-workbench serve
```

See [Getting started](docs/getting-started.md), [Configuration](docs/configuration.md), [Execution and CI](docs/execution.md), and [Contributing](CONTRIBUTING.md).

Commands configured in a workflow execute with your user account. Open trusted project configurations only. Remote agents, hosted scheduling and store submission integrations are outside this first version.

Engine and browser checks ran on macOS. Windows command plans are tested; native Windows and Linux execution still require verification on those hosts. See the execution guide for cancellation limitations.

Use it for data pipelines, backups, project checks and release workflows. See [general workflows and conditional branching](docs/general-workflows.md). The `workflow-workbench` CLI alias uses the same engine and schema as `release-workbench`.

Right-click the canvas to add visually distinct cards. Use Run tests, Run script, value, calculation and file cards to build automation through forms. See [no-code automation](docs/no-code-automation.md).

### Following a run

Workflows open in Run view without starting commands. Run all opens the left-side Overall run panel, showing selected-work progress, parallel jobs, live output and work needing attention. Canvas and List follow the current running card. Selecting a card, panning or scrolling switches to inspection; choose **Overall run · follow active work** to return and resume following. Passed cards are green, failures red and skipped cards grey. A moving green border marks running work; reduced-motion preferences disable its animation.

In parallel runs the camera stays on one active branch until that job finishes; all active branches remain visible in the overview. Progress counts finished work, including failures and skipped paths; it never implies full release approval.

### Organizing workflow entry points

Home has local folders that can contain workflows from multiple registered projects. Choose **New folder**, pick its parent, then name it. Use each entry’s **Move to folder** control to file it; **All workflows** always shows the full catalog. Folder breadcrumbs and the sidebar navigate subfolders. **Manage folder** renames a folder, including its descendants, or removes it and returns entries to **Unfiled**. New workflows created while browsing a folder are filed there automatically.

This organization is stored atomically in the launcher’s local `library.json`, alongside project registration. It does not rename or move YAML files, modify workflow configuration or run commands. Existing libraries load with all entries Unfiled.

While viewing Overall, panning the canvas or scrolling the list opens the currently running card and pauses automatic navigation, including after that card finishes. Returning to **Overall run** resumes list following and canvas centering/zoom. In parallel runs, inspection chooses the followed card if still running, otherwise another active card.
