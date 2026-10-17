"""Break card specification."""

from __future__ import annotations

from .base import TerminalSpec


class BreakSpec(TerminalSpec):
    kind, category, label = "break", "Control flows", "Break"
