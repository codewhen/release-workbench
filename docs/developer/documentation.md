# Maintain the documentation

The human-edited Markdown under docs is the single content source for repository reading, local bundled docs and GitHub Pages. VitePress 1.6.4 supplies rendering and local search. User chapters explain actions; developer chapters explain implementation.

## Development commands

From the repository root with the Python development environment activated and frontend dependencies installed:

```bash
npm --prefix docs-site ci
npm --prefix docs-site run dev
# Disposable fixture execution and content/link coverage:
npm --prefix docs-site run examples
npm --prefix docs-site run check
# Capture real application screenshots; Chromium must be installed:
npm --prefix frontend run build
npm --prefix docs-site run screenshots
# Offline app bundle and browser checks:
npm --prefix docs-site run build
# Preserve the app bundle, then build the hosted base for two-path checks:
npm --prefix docs-site run build:pages
npm --prefix docs-site run test:browser
```

The scripts use `python` from PATH; activate `.venv` or set WORKBENCH_PYTHON for screenshot/server scripts when necessary. Python checks need the project dependencies. Frontend Playwright supplies Chromium and browser tooling; no browser dependencies are required by end users.

## Reproducible evidence

`example_fixtures.py` defines deterministic downloadable YAML, companion files and card locations. Regenerate after intentional example changes, not as a way to overwrite edited prose. `check_examples.py` compiles every workflow and executes examples in temporary folders, with a local HTTP fixture, prepared poll file and scripted synthetic manual answers. No personal projects are read.

`screenshots.mjs` starts an isolated server, loads those fixtures, fixes viewport/reduced-motion settings and captures configured card panels, layout tools and user journeys. Images are actual app output. Inspect desktop and mobile captures before accepting them. Document expected output in prose; do not replace the guide with screenshots alone.

## Coverage contract

`coverage.json` maps registered cards, modes, fields, common execution settings (including retry subfields), workflow fields and visible feature groups to pages. Reviewed UI source hashes force a documentation/screenshot review when those interface modules change; update hashes only after that review. A card/mode/field missing from that manifest fails check. Pages must include their referenced examples/screenshots and the documented sections. The checker resolves local links and heading anchors; VitePress also checks Markdown targets.

Editorial accuracy is still a review responsibility. Inventory coverage does not prove a paragraph teaches a concept correctly. Use exact UI labels and verify the described action in the app. Do not imply Windows execution from reviewed commands or synthetic screenshots.

## Local and hosted builds

Local builds use `/docs/` and copy into the separate Python documentation directory. App frontend rebuilding only replaces static app assets and must not remove this bundle. Pages builds use `/release-workbench/`. Both publish companion downloads and build a local search index. No analytics, paid search, external fonts or CDNs are required.

Home/editor links open a new tab; card inspector links use kind-specific pages. Unknown local documentation paths return HTTP 404; the server bounds paths to the bundled docs root.

A manually dispatched Pages workflow is prepared. Publication still requires a human to configure GitHub Pages and authorize a deployment. Do not silently push or change hosting settings while editing docs.
