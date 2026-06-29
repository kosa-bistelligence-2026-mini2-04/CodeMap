import logging
from typing import Optional
import redis.asyncio as aioredis

from app.infra.config import get_settings

logger = logging.getLogger(__name__)

_redis_client: Optional[aioredis.Redis] = None

async def init_redis() -> None:
    global _redis_client
    settings = get_settings()
    redis_url = getattr(settings, 'REDIS_URL', None)
    
    if redis_url is not None and hasattr(redis_url, 'get_secret_value'):
        redis_url = redis_url.get_secret_value()
        
    if redis_url and str(redis_url).strip():
        try:
            _redis_client = aioredis.from_url(str(redis_url), decode_responses=True)
            await _redis_client.ping()
            logger.info('[Redis] Connected')
        except Exception as e:
            logger.warning('[Redis] Connection failed, running in single-process mode: %s', e)
            _redis_client = None
    else:
        logger.info('[Redis] REDIS_URL not configured. Running in single-process mode.')

async def close_redis() -> None:
    global _redis_client
    if _redis_client:
        await _redis_client.aclose()
        _redis_client = None

def get_redis_client() -> Optional[aioredis.Redis]:
    return _redis_client
