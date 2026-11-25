from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config import get_setting


class MemoryStore:
    """Use Supabase in hosted deployments; use SQLite only for local development."""

    def __init__(
        self,
        supabase_client: Any | None = None,
        sqlite_path: str | Path | None = None,
    ):
        self.client = supabase_client
        self.sqlite_path = Path(sqlite_path or "data/my_personal_ai.sqlite3")
        self.backend_name = (
            "Supabase（クラウド）" if self.client else "SQLite（ローカル試作用）"
        )
        if not self.client:
            self.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
            self._init_sqlite()

    @classmethod
    def from_settings(cls) -> "MemoryStore":
        url = get_setting("SUPABASE_URL")
        secret = get_setting("SUPABASE_SECRET_KEY") or get_setting("SUPABASE_SERVICE_ROLE_KEY")
        if url and secret:
            from supabase import create_client

            return cls(supabase_client=create_client(str(url), str(secret)))
        return cls()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.sqlite_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _init_sqlite(self) -> None:
        with self._connect() as con:
            con.execute(
                """CREATE TABLE IF NOT EXISTS chat_messages (
                    id TEXT PRIMARY KEY, session_id TEXT NOT NULL, role TEXT NOT NULL,
                    content TEXT NOT NULL, created_at TEXT NOT NULL
                )"""
            )
            con.execute(
                """CREATE TABLE IF NOT EXISTS memories (
                    id TEXT PRIMARY KEY, category TEXT NOT NULL, content TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )"""
            )
            con.execute(
                "CREATE INDEX IF NOT EXISTS idx_chat_session_created "
                "ON chat_messages(session_id, created_at)"
            )

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def add_message(self, session_id: str, role: str, content: str) -> None:
        if role not in {"user", "assistant"}:
            raise ValueError("role must be user or assistant")
        row = {
            "id": str(uuid.uuid4()),
            "session_id": session_id,
            "role": role,
            "content": content[:30000],
            "created_at": self._now(),
        }
        if self.client:
            self.client.table("chat_messages").insert(row).execute()
        else:
            with self._connect() as con:
                con.execute(
                    "INSERT INTO chat_messages VALUES "
                    "(:id,:session_id,:role,:content,:created_at)",
                    row,
                )

    def get_messages(self, session_id: str, limit: int = 60) -> list[dict[str, Any]]:
        if self.client:
            response = (
                self.client.table("chat_messages")
                .select("id,session_id,role,content,created_at")
                .eq("session_id", session_id)
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
            return list(reversed(response.data or []))
        with self._connect() as con:
            rows = con.execute(
                "SELECT id,session_id,role,content,created_at "
                "FROM chat_messages WHERE session_id=? "
                "ORDER BY created_at DESC LIMIT ?",
                (session_id, limit),
            ).fetchall()
            return [dict(row) for row in reversed(rows)]

    def add_memory(self, category: str, content: str) -> None:
        row = {
            "id": str(uuid.uuid4()),
            "category": category[:40],
            "content": content[:5000],
            "created_at": self._now(),
        }
        if self.client:
            self.client.table("memories").insert(row).execute()
        else:
            with self._connect() as con:
                con.execute(
                    "INSERT INTO memories VALUES (:id,:category,:content,:created_at)",
                    row,
                )

    def get_memories(self, limit: int = 100) -> list[dict[str, Any]]:
        if self.client:
            response = (
                self.client.table("memories")
                .select("id,category,content,created_at")
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
            return list(response.data or [])
        with self._connect() as con:
            rows = con.execute(
                "SELECT id,category,content,created_at FROM memories "
                "ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [dict(row) for row in rows]

    def delete_memory(self, memory_id: str) -> None:
        if self.client:
            self.client.table("memories").delete().eq("id", memory_id).execute()
        else:
            with self._connect() as con:
                con.execute("DELETE FROM memories WHERE id=?", (memory_id,))
