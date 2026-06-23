"""
NeuroGuard AI - Redis Service
==============================
Manages all Redis interactions across 4 roles:
1. EMBEDDING CACHE  - Cache face centroids to avoid DB queries per frame
2. PUB/SUB          - Push real-time events to connected dashboards
3. JWT BLACKLIST    - Invalidated tokens for logout
4. TASK QUEUE       - Queue SNN training as background jobs

Educational Notes:
- This module demonstrates how Redis is used in production AI systems
- Each role maps to a real-world pattern (see implementation plan)
"""

import asyncio
import json
import logging
from typing import Any, AsyncIterator, Dict, Optional

import numpy as np
import redis.asyncio as aioredis

from backend.config import settings

logger = logging.getLogger(__name__)

# Redis key prefixes (namespacing prevents key collisions)
CENTROID_PREFIX = "neuroguard:centroid:"
CENTROID_NAMES_KEY = "neuroguard:centroid_names"
BLACKLIST_PREFIX = "neuroguard:blacklist:"
TRAINING_STATUS_KEY = "neuroguard:training:status"
TRAINING_QUEUE_KEY = "neuroguard:training:queue"
SURVEILLANCE_CHANNEL = "neuroguard:events:surveillance"
SYSTEM_METRICS_KEY = "neuroguard:metrics"


class RedisService:
    """
    Unified Redis client managing cache, pub/sub, sessions, and queues.
    Now includes a full in-memory fallback system if Redis is unavailable.

    Usage:
        redis_svc = RedisService()
        await redis_svc.connect()
        await redis_svc.cache_centroid(user_id=1, centroid=np.array(...), name="John")
        await redis_svc.disconnect()
    """

    def __init__(self) -> None:
        self._client: Optional[aioredis.Redis] = None
        self._pubsub: Optional[aioredis.client.PubSub] = None
        
        # In-memory fallbacks
        self._fallback_mode = False
        self._fallback_centroids: Dict[int, tuple] = {}
        self._fallback_metrics: Dict[str, Any] = {}
        self._fallback_subscribers: list[asyncio.Queue] = []
        self._fallback_blacklist: set[str] = set()
        self._fallback_training_status: Dict[str, Any] = {"status": "idle", "details": {}}
        self._fallback_training_queue: asyncio.Queue = asyncio.Queue()
        self._fallback_worker_task: Optional[asyncio.Task] = None

    async def connect(self) -> None:
        """Establish Redis connection or enable fallback mode."""
        try:
            self._client = aioredis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=False,
            )
            await self._client.ping()
            self._fallback_mode = False
            logger.info(f"Connected to Redis at {settings.REDIS_URL}")
        except Exception as e:
            logger.warning(
                f"Redis connection failed: {e}. "
                "System will operate in IN-MEMORY FALLBACK mode."
            )
            self._client = None
            self._fallback_mode = True
            
            # Start local background worker for training queue
            self._fallback_worker_task = asyncio.create_task(self._local_training_worker())

    async def disconnect(self) -> None:
        """Close Redis connection cleanly."""
        if self._pubsub:
            await self._pubsub.close()
        if self._client:
            await self._client.close()
            logger.info("Redis connection closed")
        if self._fallback_worker_task:
            self._fallback_worker_task.cancel()

    @property
    def is_connected(self) -> bool:
        """Check if Redis is available. Always returns True so app works in fallback."""
        # By returning True even in fallback, we tell the rest of the app to proceed normally.
        return True

    # =========================================================================
    # 1. EMBEDDING CACHE
    # =========================================================================

    async def cache_centroid(
        self, user_id: int, centroid: np.ndarray, name: str
    ) -> None:
        if self._fallback_mode:
            self._fallback_centroids[user_id] = (centroid, name)
            return

        try:
            key = f"{CENTROID_PREFIX}{user_id}"
            await self._client.set(key, centroid.astype(np.float32).tobytes())
            await self._client.hset(CENTROID_NAMES_KEY, str(user_id), name)
            logger.debug(f"Cached centroid for user_id={user_id} ({name})")
        except Exception as e:
            logger.error(f"Failed to cache centroid: {e}")

    async def get_all_cached_centroids(self) -> Dict[int, tuple]:
        if self._fallback_mode:
            return dict(self._fallback_centroids)

        try:
            centroids = {}
            names = await self._client.hgetall(CENTROID_NAMES_KEY)

            for user_id_bytes, name_bytes in names.items():
                user_id = int(user_id_bytes.decode() if isinstance(user_id_bytes, bytes) else user_id_bytes)
                name = name_bytes.decode() if isinstance(name_bytes, bytes) else name_bytes

                key = f"{CENTROID_PREFIX}{user_id}"
                vector_bytes = await self._client.get(key)

                if vector_bytes:
                    vector = np.frombuffer(vector_bytes, dtype=np.float32)
                    centroids[user_id] = (vector, name)

            return centroids
        except Exception as e:
            logger.error(f"Failed to load cached centroids: {e}")
            return {}

    async def invalidate_centroid(self, user_id: int) -> None:
        if self._fallback_mode:
            self._fallback_centroids.pop(user_id, None)
            return

        try:
            await self._client.delete(f"{CENTROID_PREFIX}{user_id}")
            await self._client.hdel(CENTROID_NAMES_KEY, str(user_id))
            logger.debug(f"Invalidated centroid cache for user_id={user_id}")
        except Exception as e:
            logger.error(f"Failed to invalidate centroid: {e}")

    async def invalidate_all_centroids(self) -> None:
        if self._fallback_mode:
            self._fallback_centroids.clear()
            return

        try:
            async for key in self._client.scan_iter(f"{CENTROID_PREFIX}*"):
                await self._client.delete(key)
            await self._client.delete(CENTROID_NAMES_KEY)
            logger.info("Cleared all centroid caches")
        except Exception as e:
            logger.error(f"Failed to clear centroid caches: {e}")

    # =========================================================================
    # 2. PUB/SUB — Real-Time Event Broadcasting
    # =========================================================================

    async def publish_event(self, event_data: dict) -> None:
        if self._fallback_mode:
            # Broadcast to all local subscribers
            dead_queues = []
            for q in self._fallback_subscribers:
                try:
                    q.put_nowait(event_data)
                except asyncio.QueueFull:
                    dead_queues.append(q)
            for dq in dead_queues:
                if dq in self._fallback_subscribers:
                    self._fallback_subscribers.remove(dq)
            return

        try:
            message = json.dumps(event_data, default=str)
            await self._client.publish(SURVEILLANCE_CHANNEL, message)
        except Exception as e:
            logger.error(f"Failed to publish event: {e}")

    async def subscribe_events(self) -> AsyncIterator[dict]:
        if self._fallback_mode:
            q = asyncio.Queue()
            self._fallback_subscribers.append(q)
            try:
                while True:
                    event_data = await q.get()
                    yield event_data
            except asyncio.CancelledError:
                pass
            finally:
                if q in self._fallback_subscribers:
                    self._fallback_subscribers.remove(q)
            return

        self._pubsub = self._client.pubsub()
        await self._pubsub.subscribe(SURVEILLANCE_CHANNEL)

        try:
            async for message in self._pubsub.listen():
                if message["type"] == "message":
                    data = message["data"]
                    if isinstance(data, bytes):
                        data = data.decode("utf-8")
                    yield json.loads(data)
        finally:
            await self._pubsub.unsubscribe(SURVEILLANCE_CHANNEL)

    # =========================================================================
    # 3. JWT BLACKLIST — Token Revocation
    # =========================================================================

    async def blacklist_token(self, token: str, ttl_seconds: int) -> None:
        if self._fallback_mode:
            self._fallback_blacklist.add(token)
            # A simple timeout to remove it eventually (ignoring exact ttl for simplicity in fallback)
            asyncio.get_event_loop().call_later(ttl_seconds, lambda: self._fallback_blacklist.discard(token))
            return

        try:
            key = f"{BLACKLIST_PREFIX}{token}"
            await self._client.setex(key, ttl_seconds, "1")
            logger.debug("Token blacklisted")
        except Exception as e:
            logger.error(f"Failed to blacklist token: {e}")

    async def is_token_blacklisted(self, token: str) -> bool:
        if self._fallback_mode:
            return token in self._fallback_blacklist

        try:
            key = f"{BLACKLIST_PREFIX}{token}"
            result = await self._client.exists(key)
            return bool(result)
        except Exception as e:
            logger.error(f"Failed to check token blacklist: {e}")
            return False

    # =========================================================================
    # 4. TASK QUEUE — Training Jobs
    # =========================================================================

    async def enqueue_training(self, params: dict) -> None:
        if self._fallback_mode:
            await self.set_training_status("queued")
            await self._fallback_training_queue.put(params)
            logger.info("Local training job enqueued")
            return

        try:
            message = json.dumps(params)
            await self._client.rpush(TRAINING_QUEUE_KEY, message)
            await self.set_training_status("queued")
            logger.info("Training job enqueued to Redis")
        except Exception as e:
            logger.error(f"Failed to enqueue training: {e}")

    async def dequeue_training(self) -> Optional[dict]:
        if self._fallback_mode:
            # We don't manually dequeue in fallback mode externally, the local worker does it
            return None

        try:
            result = await self._client.lpop(TRAINING_QUEUE_KEY)
            if result:
                data = result.decode("utf-8") if isinstance(result, bytes) else result
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"Failed to dequeue training: {e}")
            return None

    async def set_training_status(self, status: str, details: Optional[dict] = None) -> None:
        if self._fallback_mode:
            self._fallback_training_status = {"status": status, "details": details or {}}
            return

        try:
            data = {"status": status, "details": details or {}}
            await self._client.set(
                TRAINING_STATUS_KEY,
                json.dumps(data, default=str),
            )
        except Exception as e:
            logger.error(f"Failed to set training status: {e}")

    async def get_training_status(self) -> dict:
        if self._fallback_mode:
            return self._fallback_training_status

        try:
            result = await self._client.get(TRAINING_STATUS_KEY)
            if result:
                data = result.decode("utf-8") if isinstance(result, bytes) else result
                return json.loads(data)
            return {"status": "idle", "details": {}}
        except Exception as e:
            logger.error(f"Failed to get training status: {e}")
            return {"status": "error", "details": {"error": str(e)}}

    async def _local_training_worker(self) -> None:
        """A background loop that processes training jobs locally when Redis is not available."""
        from backend.database.session import SessionLocal
        from backend.services.training_service import snn_trainer

        while True:
            params = await self._fallback_training_queue.get()
            try:
                await self.set_training_status("training", {"epochs": params.get("epochs")})
                
                # Execute blocking code in a thread
                def run_training():
                    with SessionLocal() as db:
                        return snn_trainer.train_model(
                            db=db,
                            epochs=params.get("epochs", 50),
                            lr=params.get("learning_rate", 0.001),
                            batch_size=params.get("batch_size", 32),
                            notes=params.get("notes", "Local fallback training")
                        )
                
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, run_training)
                
                await self.set_training_status("completed", result)
                # Invalidate cache so new model is used
                await self.invalidate_all_centroids()
                
            except Exception as e:
                logger.error(f"Local training failed: {e}")
                await self.set_training_status("failed", {"error": str(e)})
            finally:
                self._fallback_training_queue.task_done()

    # =========================================================================
    # System Metrics Cache
    # =========================================================================

    async def update_metrics(self, metrics: dict) -> None:
        if self._fallback_mode:
            self._fallback_metrics = metrics
            return

        try:
            await self._client.set(
                SYSTEM_METRICS_KEY,
                json.dumps(metrics, default=str),
            )
        except Exception as e:
            logger.error(f"Failed to update metrics: {e}")

    async def get_metrics(self) -> dict:
        if self._fallback_mode:
            return self._fallback_metrics

        try:
            result = await self._client.get(SYSTEM_METRICS_KEY)
            if result:
                data = result.decode("utf-8") if isinstance(result, bytes) else result
                return json.loads(data)
            return {}
        except Exception as e:
            logger.error(f"Failed to get metrics: {e}")
            return {}


# Global Redis service instance
redis_service = RedisService()

