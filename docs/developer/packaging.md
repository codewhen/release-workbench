# Package and release Workbench

Build application and documentation assets before making a wheel. End users should need only Python for a wheel installation; the npm wrapper additionally requires Node. Neither installation requires Node to build documentation at runtime.

## Build order

```bash
python -m pip install -e '.[dev]'
npm --prefix frontend ci
npm --prefix docs-site ci
npm --prefix frontend run build
npm --prefix docs-site run check
npm --prefix docs-site run examples
npm --prefix docs-site run build
python -m build
npm --prefix npm/workbench test
cd npm/workbench
npm pack
```

Screenshots are committed source assets; regenerate them when the UI/example changes, inspect them and run docs checks before packing. The Python package includes schema, app static assets, licenses and documentation HTML/search/assets/downloads. The source archive also includes Markdown, screenshots, fixtures and docs build tooling.

The npm prepack step bundles the exact built wheel and records its SHA-256. Keep Python version metadata, wheel filename and npm version aligned. It has no install/postinstall hook; first launch bootstraps an isolated Python environment and forwards CLI arguments without a shell. Scope publication is not performed by packing.

## Clean installation acceptance

Install the wheel into a fresh venv outside the checkout with PYTHONPATH unset. Serve a disposable project and verify `/docs/`, a deep card page, a screenshot, a YAML download and search while external network requests are blocked. Unknown routes and traversal attempts must return 404. End users must not need Node or the source directory for these operations.

Test a local packed npm archive independently: version/help, project wizard, dashboard reuse and a harmless noninteractive workflow. Verify a changed wheel checksum is rejected before setup and a missing Python produces actionable guidance.

A reproducible check is available after installing the wheel into a fresh environment:

```bash
python docs-site/scripts/check_installed.py --python /path/to/clean-venv/bin/python
```

The installed server starts outside the checkout with PYTHONPATH removed and no Node on its PATH. The development browser driver blocks external network requests while exercising search and downloads. Bytecode caches are excluded from both downloads and package artifacts.

## Git tag policy

Create or push a Git tag only when the user explicitly requests it. Building artifacts, updating a version or publishing a package does not authorize a tag. Do not automatically recreate removed historical tags.

## Release checks

Run backend lint/types/tests, frontend unit/type/build/browser checks, examples, coverage, docs browser checks and both base-path builds. Review licenses/notices after dependency changes. Record exact executed platforms and limitations. Native Windows remains unverified until its native acceptance suite passes.

Generate checksums for final artifacts. Keep credentials, browser-sessions.json, real reports and personal project files out of packages and git. Publication, tags, GitHub Pages activation and changing a running user's installation are separate authorized actions. Refresh a local dashboard only while idle, preserve sessions/storage/drafts and do not reload an unsaved user tab.

## Generic distribution boundary

Only generic Starter projects are registered on a fresh installation. Consumer-project YAML, library metadata, credentials, private plugins and real run evidence must never become package inputs. Keep consumer workflows in the consumer repository and register their folders explicitly.

After building the wheel, source archive and npm archive, run:

```bash
python tools/verify_distribution.py dist/*.whl dist/*.tar.gz npm/workbench/*.tgz
```

The CI packaging job runs this check. For an unpublished local consumer pin, distribute the exact wheel and its SHA-256 to that consumer; packing a local npm archive does not publish it.
