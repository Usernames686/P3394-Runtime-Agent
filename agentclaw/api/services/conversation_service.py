"""
Conversation service layer

Handles all database operations for conversation management.
"""

from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime
import json
import os
import sqlite3
import uuid

from agentclaw.database.manager import get_database
from agentclaw.logger.config import get_logger

logger = get_logger(__name__)


def _delete_result_deleted(status: str) -> bool:
    """Return whether asyncpg reports at least one deleted row."""
    parts = str(status or "").split()
    if len(parts) == 2 and parts[0].upper() == "DELETE":
        try:
            return int(parts[1]) > 0
        except ValueError:
            return True
    return True


class ConversationService:
    """Service for conversation CRUD operations."""

    def __init__(self, sqlite_path: Optional[str | Path] = None):
        self._table_ready = False
        self._feedback_table_ready = False
        self._memory_conversations: Dict[str, dict] = {}
        self._memory_feedback: Dict[str, Dict[int, str]] = {}
        self._sqlite_path = Path(sqlite_path).expanduser().resolve() if sqlite_path else self._default_sqlite_path()
        self._sqlite_ready = False

    async def _get_pool(self):
        db = get_database()
        if db and db.pg_pool:
            return db.pg_pool
        return None

    @staticmethod
    def _default_sqlite_path() -> Optional[Path]:
        explicit = os.getenv("AGENTCLAW_SQLITE_PATH", "").strip()
        if explicit:
            return Path(explicit).expanduser().resolve()

        data_dir = os.getenv("AGENTCLAW_DATA_DIR", "").strip()
        if data_dir:
            return (Path(data_dir).expanduser() / "agentclaw-local.db").resolve()

        project_dir = os.getenv("AGENTCLAW_PROJECT_DIR", "").strip()
        if project_dir:
            return (Path(project_dir).expanduser() / ".agentclaw" / "agentclaw-local.db").resolve()

        return None

    def _sqlite_enabled(self) -> bool:
        return self._sqlite_path is not None

    def _sqlite_connection(self) -> sqlite3.Connection:
        if not self._sqlite_path:
            raise RuntimeError("SQLite path is not configured")
        self._sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self._sqlite_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_sqlite(self) -> bool:
        if not self._sqlite_enabled():
            return False
        if self._sqlite_ready:
            return True
        try:
            with self._sqlite_connection() as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS agent_conversations (
                        id TEXT PRIMARY KEY,
                        workflow_id TEXT NOT NULL,
                        title TEXT DEFAULT 'New conversation',
                        messages TEXT DEFAULT '[]',
                        source TEXT DEFAULT 'admin',
                        owner_id TEXT,
                        user_id TEXT,
                        tenant_id TEXT,
                        created_at INTEGER,
                        updated_at INTEGER
                    )
                    """
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_agent_conv_workflow ON agent_conversations(workflow_id)"
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_agent_conv_source ON agent_conversations(source)"
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_agent_conv_updated ON agent_conversations(updated_at DESC)"
                )
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS message_feedback (
                        conversation_id TEXT NOT NULL,
                        message_index INTEGER NOT NULL,
                        feedback TEXT,
                        created_at INTEGER,
                        updated_at INTEGER,
                        PRIMARY KEY (conversation_id, message_index)
                    )
                    """
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_feedback_conv ON message_feedback(conversation_id)"
                )
            self._sqlite_ready = True
            return True
        except Exception as e:
            logger.warning(f"Failed to initialize local SQLite conversation store: {e}")
            self._sqlite_path = None
            return False

    async def _ensure_table(self):
        if self._table_ready:
            return True
        pool = await self._get_pool()
        if not pool:
            return False
        try:
            await pool.execute("""
                CREATE TABLE IF NOT EXISTS agent_conversations (
                    id VARCHAR(50) PRIMARY KEY,
                    workflow_id VARCHAR(100) NOT NULL,
                    title VARCHAR(200) DEFAULT '新会话',
                    messages JSONB DEFAULT '[]'::jsonb,
                    source VARCHAR(20) DEFAULT 'admin',
                    owner_id VARCHAR(100),
                    user_id VARCHAR(100),
                    tenant_id VARCHAR(100),
                    created_at BIGINT,
                    updated_at BIGINT
                );
            """)
            await pool.execute("""
                CREATE INDEX IF NOT EXISTS idx_agent_conv_workflow ON agent_conversations(workflow_id);
            """)
            await pool.execute("""
                CREATE INDEX IF NOT EXISTS idx_agent_conv_updated ON agent_conversations(updated_at DESC);
            """)
        except Exception as e:
            logger.warning(f"Failed to create conversations table: {e}")

        try:
            await pool.execute("""
                ALTER TABLE agent_conversations ADD COLUMN IF NOT EXISTS source VARCHAR(20) DEFAULT 'admin';
            """)
            await pool.execute("""
                ALTER TABLE agent_conversations ADD COLUMN IF NOT EXISTS owner_id VARCHAR(100);
            """)
            await pool.execute("""
                ALTER TABLE agent_conversations ADD COLUMN IF NOT EXISTS user_id VARCHAR(100);
            """)
            await pool.execute("""
                ALTER TABLE agent_conversations ADD COLUMN IF NOT EXISTS tenant_id VARCHAR(100);
            """)
            await pool.execute("""
                CREATE INDEX IF NOT EXISTS idx_agent_conv_source ON agent_conversations(source);
            """)
        except Exception:
            pass

        self._table_ready = True
        return True

    async def _ensure_feedback_table(self):
        if self._feedback_table_ready:
            return True
        pool = await self._get_pool()
        if not pool:
            return False
        try:
            await pool.execute("""
                CREATE TABLE IF NOT EXISTS message_feedback (
                    id SERIAL PRIMARY KEY,
                    conversation_id VARCHAR(50) NOT NULL,
                    message_index INT NOT NULL,
                    feedback VARCHAR(20),
                    created_at BIGINT,
                    updated_at BIGINT,
                    UNIQUE(conversation_id, message_index)
                );
            """)
            await pool.execute("""
                CREATE INDEX IF NOT EXISTS idx_feedback_conv ON message_feedback(conversation_id);
            """)
            self._feedback_table_ready = True
            return True
        except Exception as e:
            logger.warning(f"Failed to create feedback table: {e}")
            return False

    @staticmethod
    def _parse_row(row) -> dict:
        conv = dict(row)
        if isinstance(conv.get("messages"), str):
            conv["messages"] = json.loads(conv["messages"])
        conv.setdefault("owner_id", None)
        conv.setdefault("user_id", None)
        conv.setdefault("tenant_id", None)
        return conv

    @staticmethod
    def _parse_sqlite_row(row: sqlite3.Row | dict) -> dict:
        conv = dict(row)
        if isinstance(conv.get("messages"), str):
            try:
                conv["messages"] = json.loads(conv["messages"])
            except json.JSONDecodeError:
                conv["messages"] = []
        conv.setdefault("source", "admin")
        conv.setdefault("owner_id", None)
        conv.setdefault("user_id", None)
        conv.setdefault("tenant_id", None)
        return conv

    @staticmethod
    def _copy_conversation(conv: dict) -> dict:
        return deepcopy(conv)

    @staticmethod
    def _normalize_messages(messages: Optional[list]) -> Optional[list]:
        if messages is None:
            return None
        return [
            m.dict() if hasattr(m, "dict") else m
            for m in messages
        ]

    @staticmethod
    def _conversation_matches(
        conv: dict,
        workflow_id: str,
        source: Optional[str] = None,
        owner_id: Optional[str] = None,
    ) -> bool:
        if conv.get("workflow_id") != workflow_id:
            return False
        if source is not None and (conv.get("source") or "admin") != source:
            return False
        if owner_id is not None and conv.get("owner_id") != owner_id:
            return False
        return True

    def _sqlite_where(
        self,
        workflow_id: str,
        source: Optional[str] = None,
        owner_id: Optional[str] = None,
        *,
        include_conversation_id: Optional[str] = None,
    ) -> tuple[str, list[Any]]:
        clauses = []
        params: list[Any] = []
        if include_conversation_id is not None:
            clauses.append("id = ?")
            params.append(include_conversation_id)
        clauses.append("workflow_id = ?")
        params.append(workflow_id)
        if source is not None:
            clauses.append("COALESCE(source, 'admin') = ?")
            params.append(source)
        if owner_id is not None:
            clauses.append("owner_id = ?")
            params.append(owner_id)
        return " AND ".join(clauses), params

    def _list_conversations_sqlite(
        self,
        workflow_id: str,
        source: str,
        owner_id: Optional[str],
        page: int,
        page_size: int,
    ) -> Dict[str, Any]:
        if not self._ensure_sqlite():
            return self._list_conversations_memory(workflow_id, source, owner_id, page, page_size)

        offset = (page - 1) * page_size
        where, params = self._sqlite_where(workflow_id, source, owner_id)
        with self._sqlite_connection() as conn:
            total_row = conn.execute(
                f"SELECT COUNT(*) AS cnt FROM agent_conversations WHERE {where}",
                params,
            ).fetchone()
            rows = conn.execute(
                f"""
                SELECT id, workflow_id, title, messages,
                       COALESCE(source, 'admin') AS source,
                       owner_id, user_id, tenant_id,
                       created_at, updated_at
                FROM agent_conversations
                WHERE {where}
                ORDER BY updated_at DESC
                LIMIT ? OFFSET ?
                """,
                [*params, page_size, offset],
            ).fetchall()
        return {
            "conversations": [self._parse_sqlite_row(row) for row in rows],
            "total": int(total_row["cnt"] if total_row else 0),
            "page": page,
            "page_size": page_size,
        }

    def _list_conversations_memory(
        self,
        workflow_id: str,
        source: Optional[str],
        owner_id: Optional[str],
        page: int,
        page_size: int,
    ) -> Dict[str, Any]:
        rows = [
            self._copy_conversation(conv)
            for conv in self._memory_conversations.values()
            if self._conversation_matches(conv, workflow_id, source, owner_id)
        ]
        rows.sort(key=lambda conv: conv.get("updated_at") or conv.get("created_at") or 0, reverse=True)
        offset = (page - 1) * page_size
        return {
            "conversations": rows[offset:offset + page_size],
            "total": len(rows),
            "page": page,
            "page_size": page_size,
        }

    def _create_conversation_sqlite(self, conv: dict) -> dict:
        if not self._ensure_sqlite():
            self._memory_conversations[conv["id"]] = self._copy_conversation(conv)
            return conv

        with self._sqlite_connection() as conn:
            conn.execute(
                """
                INSERT INTO agent_conversations (
                    id, workflow_id, title, messages, source,
                    owner_id, user_id, tenant_id, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    conv["id"],
                    conv["workflow_id"],
                    conv["title"],
                    json.dumps(conv["messages"]),
                    conv["source"],
                    conv["owner_id"],
                    conv["user_id"],
                    conv["tenant_id"],
                    conv["created_at"],
                    conv["updated_at"],
                ),
            )
        return conv

    def _get_conversation_sqlite(
        self,
        workflow_id: str,
        conversation_id: str,
        source: Optional[str],
        owner_id: Optional[str],
    ) -> Optional[dict]:
        if not self._ensure_sqlite():
            conv = self._memory_conversations.get(conversation_id)
            if not conv or not self._conversation_matches(conv, workflow_id, source, owner_id):
                return None
            return self._copy_conversation(conv)

        where, params = self._sqlite_where(
            workflow_id,
            source,
            owner_id,
            include_conversation_id=conversation_id,
        )
        with self._sqlite_connection() as conn:
            row = conn.execute(
                f"""
                SELECT id, workflow_id, title, messages,
                       COALESCE(source, 'admin') AS source,
                       owner_id, user_id, tenant_id,
                       created_at, updated_at
                FROM agent_conversations
                WHERE {where}
                """,
                params,
            ).fetchone()
        return self._parse_sqlite_row(row) if row else None

    def _update_conversation_sqlite(
        self,
        workflow_id: str,
        conversation_id: str,
        title: Optional[str],
        messages: Optional[list],
        source: Optional[str],
        owner_id: Optional[str],
    ) -> Optional[dict]:
        if not self._ensure_sqlite():
            conv = self._memory_conversations.get(conversation_id)
            if not conv or not self._conversation_matches(conv, workflow_id, source, owner_id):
                return None

            now = int(datetime.now().timestamp() * 1000)
            if title is not None:
                conv["title"] = title
            normalized_messages = self._normalize_messages(messages)
            if normalized_messages is not None:
                conv["messages"] = normalized_messages
            conv["updated_at"] = now
            return self._copy_conversation(conv)

        now = int(datetime.now().timestamp() * 1000)
        updates = ["updated_at = ?"]
        params: list[Any] = [now]
        if title is not None:
            updates.append("title = ?")
            params.append(title)
        normalized_messages = self._normalize_messages(messages)
        if normalized_messages is not None:
            updates.append("messages = ?")
            params.append(json.dumps(normalized_messages))
        where, where_params = self._sqlite_where(
            workflow_id,
            source,
            owner_id,
            include_conversation_id=conversation_id,
        )
        with self._sqlite_connection() as conn:
            conn.execute(
                f"UPDATE agent_conversations SET {', '.join(updates)} WHERE {where}",
                [*params, *where_params],
            )
        return self._get_conversation_sqlite(workflow_id, conversation_id, source, owner_id)

    def _delete_conversation_sqlite(
        self,
        workflow_id: str,
        conversation_id: str,
        source: Optional[str],
        owner_id: Optional[str],
    ) -> bool:
        if not self._ensure_sqlite():
            conv = self._memory_conversations.get(conversation_id)
            if not conv or not self._conversation_matches(conv, workflow_id, source, owner_id):
                return False
            self._memory_conversations.pop(conversation_id, None)
            self._memory_feedback.pop(conversation_id, None)
            return True

        where, params = self._sqlite_where(
            workflow_id,
            source,
            owner_id,
            include_conversation_id=conversation_id,
        )
        with self._sqlite_connection() as conn:
            cursor = conn.execute(f"DELETE FROM agent_conversations WHERE {where}", params)
            conn.execute("DELETE FROM message_feedback WHERE conversation_id = ?", (conversation_id,))
        return cursor.rowcount > 0

    def _submit_feedback_sqlite(self, conversation_id: str, message_index: int, feedback: Optional[str]) -> bool:
        if not self._ensure_sqlite():
            if conversation_id not in self._memory_conversations:
                return False
            if feedback:
                self._memory_feedback.setdefault(conversation_id, {})[message_index] = feedback
            else:
                self._memory_feedback.get(conversation_id, {}).pop(message_index, None)
            return True

        with self._sqlite_connection() as conn:
            exists = conn.execute(
                "SELECT 1 FROM agent_conversations WHERE id = ?",
                (conversation_id,),
            ).fetchone()
            if not exists:
                return False
            if feedback:
                now = int(datetime.now().timestamp() * 1000)
                conn.execute(
                    """
                    INSERT INTO message_feedback (
                        conversation_id, message_index, feedback, created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(conversation_id, message_index)
                    DO UPDATE SET feedback = excluded.feedback, updated_at = excluded.updated_at
                    """,
                    (conversation_id, message_index, feedback, now, now),
                )
            else:
                conn.execute(
                    "DELETE FROM message_feedback WHERE conversation_id = ? AND message_index = ?",
                    (conversation_id, message_index),
                )
        return True

    def _get_feedback_sqlite(self, conversation_id: str) -> Dict[int, str]:
        if not self._ensure_sqlite():
            return dict(self._memory_feedback.get(conversation_id, {}))
        with self._sqlite_connection() as conn:
            rows = conn.execute(
                """
                SELECT message_index, feedback
                FROM message_feedback
                WHERE conversation_id = ?
                """,
                (conversation_id,),
            ).fetchall()
        return {int(row["message_index"]): row["feedback"] for row in rows}

    def _feedback_summary_map_sqlite(self, workflow_ids: list[str]) -> Dict[str, Dict[str, int]]:
        empty_map = {
            workflow_id: self._empty_feedback_summary()
            for workflow_id in workflow_ids
        }
        if not self._ensure_sqlite():
            for conv in self._memory_conversations.values():
                workflow_id = conv.get("workflow_id")
                if workflow_id not in empty_map:
                    continue
                for feedback in self._memory_feedback.get(conv.get("id"), {}).values():
                    if feedback == "like":
                        empty_map[workflow_id]["like_count"] += 1
                    elif feedback == "dislike":
                        empty_map[workflow_id]["dislike_count"] += 1
            return empty_map

        placeholders = ",".join("?" for _ in workflow_ids)
        with self._sqlite_connection() as conn:
            rows = conn.execute(
                f"""
                SELECT c.workflow_id,
                       SUM(CASE WHEN f.feedback = 'like' THEN 1 ELSE 0 END) AS like_count,
                       SUM(CASE WHEN f.feedback = 'dislike' THEN 1 ELSE 0 END) AS dislike_count
                FROM agent_conversations c
                LEFT JOIN message_feedback f ON f.conversation_id = c.id
                WHERE c.workflow_id IN ({placeholders})
                GROUP BY c.workflow_id
                """,
                workflow_ids,
            ).fetchall()
        for row in rows:
            empty_map[row["workflow_id"]] = {
                "like_count": int(row["like_count"] or 0),
                "dislike_count": int(row["dislike_count"] or 0),
            }
        return empty_map

    # ---- CRUD ----

    async def list_conversations(
        self,
        workflow_id: str,
        source: str = "admin",
        owner_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> Dict[str, Any]:
        pool = await self._get_pool()
        if not pool:
            return self._list_conversations_sqlite(workflow_id, source, owner_id, page, page_size)

        await self._ensure_table()
        offset = (page - 1) * page_size
        where = "workflow_id = $1 AND COALESCE(source, 'admin') = $2"
        params: list[Any] = [workflow_id, source]
        if owner_id is not None:
            where += " AND owner_id = $3"
            params.append(owner_id)

        try:
            total_row = await pool.fetchrow(f"""
                SELECT COUNT(*) as cnt FROM agent_conversations
                WHERE {where}
            """, *params)
            total = total_row["cnt"] if total_row else 0

            rows = await pool.fetch(f"""
                SELECT id, workflow_id, title, messages,
                       COALESCE(source, 'admin') as source,
                       owner_id, user_id, tenant_id,
                       created_at, updated_at
                FROM agent_conversations
                WHERE {where}
                ORDER BY updated_at DESC
                LIMIT ${len(params) + 1} OFFSET ${len(params) + 2}
            """, *params, page_size, offset)

            return {
                "conversations": [self._parse_row(r) for r in rows],
                "total": total,
                "page": page,
                "page_size": page_size,
            }
        except Exception as e:
            logger.warning(f"Failed to list conversations: {e}")
            return {"conversations": [], "total": 0, "page": page, "page_size": page_size}

    async def create_conversation(
        self,
        workflow_id: str,
        title: Optional[str] = None,
        source: str = "admin",
        owner_id: Optional[str] = None,
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
    ) -> dict:
        pool = await self._get_pool()
        conv_id = f"conv_{uuid.uuid4().hex[:24]}"
        now = int(datetime.now().timestamp() * 1000)

        conv = {
            "id": conv_id,
            "workflow_id": workflow_id,
            "title": title or "新会话",
            "messages": [],
            "source": source,
            "owner_id": owner_id,
            "user_id": user_id,
            "tenant_id": tenant_id,
            "created_at": now,
            "updated_at": now,
        }

        if not pool:
            return self._create_conversation_sqlite(conv)

        await self._ensure_table()
        try:
            await pool.execute("""
                INSERT INTO agent_conversations (
                    id, workflow_id, title, messages, source,
                    owner_id, user_id, tenant_id, created_at, updated_at
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            """, conv_id, workflow_id, conv["title"], json.dumps([]), source,
                owner_id, user_id, tenant_id, now, now)
        except Exception as e:
            logger.warning(f"Failed to create conversation: {e}")

        return conv

    async def get_conversation(
        self,
        workflow_id: str,
        conversation_id: str,
        source: Optional[str] = None,
        owner_id: Optional[str] = None,
    ) -> Optional[dict]:
        pool = await self._get_pool()
        if not pool:
            return self._get_conversation_sqlite(workflow_id, conversation_id, source, owner_id)

        where = "id = $1 AND workflow_id = $2"
        params = [conversation_id, workflow_id]
        if source is not None:
            where += " AND COALESCE(source, 'admin') = $3"
            params.append(source)
        if owner_id is not None:
            where += f" AND owner_id = ${len(params) + 1}"
            params.append(owner_id)

        try:
            row = await pool.fetchrow(f"""
                SELECT id, workflow_id, title, messages,
                       COALESCE(source, 'admin') as source,
                       owner_id, user_id, tenant_id,
                       created_at, updated_at
                FROM agent_conversations
                WHERE {where}
            """, *params)

            if not row:
                return None
            return self._parse_row(row)
        except Exception as e:
            logger.warning(f"Failed to get conversation: {e}")
            return None

    async def update_conversation(
        self,
        workflow_id: str,
        conversation_id: str,
        title: Optional[str] = None,
        messages: Optional[list] = None,
        source: Optional[str] = None,
        owner_id: Optional[str] = None,
    ) -> Optional[dict]:
        pool = await self._get_pool()
        if not pool:
            return self._update_conversation_sqlite(
                workflow_id,
                conversation_id,
                title,
                messages,
                source,
                owner_id,
            )

        now = int(datetime.now().timestamp() * 1000)

        updates = ["updated_at = $3"]
        params: list = [conversation_id, workflow_id, now]
        param_idx = 4

        if title is not None:
            updates.append(f"title = ${param_idx}")
            params.append(title)
            param_idx += 1

        if messages is not None:
            updates.append(f"messages = ${param_idx}")
            messages_json = json.dumps([
                m.dict() if hasattr(m, 'dict') else m
                for m in messages
            ])
            params.append(messages_json)
            param_idx += 1

        where = "id = $1 AND workflow_id = $2"
        if source is not None:
            where += f" AND COALESCE(source, 'admin') = ${param_idx}"
            params.append(source)
            param_idx += 1
        if owner_id is not None:
            where += f" AND owner_id = ${param_idx}"
            params.append(owner_id)
            param_idx += 1

        sql = f"""
            UPDATE agent_conversations
            SET {', '.join(updates)}
            WHERE {where}
            RETURNING id, workflow_id, title, messages,
                      COALESCE(source, 'admin') as source,
                      owner_id, user_id, tenant_id,
                      created_at, updated_at
        """

        try:
            row = await pool.fetchrow(sql, *params)
            if not row:
                return None
            return self._parse_row(row)
        except Exception as e:
            logger.warning(f"Failed to update conversation: {e}")
            return None

    async def delete_conversation(
        self,
        workflow_id: str,
        conversation_id: str,
        source: Optional[str] = None,
        owner_id: Optional[str] = None,
    ) -> bool:
        pool = await self._get_pool()
        if not pool:
            return self._delete_conversation_sqlite(workflow_id, conversation_id, source, owner_id)

        where = "id = $1 AND workflow_id = $2"
        params = [conversation_id, workflow_id]
        if source is not None:
            where += " AND COALESCE(source, 'admin') = $3"
            params.append(source)
        if owner_id is not None:
            where += f" AND owner_id = ${len(params) + 1}"
            params.append(owner_id)

        try:
            status = await pool.execute(f"""
                DELETE FROM agent_conversations
                WHERE {where}
            """, *params)
            return _delete_result_deleted(status)
        except Exception as e:
            logger.warning(f"Failed to delete conversation: {e}")
            return False

    # ---- Feedback ----

    async def submit_feedback(
        self, conversation_id: str, message_index: int, feedback: Optional[str]
    ) -> bool:
        pool = await self._get_pool()
        if not pool:
            return self._submit_feedback_sqlite(conversation_id, message_index, feedback)

        await self._ensure_feedback_table()
        now = int(datetime.now().timestamp() * 1000)

        try:
            if feedback:
                await pool.execute("""
                    INSERT INTO message_feedback (conversation_id, message_index, feedback, created_at, updated_at)
                    VALUES ($1, $2, $3, $4, $4)
                    ON CONFLICT (conversation_id, message_index)
                    DO UPDATE SET feedback = $3, updated_at = $4
                """, conversation_id, message_index, feedback, now)
            else:
                await pool.execute("""
                    DELETE FROM message_feedback
                    WHERE conversation_id = $1 AND message_index = $2
                """, conversation_id, message_index)
            return True
        except Exception as e:
            logger.warning(f"Failed to submit feedback: {e}")
            return False

    async def get_feedback(self, conversation_id: str) -> Dict[int, str]:
        pool = await self._get_pool()
        if not pool:
            return self._get_feedback_sqlite(conversation_id)

        await self._ensure_feedback_table()

        try:
            rows = await pool.fetch("""
                SELECT message_index, feedback
                FROM message_feedback
                WHERE conversation_id = $1
            """, conversation_id)
            return {row["message_index"]: row["feedback"] for row in rows}
        except Exception as e:
            logger.warning(f"Failed to get feedback: {e}")
            return {}

    @staticmethod
    def _empty_feedback_summary() -> Dict[str, int]:
        return {"like_count": 0, "dislike_count": 0}

    async def get_feedback_summary(self, workflow_id: str) -> Dict[str, int]:
        summary_map = await self.get_feedback_summary_map([workflow_id])
        return summary_map.get(workflow_id, self._empty_feedback_summary())

    async def get_feedback_summary_map(
        self,
        workflow_ids: List[str],
    ) -> Dict[str, Dict[str, int]]:
        workflow_ids = [workflow_id for workflow_id in workflow_ids if workflow_id]
        if not workflow_ids:
            return {}

        pool = await self._get_pool()
        empty_map = {
            workflow_id: self._empty_feedback_summary()
            for workflow_id in workflow_ids
        }
        if not pool:
            return self._feedback_summary_map_sqlite(workflow_ids)

        await self._ensure_table()
        await self._ensure_feedback_table()

        try:
            rows = await pool.fetch("""
                SELECT c.workflow_id,
                       COUNT(*) FILTER (WHERE f.feedback = 'like') AS like_count,
                       COUNT(*) FILTER (WHERE f.feedback = 'dislike') AS dislike_count
                FROM agent_conversations c
                LEFT JOIN message_feedback f ON f.conversation_id = c.id
                WHERE c.workflow_id = ANY($1::VARCHAR[])
                GROUP BY c.workflow_id
            """, workflow_ids)
            for row in rows:
                empty_map[row["workflow_id"]] = {
                    "like_count": row["like_count"] or 0,
                    "dislike_count": row["dislike_count"] or 0,
                }
            return empty_map
        except Exception as e:
            logger.warning(f"Failed to get feedback summary map: {e}")
            return empty_map


# Singleton
_conversation_service: Optional[ConversationService] = None


def get_conversation_service() -> ConversationService:
    global _conversation_service
    if _conversation_service is None:
        _conversation_service = ConversationService()
    return _conversation_service
