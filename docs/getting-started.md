# Create your first workflow

Release Workbench runs locally. Python 3.11 or newer is required; Node is required only for contributors rebuilding the frontend. Download a versioned wheel from the repository's GitHub Releases, install it into a virtual environment, then:

```bash
release-workbench init
release-workbench serve
```

`init` asks for a workflow name, starter template and test command. Use `--template blank --name "My release"` to create a blank configuration without prompts. Add `--config path/to/release-workbench.yaml` to each command to select a different file. The file's parent directory is the workspace; commands and report paths resolve from it.

## Home: multiple workflows and projects

`serve` opens the workflow library first. The initial project is the parent folder of `--config`; that folder must exist, but the YAML file need not exist yet. You can start in an empty project with `release-workbench serve` and create its first checklist from Home.

- **Add project or file** registers an absolute local folder path or an existing YAML file. Folders discover `release-workbench*.yaml` and `release-workbench*.yml` directly within them. Add an individual file for a different filename. Registration validates YAML files and never executes commands.
- **New workflow** selects a registered project, name, YAML filename and blank/test/release starter. It creates a separate file without overwriting any existing configuration. Commands resolve from that file's parent project folder.
- Search names, descriptions, projects or filenames; use the Project filter for one folder. Workflow rows show the current session's run, or the last matching configuration run on disk. A displayed completion is historical evidence, not permission to publish a release.
- **Open workflow** enters its canvas. **Home** returns to the list; unsaved changes require an explicit keep/discard choice. Existing server-side jobs continue while Home is displayed, and opening the same workflow again keeps its current engine and evidence.

Project registration is persisted in `library.json` inside the initial project's configured output directory (default `.workbench`). It contains local absolute paths; do not commit or publish it. The same relative output setting applies in each registered project; logs and reports stay inside that project's output directory. Keep generated outputs ignored by Git.

One workflow runs at a time in a launcher, including paused scheduling. Finish or stop it before executing another workflow. Parallel branches within the chosen workflow continue to use its configured concurrency and resource locks. Separate launcher processes do not coordinate hardware locks; use one launcher for a shared desktop/phone.

Opening an uncached workflow creates a fresh run and never silently inherits old passes. Use `serve --config PATH --resume RUN_ID` for a matching saved run; it opens that workflow directly. Source/configuration changes still require fresh verification. Creating a YAML file changes a Git checkout, so an already-fingerprinted run may need **New run** before further execution.

## Ten steps without writing YAML

1. Open the local URL printed by `serve` (default port 3103).
2. On Home choose **New workflow**, enter its name and filename, select the project and **Blank checklist**, then **Create and open**. This creates a separate empty YAML file; no commands run. Step edits remain unsaved until Save.
3. Choose **Add first step**, enter the step name and command. The default command is a harmless Python demonstration, not a test of your application.
4. Choose **Add next step** nine times, naming each step and entering its command. Connections automatically make each new step depend on the preceding step.
5. Choose **Validate & review**. Fix missing commands, unknown dependencies, invalid fields or cycles; inspect the YAML diff.
6. Choose **Save** to write configuration, or **Save and run** to write configuration and execute it.
7. In **Run**, choose a node to inspect its current stage, live output and saved evidence. A saved workflow does not imply that tests have passed.

Command execution defaults to a program plus arguments. Quotes group arguments; pipes, `&&` and redirects are not evaluated. Choose an explicit bash/sh/PowerShell/cmd shell for scripts that need those operators. Only run workflow files from trusted repositories.

## Branches, gates and advanced settings

Connect one node to two others to create parallel branches. Connect both branches to a later node to form a join. Use the plus button on a connection to insert a step. Deleting a step reconnects its dependents to its prerequisites, after an in-page confirmation. The dependency settings also provide checkboxes, so graph manipulation is never required.

Select **Add manual gate** when a person must inspect evidence or prepare devices. When a gate becomes ready, the browser opens an **Action required** dialog with its instructions. Record a meaningful evidence note to complete it; manual gates do not execute commands. **Not now** closes the dialog without completing the gate. A **Respond** reminder stays visible in Run view and on the Home page until the gate is completed. After recording, waiting dependents can continue automatically. A disabled prerequisite blocks downstream work; it never becomes a pass.

Expand **Advanced settings** for platform commands, resources, timeouts, input requirements, progress parsing and reports. Workflow settings contains input definitions, environment references, profiles and detection hooks. Complex fields use labelled JSON controls; the YAML tab is the complete configuration view, not a second configuration store.

**List** provides equivalent selection and step editing on narrow screens. Below 700px it is selected automatically. Choosing a step opens and focuses its settings; **Back to workflow steps** returns to the list. Workflow settings also opens in view on mobile. **Undo/Redo** affects unsaved configuration only. Execution evidence is never undone.

## Saving and resuming

Switching away from YAML validates and applies pending edits; invalid YAML stays in the editor and is never discarded. New/delete dialogs trap keyboard focus, close with Escape and return focus to their triggering control.

Save checks that the file has not changed externally, validates all settings and writes atomically. A conflict asks you to reload rather than overwriting someone else's edit. Configuration edits are disabled while execution or paused scheduling is active.

The desktop work area fits the viewport, with independently scrollable settings and larger canvas controls. In Run, **View running step** focuses the active job; **Inputs and run evidence** expands to reveal detection and report links. Manual gates show evidence status instead of execution percentages.

Reloading the page leaves execution on the server running. Stop the server only after stopping jobs and waiting for cleanup. To resume a matching saved run:

```bash
release-workbench serve --resume RUN_ID
release-workbench run --resume RUN_ID --non-interactive
```

Source, platform and workflow fingerprints must match. Changed source/configuration starts a new run; old HTML/JSON reports remain available. Non-Git projects should declare `source_paths` to fingerprint application source. Git projects fingerprint HEAD and changed/untracked files, excluding the configured evidence output directory.

## Required inputs before running

When you choose Run all, Run selected or Save and run, the browser checks the inputs needed by that selection and its prerequisites. Missing or invalid values open an **Inputs required** dialog before commands start. Fill the labelled fields, or use **Auto-detect inputs** when the workflow defines a detection command, then choose **Save inputs and start**. Dismissing the dialog leaves an **Enter required inputs** reminder. Saving configuration alone never executes commands.

Inputs produced by a selected prerequisite through declared JSON outputs are collected during execution instead of being requested beforehand. If a step later needs input, its **Review** action opens the fields or the step details. Changing inputs after attempts or manual evidence have been recorded requires an explicitly labelled new run; previous evidence remains in its historical run.

Commands should consume configured workflow inputs or environment references. An arbitrary command-line stdin prompt does not become a browser form automatically; model human preparation as a manual gate and values as workflow inputs.

## Arrange your workspace

Details appear on the left of the workflow. Drag the divider to change its width, or focus the divider and press Left/Right (Shift for larger changes); Home and End select the allowed minimum and maximum. **Hide details** gives the workflow the full width; **Show details** restores the panel. The browser remembers your preference. Selecting a step or opening Workflow settings reveals the panel. Both panes scroll independently. On a phone the workflow and details stack vertically, and the horizontal divider is hidden.
