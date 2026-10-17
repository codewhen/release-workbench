"""Recognize application deep links without falling back for arbitrary file paths."""

from __future__ import annotations

import re
from urllib.parse import unquote

_PAGE = re.compile(
    r"/(?:workspace|folders/[^/]+(?:/[^/]+)*|workflows"
    r"(?:/[^/]+(?:/(?:run|edit)(?:/(?:canvas|list|yaml))?)?"
    r"(?:/functions/[^/]+)?(?:/cards/[^/]+)?(?:/settings)?)?)/?"
)


def application_page(path: str) -> bool:
    return bool(_PAGE.fullmatch(path)) and all(
        unquote(part) not in {".", ".."} and "\x00" not in unquote(part) for part in path.split("/")
    )
