"""Long-term Memory Store - SQLite-based persistent storage for conversation memory."""
import json
import sqlite3
import os
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "memory.db")
def _get_db() -> sqlite3.Connection:
    """Get a thread-local SQLite connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize the memory database schema."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = _get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            query TEXT NOT NULL,
            answer TEXT NOT NULL,
            summary TEXT,
            confidence INTEGER DEFAULT 0,
            timestamp TEXT NOT NULL,
            metadata TEXT DEFAULT '{}'
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_conversations_session
        ON conversations(session_id)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_conversations_timestamp
        ON conversations(timestamp DESC)
    """)
    conn.commit()
    conn.close()
    print(f"✅ Memory DB initialized at {DB_PATH}")


def store_conversation(
    session_id: str,
    query: str,
    answer: str,
    confidence: int = 0,
    summary: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
):
    """Store a conversation in long-term memory."""
    try:
        conn = _get_db()
        conn.execute(
            """INSERT INTO conversations
               (session_id, query, answer, summary, confidence, timestamp, metadata)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                session_id,
                query,
                answer,
                summary or answer[:200],
                confidence,
                datetime.utcnow().isoformat(),
                json.dumps(metadata or {}),
            )
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"⚠️ Failed to store conversation: {e}")


def get_recent_conversations(
    session_id: str,
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """Retrieve recent conversations for a session."""
    try:
        conn = _get_db()
        rows = conn.execute(
            """SELECT query, answer, summary, confidence, timestamp
               FROM conversations
               WHERE session_id = ?
               ORDER BY timestamp DESC
               LIMIT ?""",
            (session_id, limit),
        ).fetchall()
        conn.close()
        return [dict(row) for row in rows]
    except Exception as e:
        print(f"⚠️ Failed to retrieve conversations: {e}")
        return []


def get_long_term_summary(session_id: str) -> str:
    """Get a summary of all conversations for a session."""
    try:
        conn = _get_db()
        rows = conn.execute(
            """SELECT summary, confidence, timestamp
               FROM conversations
               WHERE session_id = ?
               ORDER BY timestamp DESC
               LIMIT 20""",
            (session_id,),
        ).fetchall()
        conn.close()

        if not rows:
            return ""

        parts = []
        for i, row in enumerate(rows[::-1]):  # Oldest first
            parts.append(f"[{i+1}] (confidence: {row['confidence']}%): {row['summary']}")

        return "\n".join(parts)
    except Exception as e:
        print(f"⚠️ Failed to build summary: {e}")
        return ""


def clear_session(session_id: str):
    """Clear all memory for a session."""
    try:
        conn = _get_db()
        conn.execute("DELETE FROM conversations WHERE session_id = ?", (session_id,))
        conn.commit()
        conn.close()
        print(f"🧹 Cleared memory for session: {session_id}")
    except Exception as e:
        print(f"⚠️ Failed to clear session: {e}")