"""Continue card specification."""

from __future__ import annotations

from .base import TerminalSpec


class ContinueSpec(TerminalSpec):
    kind, category, label = "continue", "Control flows", "Continue"
