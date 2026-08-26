"""Long-term Memory Store - PostgreSQL-based persistent storage for conversation memory."""
import json
import os
import time
from datetime import datetime
from typing import Dict, List, Optional, Any

from shared.db import get_pool


async def init_db():
    """Initialize the memory database schema."""
    pool = await get_pool()
    async with pool.acquire() as conn:
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
    print(f"✅ Memory DB initialized (PostgreSQL)")


async def store_conversation(
    session_id: str,
    query: str,
    answer: str,
    confidence: int = 0,
    summary: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
):
    """Store a conversation in long-term memory."""
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO conversations
                   (session_id, query, answer, summary, confidence, timestamp, metadata)
                   VALUES ($1, $2, $3, $4, $5, $6, $7)""",
                session_id,
                query,
                answer,
                summary or answer[:200],
                confidence,
                datetime.utcnow().isoformat(),
                json.dumps(metadata or {}),
            )
    except Exception as e:
        print(f"⚠️ Failed to store conversation: {e}")


async def get_recent_conversations(
    session_id: str,
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """Retrieve recent conversations for a session."""
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """SELECT query, answer, summary, confidence, timestamp
                   FROM conversations
                   WHERE session_id = $1
                   ORDER BY timestamp DESC
                   LIMIT $2""",
                session_id, limit,
            )
            return [dict(row) for row in rows]
    except Exception as e:
        print(f"⚠️ Failed to retrieve conversations: {e}")
        return []


async def get_long_term_summary(session_id: str) -> str:
    """Get a summary of all conversations for a session."""
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """SELECT summary, confidence, timestamp
                   FROM conversations
                   WHERE session_id = $1
                   ORDER BY timestamp DESC
                   LIMIT 20""",
                session_id,
            )

        if not rows:
            return ""

        parts = []
        for i, row in enumerate(rows[::-1]):  # Oldest first
            parts.append(f"[{i+1}] (confidence: {row['confidence']}%): {row['summary']}")

        return "\n".join(parts)
    except Exception as e:
        print(f"⚠️ Failed to build summary: {e}")
        return ""


async def clear_session(session_id: str):
    """Clear all memory for a session."""
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM conversations WHERE session_id = $1",
                session_id,
            )
        print(f"🧹 Cleared memory for session: {session_id}")
    except Exception as e:
        print(f"⚠️ Failed to clear session: {e}")