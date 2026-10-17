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

## Install from the public registry

After a maintainer publishes the package with the preview tag:

```bash
npm install -g @codewhen/workbench@preview
workbench
workbench create
```

Or run without a global install:

```bash
npx @codewhen/workbench@preview
npx @codewhen/workbench@preview serve
npx @codewhen/workbench@preview create
```

These commands require a published version and preview tag. ETARGET means the requested version/tag cannot be resolved. Check availability with:

```bash
npm view @codewhen/workbench dist-tags versions --json
```

See the [full installation guide](https://github.com/codewhen/release-workbench/blob/codex/typed-flowcharts-preview/docs/user/installation.md) for exact versions, updates, removal and first-launch requirements.

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
