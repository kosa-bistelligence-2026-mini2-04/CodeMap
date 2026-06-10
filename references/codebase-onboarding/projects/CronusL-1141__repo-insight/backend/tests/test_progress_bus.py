from __future__ import annotations

import asyncio
import pytest

from app.api.progress_bus import ProgressBus


@pytest.mark.asyncio
async def test_publish_and_subscribe():
    bus = ProgressBus()
    await bus.publish("job1", {"type": "stage", "stage": "clone", "status": "running"})
    await bus.publish("job1", {"type": "completed"})

    events = []
    async for event in bus.subscribe("job1", timeout=2.0):
        events.append(event)

    assert len(events) == 2
    assert events[0]["type"] == "stage"
    assert events[1]["type"] == "completed"


@pytest.mark.asyncio
async def test_subscribe_stops_on_completed():
    bus = ProgressBus()
    await bus.publish("job2", {"type": "completed"})
    await bus.publish("job2", {"type": "should_not_appear"})

    events = []
    async for event in bus.subscribe("job2", timeout=2.0):
        events.append(event)

    assert events[-1]["type"] == "completed"
    assert len(events) == 1


@pytest.mark.asyncio
async def test_separate_job_queues():
    bus = ProgressBus()
    await bus.publish("jobA", {"type": "stage", "data": "A"})
    await bus.publish("jobB", {"type": "stage", "data": "B"})
    await bus.publish("jobA", {"type": "completed"})
    await bus.publish("jobB", {"type": "completed"})

    events_a = []
    async for ev in bus.subscribe("jobA", timeout=2.0):
        events_a.append(ev)

    assert all(e.get("data") != "B" for e in events_a if "data" in e)
