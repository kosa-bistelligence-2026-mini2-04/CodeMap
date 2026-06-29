import asyncio
import unittest
import uuid
from app.gen.background import _mark_in_progress, _mark_done
from app.infra.redis import get_redis_client, init_redis, close_redis

class TestDistributedLock(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        await init_redis()
        
    async def asyncTearDown(self):
        await close_redis()

    async def test_docs_generation_distributed_lock(self):
        redis = get_redis_client()
        if not redis:
            self.skipTest("Redis not configured")
            
        repo_id = uuid.uuid4()
        async def try_acquire():
            return await _mark_in_progress(repo_id)
            
        results = await asyncio.gather(*(try_acquire() for _ in range(5)))
        success_count = sum(1 for r in results if r is True)
        self.assertEqual(success_count, 1)
        
        await _mark_done(repo_id)
