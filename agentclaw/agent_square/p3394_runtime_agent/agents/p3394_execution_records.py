"""SQLite-backed P3394 execution records."""

from __future__ import annotations

import json
import os
import sqlite3
import uuid
from pathlib import Path
from time import time
from typing import Any


_MEMORY_EXECUTION_RECORDS: list[dict[str, Any]] = []


def _default_sqlite_path() -> Path | None:
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


def _connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_schema(path: Path) -> None:
    with _connect(path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS p3394_execution_records (
                id TEXT PRIMARY KEY,
                workflow_id TEXT NOT NULL,
                thread_id TEXT,
                task_history_id TEXT,
                request TEXT,
                route TEXT,
                status TEXT,
                answer_preview TEXT,
                role_statuses TEXT,
                created_at INTEGER,
                updated_at INTEGER,
                completed_at INTEGER
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_p3394_exec_workflow ON p3394_execution_records(workflow_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_p3394_exec_thread ON p3394_execution_records(thread_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_p3394_exec_updated ON p3394_execution_records(updated_at DESC)"
        )


def _parse_row(row: sqlite3.Row | dict[str, Any]) -> dict[str, Any]:
    item = dict(row)
    for key, fallback in (("route", {}), ("role_statuses", [])):
        if isinstance(item.get(key), str):
            try:
                item[key] = json.loads(item[key])
            except json.JSONDecodeError:
                item[key] = fallback
    return item


def record_p3394_execution_record(
    *,
    workflow_id: str,
    thread_id: str,
    task_history_id: str,
    request: str,
    route: dict[str, Any],
    status: str,
) -> str:
    record_id = f"p3394_exec_{uuid.uuid4().hex[:24]}"
    now = int(time() * 1000)
    item = {
        "id": record_id,
        "workflow_id": workflow_id,
        "thread_id": thread_id,
        "task_history_id": task_history_id,
        "request": request,
        "route": route,
        "status": status,
        "answer_preview": "",
        "role_statuses": [],
        "created_at": now,
        "updated_at": now,
        "completed_at": None,
    }
    path = _default_sqlite_path()
    if not path:
        _MEMORY_EXECUTION_RECORDS.insert(0, item)
        return record_id

    _ensure_schema(path)
    with _connect(path) as conn:
        conn.execute(
            """
            INSERT INTO p3394_execution_records (
                id, workflow_id, thread_id, task_history_id, request, route, status,
                answer_preview, role_statuses, created_at, updated_at, completed_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record_id,
                workflow_id,
                thread_id,
                task_history_id,
                request,
                json.dumps(route),
                status,
                "",
                json.dumps([]),
                now,
                now,
                None,
            ),
        )
    return record_id


def complete_p3394_execution_record(
    *,
    record_id: str,
    workflow_id: str,
    answer_preview: str,
    role_statuses: list[str],
    status: str,
) -> bool:
    now = int(time() * 1000)
    path = _default_sqlite_path()
    if not path:
        for item in _MEMORY_EXECUTION_RECORDS:
            if item.get("id") == record_id and item.get("workflow_id") == workflow_id:
                item["answer_preview"] = answer_preview
                item["role_statuses"] = role_statuses
                item["status"] = status
                item["updated_at"] = now
                item["completed_at"] = now
                return True
        return False

    _ensure_schema(path)
    with _connect(path) as conn:
        cursor = conn.execute(
            """
            UPDATE p3394_execution_records
            SET answer_preview = ?, role_statuses = ?, status = ?, updated_at = ?, completed_at = ?
            WHERE id = ? AND workflow_id = ?
            """,
            (
                answer_preview,
                json.dumps(role_statuses),
                status,
                now,
                now,
                record_id,
                workflow_id,
            ),
        )
        return cursor.rowcount > 0


def get_latest_p3394_execution_record_for_thread(
    *,
    workflow_id: str,
    thread_id: str,
) -> dict[str, Any] | None:
    path = _default_sqlite_path()
    if not path or not path.exists():
        for item in _MEMORY_EXECUTION_RECORDS:
            if item.get("workflow_id") == workflow_id and item.get("thread_id") == thread_id:
                return item
        return None

    _ensure_schema(path)
    with _connect(path) as conn:
        row = conn.execute(
            """
            SELECT id, workflow_id, thread_id, task_history_id, request, route, status,
                   answer_preview, role_statuses, created_at, updated_at, completed_at
            FROM p3394_execution_records
            WHERE workflow_id = ? AND thread_id = ?
            ORDER BY updated_at DESC
            LIMIT 1
            """,
            (workflow_id, thread_id),
        ).fetchone()
    return _parse_row(row) if row else None


def list_p3394_execution_records(workflow_id: str, limit: int = 50) -> list[dict[str, Any]]:
    path = _default_sqlite_path()
    if not path or not path.exists():
        return [
            item
            for item in _MEMORY_EXECUTION_RECORDS
            if item.get("workflow_id") == workflow_id
        ][:limit]

    _ensure_schema(path)
    with _connect(path) as conn:
        rows = conn.execute(
            """
            SELECT id, workflow_id, thread_id, task_history_id, request, route, status,
                   answer_preview, role_statuses, created_at, updated_at, completed_at
            FROM p3394_execution_records
            WHERE workflow_id = ?
            ORDER BY updated_at DESC
            LIMIT ?
            """,
            (workflow_id, limit),
        ).fetchall()
    return [_parse_row(row) for row in rows]
