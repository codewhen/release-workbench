# Workflow Workbench

A local visual workflow builder and parallel test/release runner with a multi-project workflow home page. Configure steps in the browser canvas, YAML, or a terminal starter wizard. Runs stay on your own machine. MIT licensed; no subscriptions or hosted service required.

```bash
python -m pip install https://github.com/codewhen/release-workbench/releases/download/v0.14.1/release_workbench-0.14.1-py3-none-any.whl
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

Home has local folders that can contain workflows from multiple registered projects. Choose **New folder**, pick its parent, then name it. Right-click an entry and choose **Move to folder…** to file it; **All workflows** always shows the full catalog. Folder breadcrumbs and the sidebar navigate subfolders. Right-click a folder to rename it, move it to another parent, create a subfolder or remove it and return its entries to **Unfiled**. Removing a folder opens an inline confirmation. Right-click a workflow entry to open it, move it, return it to Unfiled or copy its YAML path. Focus a folder or entry and press **Shift+F10** (or the Context Menu key) for the same actions; arrow keys navigate the menu and Escape closes it. New workflows created while browsing a folder are filed there automatically.

This organization is stored atomically in the launcher’s local `library.json`, alongside project registration. It does not rename or move YAML files, modify workflow configuration or run commands. Existing libraries load with all entries Unfiled.

While viewing Overall, panning the canvas or scrolling the list opens the currently running card and pauses automatic navigation, including after that card finishes. Returning to **Overall run** resumes list following and canvas centering/zoom. In parallel runs, inspection chooses the followed card if still running, otherwise another active card.

### Stopping jobs

**Stop all** or **Stop selected job** requests cancellation and gives processes up to 30 seconds for device restoration and cleanup. The running panel shows a countdown. While stopping, the button changes to **Force stop**; this terminates remaining processes without waiting for graceful cleanup. If the grace period expires, termination happens automatically. Logs and partial evidence remain saved, and cancelled work is distinct from failed work.

Process supervision remains active while output pipes drain, including when a shell exits before a child process. On POSIX, cancellation tracks descendants and the managed command’s isolated process group; it does not target other independent workflow jobs. Windows uses targeted process-tree termination and retained descendant handles. Windows native verification remains outstanding.

### Small screens and saved reports

On phones, expand **Folders** to browse Home; press and hold a folder or workflow entry for organization actions. The workflow toolbar keeps its primary actions visible and puts secondary actions under **More controls**. List, YAML and the details panel remain available with independent scrolling. Blank workflows offer **Start editing**.

HTML reports include **Jump to a step**, written outcome counts, attempts and artifact checksums. They work without JavaScript and preserve project context when opened through the server. Historical report files remain unchanged; new runs use the updated report layout. See [the interface review](docs/ui-review.md) for coverage and verification limits.
