# Build task automation without writing code

Workflow Workbench is for local task automation and test workflows. It does not replace a programming language or generate applications. Use built-in cards and their forms for common actions; call an existing script when a task needs custom logic.

## Add and connect cards

Right-click empty canvas space (or a card) to open **Add a card**. Choose a type; the new card appears at that location without connections. The toolbar's **Add card** opens the same picker, including in List view and on phones. Escape closes the picker; arrow keys, Home and End move through choices.

Commands use rectangular cards with a terminal icon. If uses a diamond with True on the right and False below. Manual checks use rounded gate cards. Reusable workflows use a double outline. Built-in actions have a labelled header and an action-specific icon. Outcome text and selection remain separate from the type styling.

Drag—or click—an output and then an input to connect cards. One output may feed multiple cards for parallel work. Select a connection and use Disconnect or Insert card. Add next remains a connected shortcut. Save never starts work; choose Run explicitly.

## Available cards

| Card | Configure in its form | Result |
| --- | --- | --- |
| Run tests | Runner, target/test folder, project folder | Exit code and live test output |
| Run script | Existing file, Python/Bash/PowerShell, separate arguments | Exit code; optional text/JSON capture |
| Set values | Named text, numbers and Boolean flags | Named values in returned JSON |
| Calculate | First value, operation, second value | Number under `value` |
| Check file | Project-relative file path | Boolean under `exists` |
| Read JSON | Project-relative JSON file | Parsed JSON data |
| Write file | File path, text/JSON content, overwrite and folder options | Path, byte count, written flag and file hash evidence |
| If condition | Choose an earlier value, operator and comparison value | True or False branch |
| Manual check | Instructions and operator evidence | Recorded evidence |
| Run workflow | Another YAML workflow in this project root | Child execution and reports |
| Command | Program/arguments or an explicit shell | Custom automation escape hatch |

## Example: run tests and record success

1. Create a blank workflow from Home.
2. Right-click and add **Run tests**. Choose the runner and test folder.
3. Add **If condition**, then connect the test card's output to its input.
4. In **Choose a result**, select the test card's exit code. Choose Equals, Number, and 0.
5. Add **Write file** and connect True to its input. Enter an output filename and a message such as "Tests passed".
6. Add a Manual check to False if you want an operator to review a different normal result. Unexpected test failures still fail the test card and block dependents; they never masquerade as a successful False decision.
7. Save and run. Inspect live output, returned values, decision evidence and file hashes.

The test runner must already be installed. Supported presets are Python unittest, Python pytest, Go, Flutter, npm and the Gradle wrapper. Python unittest requires actual discovered tests and fails if there are none. Other tools use their normal success/failure exit codes. Native Windows execution remains unverified; reviewed Windows command construction is not a Windows test result.

To run an existing integration runner without writing a command, choose Run script, select Python, enter its project-relative file path and add each argument as a separate row. Arguments are passed separately rather than evaluated as shell expressions. Interpreter/tool installation is still necessary; the workbench adds no paid services.

## Use values from previous cards

Set values creates fields through forms; no JSON or script source is required. Calculate and Write file let you choose **A value I enter** or **An earlier card or input**. The picker shows ancestor cards and known values, such as a calculated number or a file-existence flag. Connect prerequisite cards before selecting their values.

If's result picker exposes those same values. For Read JSON, choose all data and enter a simple **JSON field**, such as `ready` or `summary.count`. Fields found in a previous run are also listed. Reference details remain available for advanced configurations, but ordinary automation does not require writing reference expressions.

## Starters

Home → New workflow → Start with includes **No-code data and file automation** and **No-code Python test workflow**. The data demo uses Set values → Calculate → If → Write file → Read JSON. It writes only demonstration data beneath `.workbench/demo/`. The test starter expects your existing Python tests; configure the folder before running.

The same templates work in the CLI:

```bash
workflow-workbench init --template no-code --name "Data automation"
workflow-workbench init --template no-code-tests --name "Project tests" --config workflow-workbench-tests.yaml
```

## Boundaries

- Built-in file actions stay inside the project workspace; symlinks cannot escape it. JSON reads and file content are limited to 1 MiB.
- Write file refuses to replace an existing file unless you enable that option. A completed file write is a real side effect, even if a later card fails; Stop does not undo it.
- Files saved outside the run-output directory need a matching configured report directory for browser file links. Paths and hashes remain in evidence regardless.
- Values keep their types. Booleans differ from numbers and text. Missing bindings, invalid JSON and division by zero fail visibly.
- Built-in actions use the same dependencies, resources, exclusive scheduling, cancellation, timeouts and reports as other cards. Tiny local file/value operations check cancellation before and after work; they are not interruptible halfway through an atomic write.
- Captured script JSON expects one valid JSON value in the final command's combined stdout/stderr; use a separate diagnostic file when necessary.
- Loops, retries, schedulers, API/database connectors and general-purpose expression programming are not included in this version. Use an existing script for specialized work; see the general-workflow roadmap for future additions.
