# Run inputs and automatic discovery

Workflow inputs collect the information an automation needs before it starts: a server address, device identifier, output folder, worker count or a dry-run choice. The same mechanism works for tests, deployments, data processing and local maintenance. Workbench does not assign special meaning to an input called `host`, `serial` or `pid`.

## Declare inputs before running

1. Open your workflow and choose **Edit → Workflow settings**.
2. In **Workflow inputs**, add a name, choose its type and choose whether it is **Required without default**.
3. For optional inputs, enter a **Default value** of the declared type. Save the settings and workflow.
4. Choose **Run → Run all**. The **Run inputs** dialog lets you review and edit the supplied values before **Run workflow** starts execution.

```yaml
inputs:
  target:
    type: string
    description: Project directory to inspect
    default: .
  workers:
    type: number
    default: 1
  profile:
    type: string
    default: quick
  dry_run:
    type: boolean
    default: true
```

Omit `default` to require a value. The browser uses text and number fields, a True/False selector, and JSON fields for structured types. Descriptions explain the fields. Input declarations validate types, not application rules: an empty string is still a string, a number is not necessarily a valid process ID, and a string is not automatically checked as an IP address. Put semantic checks in your own validation card or project script before side effects.

Do not put passwords in input defaults or shared YAML. Prefer environment references and declared secret names; see [settings and secrets](settings.md).

## Pass the value to a card

Declaring an input makes it available; it does not inject it into every operation. Select a card, add a **Named inputs** entry and choose the workflow input from its value-source picker. For a Python card receiving `workers`, read `inputs["workers"]`.

```yaml
# On the receiving card, separate from the workflow-level declaration:
inputs:
  workers: {$ref: 'input:workers'}
```

Program/Bash/Script receive named inputs on stdin as `{"inputs":{"workers":1}}`. Their command-line arguments are separate. External workspace cards pass an explicit **Workflow inputs** object. Child workflows do not inherit parent inputs or invoke discovery automatically.

## Add Auto-detect inputs

Discovery is an optional command you configure for the workflow. It runs on the machine hosting Workbench, using that workflow's resolved workspace and environment. It can call Python, a system tool or a project-owned helper. There is no built-in device scanner, network scanner or application-specific detector.

1. Place your read-only detector script in the project.
2. Open **Workflow settings → Input discovery and report files**.
3. Set **Input discovery command** to an argument array, as below. Each array item is one literal argument; shell pipes, substitutions and glob expansion do not run.
4. Set the timeout if needed, save, then open **Run inputs → Auto-detect inputs**.
5. Review candidates and warnings, choose ambiguous values, and choose **Run workflow** when ready.

```yaml
input_detection:
  argv:
    - {$ref: 'runtime:python'}
    - detect_inputs.py
  timeout: 30
```

`runtime:python` is the interpreter running Workbench, including an npm launcher's managed Python environment. It does not install your project's Python dependencies. Use an explicit project interpreter when those dependencies require a separate environment. The default discovery timeout is 30 seconds; the maximum is 120 seconds.

![Run inputs and detection using synthetic example values](../assets/screenshots/input-discovery.png)

## Detector output contract

Print exactly one JSON object to stdout and exit with code zero. Send diagnostic logging to stderr. Every declared input you want to detect maps to an array of candidate objects:

```json
{
  "target": [{"value": ".", "label": "Current project", "automatic": true}],
  "workers": [{"value": 4, "label": "Four workers", "automatic": true}],
  "profile": [
    {"value": "quick", "label": "Quick checks", "automatic": false},
    {"value": "full", "label": "Full checks", "automatic": false}
  ],
  "warnings": ["Choose the profile you want to run."]
}
```

| Field | Contract |
|---|---|
| Input-name key | Must correspond to a declared workflow input to be used. Undeclared keys are ignored. Missing keys produce no candidates. |
| Candidate `value` | Required; must match the input's declared type. Decimal digit strings can be converted to numbers for numeric declarations. |
| Candidate `label` | Optional display text; defaults to the value rendered as text. |
| Candidate `automatic` | Optional Boolean; defaults to `true`. Explicit `false` requires operator selection. |
| `warnings` | Optional array of strings; displayed in the dialog. Defaults to an empty array. |

Exactly one candidate with automatic selection enabled replaces the current input value. Two or more candidates never auto-select, even when one is marked automatic. No candidate leaves the existing value unchanged. A subsequent detection can replace previously entered values; review the dialog before starting. You can always edit fields manually.

Detection is available only through its explicit button, is disabled while a workflow is executing, and is not a manual approval. A command failure, timeout, invalid JSON, wrong candidate type or truncated output displays an error and does not start the workflow. Keep both discovery streams small: truncated discovery output is rejected. The command is trusted local code with your permissions; “read-only” is a requirement for your detector, not an enforced sandbox.

## Download and try the complete example

Download [input-discovery.yaml](../examples/input-discovery.yaml) and [detect_inputs.py](../examples/detect_inputs.py) into the same disposable project folder. Register that folder on Home and open **Input discovery example**.

The detector reads the CPU count and offers a bounded worker count plus two profile choices. It creates no files, scans no network and starts no tests. Click **Auto-detect inputs**, choose a profile, then run. **Review selected inputs** returns the chosen object; Finish returns that same object. This demonstrates the generic contract independently of any application.

To run without a browser:

```bash
workbench run --non-interactive --config input-discovery.yaml --input target=. --input workers=2 --input profile=quick --input dry_run=true
```

CLI runs use supplied/default inputs and do not run discovery. Child calls likewise supply values explicitly; use a preceding operation if the parent needs to compute them. Discovery does not add a dependency card or change graph execution order.

## Common problems

| Symptom | What to check |
|---|---|
| No Auto-detect inputs button | Configure `input_detection`, save, and reopen Run inputs. |
| No candidates for a field | Match its declared name exactly and return an array, even for one candidate. |
| Wrong type error | Use JSON `true`, a number or an object as appropriate, rather than quoted approximations. |
| Multiple devices or addresses | Return all plausible candidates and labels; let the operator choose. Do not silently select the first. |
| Command cannot import a module | The Workbench Python environment may differ from the project's environment. |
| Required address is blank | Required means a supplied typed value; add explicit nonempty/address validation to your workflow. |
| Discovery used in CI | Supply `--input` values or compute them in a normal card. The button is an interactive setup aid. |

Continue with [connections and values](values.md), [External workspace](cards/workspace.md), and [report files and resource settings](settings.md).
