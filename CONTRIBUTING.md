# Contributing

Python 3.11+ and Node 22 are the development prerequisites. Runtime users need only Python and the packaged wheel.

```bash
python -m venv .venv
# POSIX:
source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -e . build setuptools wheel
npm --prefix frontend ci
npm --prefix frontend test
npm --prefix frontend run build
python -m unittest discover -s tests -v
python -m build
```

Commit frontend source and built static assets together. The wheel includes the offline static UI and JSON Schema. Do not put private project workflows, real logs, credentials, device identifiers or customer fixtures in this repository. Examples and tests must use synthetic values and portable commands.

Change the schema, browser controls, documentation and tests together when adding configuration fields. Browser, YAML and wizard output must agree. For execution changes add tests that exercise real child processes, dependencies and resource ownership rather than only copying implementation logic.

A release is a versioned wheel/source archive with SHA256 checksums. Verify a clean wheel installation and standalone example before publishing GitHub release assets. CI recipes may run on free/local runners; successful macOS plans do not replace actual native Windows verification.
