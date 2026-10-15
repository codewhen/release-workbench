"""One scheduling coordinator shared by every function and workspace call."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager


class Coordinator:
    def __init__(self, concurrency: int):
        self.concurrency = concurrency
        self.active: dict[str, tuple[set[str], bool]] = {}
        self.paused = False
        self.exclusive_waiters: set[str] = set()

    async def ready(self, check: Callable[[], None]) -> None:
        while self.paused:
            check()
            await asyncio.sleep(0.03)
        check()

    @asynccontextmanager
    async def slot(
        self, path: str, resources: set[str], exclusive: bool, check: Callable[[], None]
    ) -> AsyncIterator[None]:
        if exclusive:
            self.exclusive_waiters.add(path)
        try:
            while True:
                await self.ready(check)
                held = (
                    set().union(*(item[0] for item in self.active.values()))
                    if self.active
                    else set()
                )
                available = (
                    not held.intersection(resources)
                    and not any(item[1] for item in self.active.values())
                    and len(self.active) < self.concurrency
                )
                if available and (not self.active if exclusive else not self.exclusive_waiters):
                    self.active[path] = (resources, exclusive)
                    break
                await asyncio.sleep(0.03)
            yield
        finally:
            self.exclusive_waiters.discard(path)
            self.active.pop(path, None)
