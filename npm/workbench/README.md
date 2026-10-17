# Workbench npm launcher

Optional npm/npx entry point for the MIT-licensed Python Workbench engine.
**This package is prepared locally; it has not been published to npm.**
Python 3.11+ and Node 18+ are required. Windows acceptance remains unverified.

## Local package

From the repository root, after building the bundled frontend:

```bash
python -m build --wheel
npm --prefix npm/workbench test
cd npm/workbench
npm pack
npm install -g ./codewhen-workbench-0.18.0-preview.5.tgz
workbench
workbench create
```

Or execute the local archive without a global install:

```bash
npx --package ./codewhen-workbench-0.18.0-preview.5.tgz workbench serve
```

After publication under the configured scope, these will be available:

```bash
npx @codewhen/workbench
npm install -g @codewhen/workbench
workbench create
```

First launch verifies the bundled wheel SHA-256, creates an isolated venv under
`~/.cache/codewhen-workbench/<wheel checksum>/`, and installs that wheel and its
Python dependencies using pip. Dependencies need network access on first setup;
subsequent launches reuse the venv. No global Python installation is changed.
The launcher has no install/postinstall script. `WORKBENCH_PYTHON` can point to a
specific Python executable. npm update installs a new bundled wheel with a new
cache identity. Do not delete a runtime while it is serving a dashboard.

The checksum detects accidental payload changes; package/release provenance must
still be trusted. Runtime caches are separate from projects and reports. All
arguments go directly to the Python CLI without a shell. Commands run with the
current user's permissions. Publishing remains a separate authorized action.
