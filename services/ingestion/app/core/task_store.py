"""Task Store - Tracks async ingestion task status using PostgreSQL."""
from __future__ import annotations

import uuid
import time
import os
from typing import Dict, Any, Optional, List

from shared.db import get_pool


async def init_task_store():
    """Initialize the task store database schema."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS ingestion_tasks (
                task_id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                message TEXT DEFAULT '',
                created_at DOUBLE PRECISION NOT NULL,
                updated_at DOUBLE PRECISION NOT NULL,
                completed_at DOUBLE PRECISION
            )
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_ingestion_tasks_status
            ON ingestion_tasks(status)
        """)
    print("✅ Task store initialized (PostgreSQL)")


async def create_task(filename: str) -> str:
    """Create a new ingestion task and return its ID."""
    task_id = str(uuid.uuid4())
    now = time.time()

    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO ingestion_tasks (task_id, filename, status, created_at, updated_at) VALUES ($1, $2, $3, $4, $5)",
            task_id, filename, "pending", now, now,
        )
    print(f"📋 Task created: {task_id} for {filename}")
    return task_id


async def update_task(task_id: str, status: str, message: str = ""):
    """Update the status of a task."""
    now = time.time()
    completed_at = now if status in ("done", "failed") else None

    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE ingestion_tasks SET status = $1, message = $2, updated_at = $3, completed_at = $4 WHERE task_id = $5",
            status, message, now, completed_at, task_id,
        )


async def get_task(task_id: str) -> Optional[Dict[str, Any]]:
    """Get a task by ID."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM ingestion_tasks WHERE task_id = $1", task_id
        )
        if row:
            return dict(row)
        return None


async def get_all_tasks(limit: int = 20) -> List[Dict[str, Any]]:
    """Get all tasks, most recent first."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM ingestion_tasks ORDER BY created_at DESC LIMIT $1", limit
        )
        return [dict(row) for row in rows]


async def get_pending_tasks() -> List[Dict[str, Any]]:
    """Get all pending tasks."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM ingestion_tasks WHERE status = 'pending' ORDER BY created_at ASC"
        )
        return [dict(row) for row in rows]