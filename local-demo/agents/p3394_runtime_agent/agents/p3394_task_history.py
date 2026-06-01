"""SQLite-backed P3394 task history."""

from __future__ import annotations

import json
import os
import sqlite3
import uuid
from pathlib import Path
from time import time
from typing import Any


_MEMORY_TASK_HISTORY: list[dict[str, Any]] = []


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
            CREATE TABLE IF NOT EXISTS p3394_task_history (
                id TEXT PRIMARY KEY,
                workflow_id TEXT NOT NULL,
                thread_id TEXT,
                request TEXT,
                route TEXT,
                role_plan TEXT,
                status TEXT,
                created_at INTEGER,
                updated_at INTEGER
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_p3394_task_workflow ON p3394_task_history(workflow_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_p3394_task_updated ON p3394_task_history(updated_at DESC)"
        )


def _parse_row(row: sqlite3.Row | dict[str, Any]) -> dict[str, Any]:
    item = dict(row)
    for key in ("route", "role_plan"):
        if isinstance(item.get(key), str):
            try:
                item[key] = json.loads(item[key])
            except json.JSONDecodeError:
                item[key] = [] if key == "role_plan" else {}
    return item


def record_p3394_task_history(
    *,
    workflow_id: str,
    thread_id: str,
    request: str,
    route: dict[str, Any],
    role_plan: list[dict[str, Any]],
    status: str,
) -> str:
    history_id = f"p3394_task_{uuid.uuid4().hex[:24]}"
    now = int(time() * 1000)
    item = {
        "id": history_id,
        "workflow_id": workflow_id,
        "thread_id": thread_id,
        "request": request,
        "route": route,
        "role_plan": role_plan,
        "status": status,
        "created_at": now,
        "updated_at": now,
    }
    path = _default_sqlite_path()
    if not path:
        _MEMORY_TASK_HISTORY.insert(0, item)
        return history_id

    _ensure_schema(path)
    with _connect(path) as conn:
        conn.execute(
            """
            INSERT INTO p3394_task_history (
                id, workflow_id, thread_id, request, route, role_plan, status, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                history_id,
                workflow_id,
                thread_id,
                request,
                json.dumps(route),
                json.dumps(role_plan),
                status,
                now,
                now,
            ),
        )
    return history_id


def update_p3394_task_history(
    *,
    history_id: str,
    workflow_id: str,
    role_plan: list[dict[str, Any]] | None = None,
    status: str | None = None,
) -> bool:
    now = int(time() * 1000)
    path = _default_sqlite_path()
    if not path:
        for item in _MEMORY_TASK_HISTORY:
            if item.get("id") == history_id and item.get("workflow_id") == workflow_id:
                if role_plan is not None:
                    item["role_plan"] = role_plan
                if status is not None:
                    item["status"] = status
                item["updated_at"] = now
                return True
        return False

    _ensure_schema(path)
    assignments: list[str] = []
    params: list[Any] = []
    if role_plan is not None:
        assignments.append("role_plan = ?")
        params.append(json.dumps(role_plan))
    if status is not None:
        assignments.append("status = ?")
        params.append(status)
    if not assignments:
        return False

    assignments.append("updated_at = ?")
    params.extend([now, history_id, workflow_id])
    with _connect(path) as conn:
        cursor = conn.execute(
            f"""
            UPDATE p3394_task_history
            SET {", ".join(assignments)}
            WHERE id = ? AND workflow_id = ?
            """,
            params,
        )
        return cursor.rowcount > 0


def get_latest_p3394_task_history_for_thread(
    *,
    workflow_id: str,
    thread_id: str,
) -> dict[str, Any] | None:
    path = _default_sqlite_path()
    if not path or not path.exists():
        for item in _MEMORY_TASK_HISTORY:
            if item.get("workflow_id") == workflow_id and item.get("thread_id") == thread_id:
                return item
        return None

    _ensure_schema(path)
    with _connect(path) as conn:
        row = conn.execute(
            """
            SELECT id, workflow_id, thread_id, request, route, role_plan, status, created_at, updated_at
            FROM p3394_task_history
            WHERE workflow_id = ? AND thread_id = ?
            ORDER BY updated_at DESC
            LIMIT 1
            """,
            (workflow_id, thread_id),
        ).fetchone()
    return _parse_row(row) if row else None


def list_p3394_task_history(workflow_id: str, limit: int = 50) -> list[dict[str, Any]]:
    path = _default_sqlite_path()
    if not path or not path.exists():
        return [
            item
            for item in _MEMORY_TASK_HISTORY
            if item.get("workflow_id") == workflow_id
        ][:limit]

    _ensure_schema(path)
    with _connect(path) as conn:
        rows = conn.execute(
            """
            SELECT id, workflow_id, thread_id, request, route, role_plan, status, created_at, updated_at
            FROM p3394_task_history
            WHERE workflow_id = ?
            ORDER BY updated_at DESC
            LIMIT ?
            """,
            (workflow_id, limit),
        ).fetchall()
    return [_parse_row(row) for row in rows]
