"""Resolve read-only bundled documentation without exposing adjacent package files."""

from __future__ import annotations

from pathlib import Path


def documentation_file(relative: str, root: Path | None = None) -> tuple[Path | None, int]:
    base = (root or Path(__file__).resolve().parents[1] / "documentation").resolve()
    candidate = (base / (relative or "index.html")).resolve()
    if not candidate.is_relative_to(base):
        return None, 404
    if candidate.is_dir():
        candidate = candidate / "index.html"
    elif not candidate.suffix:
        candidate = candidate.with_suffix(".html")
    if candidate.is_file() and candidate.resolve().is_relative_to(base):
        return candidate, 200
    fallback = base / "404.html"
    return (
        fallback if fallback.is_file() and fallback.resolve().is_relative_to(base) else None
    ), 404
