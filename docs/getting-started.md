# Your first workflow

## Create a project from your terminal

Install Workbench, open a terminal in your project directory, and run:

```bash
workbench create
```

Enter the project name and YAML filename (default `workflow-workbench.yaml`).
The wizard creates a blank Start → Finish workflow **in that directory** and
opens it in the dashboard. It never overwrites a file. `workbench`, `workbench
serve` and `workbench run` all open the dashboard without starting card execution.
Use `workbench run --non-interactive` when you deliberately want terminal execution.

Your default preview library lives in `~/.workbench-preview-v3`. Projects from
multiple folders share that dashboard; `--storage` selects a separate library.
Starter examples are installed separately under `<storage>/projects/starter` and
appear in Home's **Starter** folder. Editing an example does not cause it to be
overwritten on restart.

## Choose a starting point

Home is a library of workflow **entry points**, organized into folders across multiple project directories. Folders organize the library; they do not move files on disk. Use **Add project or file** for a local path. **Open YAML** opens the browser file picker and validates uploaded contents before creating a new file in the selected project. Existing files are never overwritten by import.

Choose **New workflow**, enter its name, project folder and unique YAML filename, then choose a starter. Start with **Python return and file output** to see an operation that logs text, returns a typed object and writes it to disk. Choose **Blank flowchart** to build entirely from cards.

## Build ten steps without YAML

1. Open the workflow and choose **Edit**. Choose List for keyboard editing, or Flowchart for wiring.
2. Click **Add card**, or right-click empty canvas space. The picker groups operations into six categories.
3. Add a **Wait** card. Its duration is editable directly on the canvas and in the details panel. Set it to `0` for this demonstration. Rename it “Step one”.
4. Add nine more Wait cards. Each new card receives focus. The cards are not executable until connected.
5. Connect Start's execution output to Step one's Entry. Connect the ten cards in order, then connect the last to Finish. In List view select the source, choose **Connections → Connect to**, then **Connect execution**. A new connection replaces that execution output's previous connection.
6. Click **Validate & review**. This shows structural errors or the configuration diff without executing anything. A disconnected operation must be connected or deleted before validation succeeds. You can still Save the unfinished draft and return to it later.
7. Click **Save**, then choose Run and **Run all**. The overall panel shows active work. Select a card to inspect its attempts, returned value and logs. **Overall run** follows active execution again.

Right-click a card to duplicate, disconnect or delete it. Right-click a connection to delete it. Undo/redo restore browser draft changes. Start cannot be deleted. Layout areas have no effect on execution. Collapse an area only to hide its selected member cards.

## Return data from Python

Choose the Python starter or add a Python card. In its details panel enter:

```python
print("Checking the supplied name")
return {"greeting": "Hello " + inputs["name"]}
```

Declare a named input `name` in **Named inputs** and choose an entered value or a previous card's result. Set Return type to `object`. Printing creates log output; it does not replace the returned object. The generated wrapper is a function in a child process, so ordinary `return` works.

Connect this card's square Value output to a later card's square field/argument input, or choose a prior card in Named inputs. Execution must still pass through the producer before the consumer. A value wire never runs either card. Validation rejects values that are unavailable on one incoming branch.

## Conditions and functions

If, While and Poll select a function declared to return Boolean. Use **Create function** to open a dedicated flowchart. It starts with Start and a Boolean Return marker. Insert Python, a comparison, a file check or a Manual decision between them; pass that result to Return. Use the breadcrumb **Back to caller** to return to the main workflow.

Return **true/false**, never the strings `"true"`/`"false"`, `0`/`1`, or arbitrary JSON. A function with a dynamic JSON-producing operation is checked again at runtime.

## Run from the terminal

```bash
workflow-workbench init --template while --name "Count to three"
workflow-workbench validate
workflow-workbench run --non-interactive
```

The While starter declares a numeric `count` global, evaluates “Count below three” before each iteration and increments count in its main-canvas Body. Observe four condition evaluations and three body executions in the report.

Commands use the workflow YAML's directory as their workspace. Keep scripts and file operations beneath that project. External workspace calls deliberately select another YAML file and execute relative to its own directory.

## Saving work in progress

Save preserves schema-valid drafts even when cards are disconnected or required execution fields are unfinished. It shows what must be completed before running. Validate checks readiness; Run never executes an invalid flowchart. Connection messages include the graph/card and offer buttons to open the affected card.

If an older editor rejects Save, the updated server backs up that submitted draft. Reload the page only after the error confirms **Draft backed up**. The updated editor restores the backup as an unsaved draft; click Save to keep it. A backup whose base revision no longer matches the saved file is not restored over external changes.

## Create and initialize a global variable

In **Edit** view, open **Workflow settings → Global variables**. Enter a name such as `count`, click **Add global variable**, choose **number**, and set **Initial value** to `0`. Save the workflow. You can also select a Variable card and click **Create / initialize global** to open this form directly.

Use **Get** to read the current value, **Set** to replace it, and **Update** to change it during a run. Initial values are restored when a new run starts; Get/Set/Update do not declare new globals.

Validation diagnostics appear after **Save** or **Validate & review**. Editing clears the displayed diagnostics; check again when ready. Run still enforces execution safety, and an invalid flowchart is not started.


### Add a project folder

On Home, choose **Add project or file → Choose project folder…**. Finder (macOS),
File Explorer's folder dialog (Windows), or an available Zenity/KDialog picker
(Linux) opens on the computer running Workbench. Select a folder, review its
absolute path, then choose **Add to library**. Cancelling keeps the existing path.
You can also paste a folder or workflow YAML path. Native Windows selection has
not yet been verified on Windows. Headless hosts can use the path field.
