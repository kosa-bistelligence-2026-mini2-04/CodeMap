from __future__ import annotations

import asyncio
from typing import AsyncIterator


class ProgressBus:
    """Per-job asyncio.Queue-based progress event bus."""

    def __init__(self) -> None:
        self._queues: dict[str, asyncio.Queue] = {}

    def get_or_create(self, job_id: str) -> asyncio.Queue:
        if job_id not in self._queues:
            self._queues[job_id] = asyncio.Queue()
        return self._queues[job_id]

    async def publish(self, job_id: str, event: dict) -> None:
        q = self.get_or_create(job_id)
        await q.put(event)

    async def subscribe(self, job_id: str, timeout: float = 300.0) -> AsyncIterator[dict]:
        """Yield events until a 'completed' event or the overall timeout elapses.

        BUG fix: previously a 5s idle (no events) caused a premature ``break``,
        killing the WebSocket while agents were mid-task. The 5s cadence now
        acts only as a cooperative cancellation check — we keep waiting for
        new events until the overall deadline or a terminal event arrives.
        """
        q = self.get_or_create(job_id)
        deadline = asyncio.get_event_loop().time() + timeout
        while True:
            remaining = deadline - asyncio.get_event_loop().time()
            if remaining <= 0:
                break
            try:
                event = await asyncio.wait_for(q.get(), timeout=min(remaining, 5.0))
            except asyncio.TimeoutError:
                continue  # no events in the last 5s — keep the stream alive
            yield event
            etype = event.get("type")
            if etype in ("completed", "failed"):
                break

    def cleanup(self, job_id: str) -> None:
        self._queues.pop(job_id, None)


progress_bus = ProgressBus()
