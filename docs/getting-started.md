# Create your first workflow

Release Workbench runs locally. Python 3.11 or newer is required; Node is required only for contributors rebuilding the frontend. Download a versioned wheel from the repository's GitHub Releases, install it into a virtual environment, then:

```bash
release-workbench init
release-workbench serve
```

`init` asks for a workflow name, starter template and test command. Use `--template blank --name "My release"` to create a blank configuration without prompts. Add `--config path/to/release-workbench.yaml` to each command to select a different file. The file's parent directory is the workspace; commands and report paths resolve from it.

## Ten steps without writing YAML

1. Open the local URL printed by `serve` (default port 3103).
2. Choose **New workflow**, enter its name, and select **Blank checklist**. This creates a draft; the file remains unchanged.
3. Choose **Add first step**, enter the step name and command. The default command is a harmless Python demonstration, not a test of your application.
4. Choose **Add next step** nine times, naming each step and entering its command. Connections automatically make each new step depend on the preceding step.
5. Choose **Validate & review**. Fix missing commands, unknown dependencies, invalid fields or cycles; inspect the YAML diff.
6. Choose **Save** to write configuration, or **Save and run** to write configuration and execute it.
7. In **Run**, choose a node to inspect its current stage, live output and saved evidence. A saved workflow does not imply that tests have passed.

Command execution defaults to a program plus arguments. Quotes group arguments; pipes, `&&` and redirects are not evaluated. Choose an explicit bash/sh/PowerShell/cmd shell for scripts that need those operators. Only run workflow files from trusted repositories.

## Branches, gates and advanced settings

Connect one node to two others to create parallel branches. Connect both branches to a later node to form a join. Use the plus button on a connection to insert a step. Deleting a step reconnects its dependents to its prerequisites, after an in-page confirmation. The dependency settings also provide checkboxes, so graph manipulation is never required.

Select **Add manual gate** when a person must inspect evidence or prepare devices. Record a meaningful note in Run view; manual gates do not execute commands. After recording, waiting dependents can continue automatically. A disabled prerequisite blocks downstream work; it never becomes a pass.

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
