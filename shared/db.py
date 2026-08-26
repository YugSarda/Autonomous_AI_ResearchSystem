"""Shared async PostgreSQL connection pool for all microservices."""
import os
import asyncpg
from typing import Optional

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://research:research_pass@postgres:5432/research_db"
)

_pool: Optional[asyncpg.Pool] = None


async def get_pool() -> asyncpg.Pool:
    """Get or create the global asyncpg connection pool."""
    global _pool
    if _pool is None:
        print(f"🔌 Creating PostgreSQL connection pool...")
        _pool = await asyncpg.create_pool(
            DATABASE_URL,
            min_size=5,
            max_size=20,
            command_timeout=30,
        )
        print(f"✅ PostgreSQL pool created (min=5, max=20)")
    return _pool


async def init_db():
    """Initialize database schema for all services."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Task store schema
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

        # Create index on status for fast pending task lookups
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_ingestion_tasks_status
            ON ingestion_tasks(status)
        """)

        # Memory store schema
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id BIGSERIAL PRIMARY KEY,
                session_id TEXT NOT NULL,
                query TEXT NOT NULL,
                answer TEXT NOT NULL,
                summary TEXT,
                confidence INTEGER DEFAULT 0,
                timestamp TEXT NOT NULL,
                metadata TEXT DEFAULT '{}'
            )
        """)

        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_conversations_session
            ON conversations(session_id)
        """)

        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_conversations_timestamp
            ON conversations(timestamp DESC)
        """)

    print("✅ Database schema initialized")


async def close_pool():
    """Close the connection pool gracefully."""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
        print("🔌 PostgreSQL pool closed")