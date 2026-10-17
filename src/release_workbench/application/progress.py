"""Parse bounded progress events before they reach persisted run evidence."""

from __future__ import annotations

import json
import math
from typing import Any


def parse_progress(text: str) -> dict[str, Any] | None:
    try:
        value = json.loads(text)
    except (ValueError, TypeError):
        return None
    if not isinstance(value, dict):
        return None
    done, total = value.get("done"), value.get("total")
    if (
        type(done) not in (int, float)
        or type(total) not in (int, float)
        or not isinstance(done, (int, float))
        or not isinstance(total, (int, float))
        or not math.isfinite(done)
        or not math.isfinite(total)
        or total <= 0
        or done < 0
        or done > total
    ):
        return None
    return {"done": done, "total": total, "stage": str(value.get("stage", "")), "measured": True}
