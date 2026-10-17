"""Reconnect local CLI launches to an already-running dashboard."""

from __future__ import annotations

import json
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

from release_workbench.infrastructure.sessions import LocalSessions


def reuse_dashboard(project: Path, storage: Path, port: int) -> bool:
    base = f"http://127.0.0.1:{port}"
    try:
        with urlopen(base + "/api/instance", timeout=1) as response:
            instance = json.load(response)
    except (URLError, OSError, ValueError):
        return False
    if instance.get("application") != "workflow-workbench-v3":
        return False
    if instance.get("storage") != str(storage.resolve()):
        raise ValueError("This port serves another Workbench library. Use a different --port.")
    request = Request(
        base + "/api/register",
        data=json.dumps({"path": str(project.resolve())}).encode(),
        headers={
            "Content-Type": "application/json",
            "X-Workbench-Token": LocalSessions(storage / "browser-sessions.json").token,
        },
    )
    with urlopen(request, timeout=5) as response:
        response.read()
    return True
