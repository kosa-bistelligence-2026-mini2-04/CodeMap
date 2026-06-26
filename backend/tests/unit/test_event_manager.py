import asyncio
import unittest
from datetime import datetime, timezone

from app.pipeline.event_manager import EventManager
from app.pipeline.schemas import JobStatus, PipelineStage, ProgressEvent


def progress_event(status: JobStatus = JobStatus.IN_PROGRESS) -> ProgressEvent:
    return ProgressEvent(
        stage=PipelineStage.CODE_MAP,
        status=status,
        progress=50,
        message="testing",
        timestamp=datetime.now(timezone.utc),
    )


class EventManagerTests(unittest.IsolatedAsyncioTestCase):
    async def test_tracked_task_reference_is_released_after_completion(self):
        manager = EventManager()
        started = asyncio.Event()
        finish = asyncio.Event()

        async def background_job():
            started.set()
            await finish.wait()

        task = manager._create_tracked_task(background_job())

        await started.wait()
        self.assertIn(task, manager._task_refs)

        finish.set()
        await task
        await asyncio.sleep(0)

        self.assertNotIn(task, manager._task_refs)

    async def test_publish_updates_last_event_and_subscriber_under_lock(self):
        manager = EventManager()
        job_id = "job-1"
        queue: asyncio.Queue = asyncio.Queue()
        event = progress_event()

        async with manager._lock:
            manager._subscribers[job_id].append(queue)

        await manager.publish(job_id, event)

        self.assertIs(manager.get_last_event(job_id), event)
        self.assertIs(await queue.get(), event)
