# HTTP request

Call an HTTP(S) endpoint with optional JSON body and headers, returning response information.

## Before you start

Work in **Edit** view in a saved project folder. Start with the downloadable example in its own directory; it includes the surrounding wiring needed for this card. See [connections and values](../values.md) if ports or result sources are unfamiliar.

## Behavior and ports

Choose **Method** from GET/POST/PUT/PATCH/DELETE/HEAD and configure **URL**. Advanced **Headers** is an object; **JSON body** is a JSON value or null. Use declared inputs/value references for dynamic URLs and environment references for credentials. Do not commit literal API keys.

The result contains `status`, `headers`, `text`, and `json` (null when the body is not valid JSON). Non-2xx responses fail. Cross-origin redirects are rejected; request the intended destination explicitly. The operation runs in a cancellable child process and respects timeout/output limits. No hosted service is required for the local example.

**Execution outputs:** `next`. **Catalog value contract:** `object`; configuration, declared variables/functions and runtime validation refine the actual type as described above. Inspect the typed return value after running.

## Fields and defaults

| UI field | YAML key | Default | Rules and visibility |
|---|---|---|---|
| Method | `method` | `"GET"` | Options: `GET`, `POST`, `PUT`, `PATCH`, `DELETE`, `HEAD` |
| URL | `url` | `""` | Required |
| Headers | `headers` | `{}` | Advanced |
| JSON body | `body` | `null` | Advanced |

This operation supports resource locks, interactive/exclusive scheduling and a configured timeout. Retry is supported but off by default. Use it only when repeating the operation is safe. See [common execution settings](../settings.md) for field-by-field configuration, cancellation and evidence.

## Configure it in the browser

1. Download [http_fixture.py](../../examples/http_fixture.py) and run `python3 http_fixture.py` in another terminal; it listens only on 127.0.0.1:8765.
2. Open the HTTP example. Its workflow input `url` defaults to `http://127.0.0.1:8765/health`.
3. Select HTTP request: Method GET; URL uses that input. Leave Headers `{}` and JSON body null.
4. Save and run. Inspect status `200` and json `{"ok":true,"service":"documentation"}`.
5. Stop the fixture with Ctrl+C after the walkthrough. The [HTTP and file processing example](../../examples/http-io.yaml) saves and reads that JSON.

## Configured example

![HTTP request configured in Workbench with its details panel and flowchart](../../assets/screenshots/card-http.png)

*Actual Workbench screenshot from a disposable documentation project. Select the image to enlarge it in the documentation site.*

[Download the complete runnable workflow](../../examples/http.yaml). Place it in a dedicated folder, add any companion files described above, then use **Home → Add project or file** to open it. It is configured for the current schema; it is not a screenshot-only mockup.

This is the selected card's YAML configuration. The download also includes its Start, completion markers, graph declarations and execution connections:

```yaml
id: operation
kind: http
name: Operation
config:
  method: GET
  url:
    $ref: input:url
  headers: {}
  body:
```

Bindings such as `$ref` in this YAML are represented by named value choices in the browser. They supply values and never start execution. Save your own edits, validate, and compare **Run** evidence with the behavior described above.

## Common mistakes and recovery

Connection refused usually means the local fixture is not running or uses another port. A valid HTTP 404 fails the card. Do not place extra log text inside a JSON request body. Declare secret environment names before supplying sensitive headers.

If validation reports an issue, click that issue to locate the card on its flowchart. Correct its fields, scope or connections, then Validate again. Check the selected execution's log, attempts and typed result for runtime errors before deliberately rerunning side effects.

## Next example

Use Try/Catch to handle a service error, or retry a safe/idempotent request for a transient failure.

Continue with [the control-flow tutorials](../tutorials/completion.md), [running and evidence](../running.md), or the [card catalog](index.md).
