"""Async Ingestion Worker - Processes file ingestion using Redis Streams for persistent queue."""
from __future__ import annotations

import asyncio
import json
import os
import time
import traceback
from typing import Optional

import redis.asyncio as aioredis

from app.core.config import REDIS_URL
from app.core.task_store import create_task, update_task
from app.services.ingestion_service import ingest_documents

# Redis Stream configuration
STREAM_KEY = "ingestion:queue"
CONSUMER_GROUP = "ingestion_workers"
CONSUMER_NAME = "worker_1"

_redis_client: Optional[aioredis.Redis] = None
_worker_task: Optional[asyncio.Task] = None


# async def get_redis() -> aioredis.Redis:
#     """Get or create the global Redis client."""
#     global _redis_client
#     if _redis_client is None:
#         _redis_client = aioredis.from_url(
#             REDIS_URL,
#             decode_responses=True,
#         )
#         print("✅ Redis client created for async ingestion")
#     return _redis_client
async def get_redis() -> aioredis.Redis:
    """Get or create the global Redis client."""
    global _redis_client

    if _redis_client is None:
        _redis_client = aioredis.from_url(
            REDIS_URL,
            decode_responses=True,
            socket_timeout=None,
            socket_connect_timeout=10,
        )
        print("✅ Redis client created for async ingestion")

    return _redis_client

async def init_redis_stream():
    """Initialize the Redis Stream consumer group."""
    redis = await get_redis()
    try:
        # Create consumer group (idempotent - error if exists is fine)
        await redis.xgroup_create(
            STREAM_KEY,
            CONSUMER_GROUP,
            id="0",
            mkstream=True,
        )
        print(f"✅ Redis Stream group '{CONSUMER_GROUP}' created for '{STREAM_KEY}'")
    except aioredis.ResponseError as e:
        if "BUSYGROUP" in str(e):
            print(f"ℹ️ Redis Stream group '{CONSUMER_GROUP}' already exists")
        else:
            print(f"⚠️ Redis Stream group error: {e}")


async def start_ingestion_worker():
    """Start the background ingestion worker."""
    global _worker_task
    if _worker_task is not None and not _worker_task.done():
        print("⚠️ Ingestion worker already running")
        return

    await init_redis_stream()
    _worker_task = asyncio.create_task(_ingestion_worker_loop())
    print("🚀 Ingestion worker started (Redis Streams)")


async def stop_ingestion_worker():
    """Stop the background ingestion worker."""
    global _worker_task
    if _worker_task and not _worker_task.done():
        _worker_task.cancel()
        try:
            await _worker_task
        except asyncio.CancelledError:
            pass
        _worker_task = None
        print("🛑 Ingestion worker stopped")


async def enqueue_ingestion(file_path: str) -> str:
    """
    Enqueue a file for async ingestion using Redis Streams.

    Args:
        file_path: Path to the file to ingest.

    Returns:
        task_id: The task ID for status tracking.
    """
    filename = os.path.basename(file_path)
    task_id = await create_task(filename)

    redis = await get_redis()
    await redis.xadd(
        STREAM_KEY,
        {
            "task_id": task_id,
            "file_path": file_path,
            "filename": filename,
            "enqueued_at": str(time.time()),
        },
        maxlen=1000,  # Keep last 1000 messages
    )

    print(f"📤 Enqueued {filename} for async ingestion (task_id={task_id})")
    return task_id


async def _ingestion_worker_loop():
    """Background worker loop that processes ingestion tasks from Redis Stream."""
    print("👷 Ingestion worker loop started (Redis Streams)")
    redis = await get_redis()

    while True:
        try:
            # Read new messages from the stream (blocking read)
            messages = await redis.xreadgroup(
                groupname=CONSUMER_GROUP,
                consumername=CONSUMER_NAME,
                streams={STREAM_KEY: ">"},
                count=1,
                block=5000,  # Block for 5 seconds max
            )

            if not messages:
                await asyncio.sleep(0.1)
                continue

            # Process each message
            for stream_name, stream_messages in messages:
                for msg_id, msg_data in stream_messages:
                    task_id = msg_data.get("task_id")
                    file_path = msg_data.get("file_path")
                    filename = msg_data.get("filename", os.path.basename(file_path))

                    print(f"\n{'='*60}")
                    print(f"📥 ASYNC INGESTION WORKER: Processing task {task_id}")
                    print(f"📂 File: {file_path}")
                    print(f"{'='*60}")

                    # Update task status to processing
                    await update_task(task_id, "processing", "Ingestion started")

                    try:
                        # Run ingestion (synchronous operation, run in executor)
                        loop = asyncio.get_event_loop()
                        index = await loop.run_in_executor(
                            None, ingest_documents, file_path
                        )

                        print(f"✅ Ingestion complete for task {task_id}")

                        # (No retriever built here — the query service rebuilds
                        #  it from ChromaDB on demand. Status is all we track.)
                        await update_task(task_id, "done", "Ingestion completed successfully")

                        # Acknowledge the message (remove from pending)
                        await redis.xack(STREAM_KEY, CONSUMER_GROUP, msg_id)

                    except Exception as e:
                        error_msg = f"Ingestion failed: {str(e)}"
                        print(f"❌ {error_msg}")
                        traceback.print_exc()
                        await update_task(task_id, "failed", error_msg)

                        # Acknowledge failed message so it doesn't block the stream
                        await redis.xack(STREAM_KEY, CONSUMER_GROUP, msg_id)

        except asyncio.CancelledError:
            print("👷 Ingestion worker cancelled")
            break
        except Exception as e:
            print(f"❌ Ingestion worker error: {e}")
            traceback.print_exc()
            await asyncio.sleep(1)