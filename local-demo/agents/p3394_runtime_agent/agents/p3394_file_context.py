"""SQLite-backed P3394 file context records."""

from __future__ import annotations

import os
import re
import sqlite3
import uuid
from pathlib import Path
from time import time
from typing import Any


_MEMORY_FILE_CONTEXTS: list[dict[str, Any]] = []
_TEXT_PREVIEW_TYPES = {"markdown", "text", "code", "json", "yaml"}


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
            CREATE TABLE IF NOT EXISTS p3394_file_contexts (
                id TEXT PRIMARY KEY,
                workflow_id TEXT NOT NULL,
                thread_id TEXT,
                path TEXT NOT NULL,
                display_name TEXT,
                source TEXT,
                file_type TEXT,
                mime_type TEXT,
                size INTEGER,
                status TEXT,
                preview TEXT,
                request TEXT,
                created_at INTEGER,
                updated_at INTEGER,
                UNIQUE(workflow_id, thread_id, path)
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_p3394_file_workflow ON p3394_file_contexts(workflow_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_p3394_file_updated ON p3394_file_contexts(updated_at DESC)"
        )


def _parse_row(row: sqlite3.Row | dict[str, Any]) -> dict[str, Any]:
    return dict(row)


def _normalize_path(value: Any) -> str:
    text = str(value or "").strip().strip("\"'")
    if not text:
        return ""
    try:
        return str(Path(text).expanduser().resolve())
    except Exception:
        return text


def _file_type(path: str, mime_type: str = "") -> str:
    lower_mime = mime_type.lower()
    suffix = Path(path).suffix.lower()
    if suffix in {".md", ".markdown"} or "markdown" in lower_mime:
        return "markdown"
    if suffix == ".pdf" or "pdf" in lower_mime:
        return "pdf"
    if suffix in {".doc", ".docx"} or "word" in lower_mime:
        return "document"
    if suffix in {".ppt", ".pptx"} or "presentation" in lower_mime:
        return "presentation"
    if suffix in {".xls", ".xlsx", ".csv"} or "spreadsheet" in lower_mime:
        return "spreadsheet"
    if suffix in {".json"} or "json" in lower_mime:
        return "json"
    if suffix in {".yml", ".yaml"}:
        return "yaml"
    if suffix in {
        ".py",
        ".js",
        ".ts",
        ".tsx",
        ".vue",
        ".go",
        ".rs",
        ".java",
        ".cs",
        ".cpp",
        ".c",
        ".h",
        ".css",
        ".html",
        ".sql",
        ".sh",
        ".ps1",
    }:
        return "code"
    if suffix in {".txt", ".log", ".env", ".ini", ".toml"} or lower_mime.startswith("text/"):
        return "text"
    if lower_mime.startswith("image/"):
        return "image"
    return suffix.lstrip(".") or "file"


def _preview_for(path: str, file_type: str) -> str:
    if file_type not in _TEXT_PREVIEW_TYPES:
        return ""
    try:
        value = Path(path).read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""
    return value.strip()[:500]


def _status_for(path: str) -> str:
    return "available" if Path(path).exists() else "missing"


def _extract_mentioned_paths(request: str) -> list[dict[str, Any]]:
    pattern = re.compile(r"(?P<path>(?:[A-Za-z]:[\\/]|/|\.{1,2}[\\/])[^\s\"'<>|]+)")
    items: list[dict[str, Any]] = []
    for match in pattern.finditer(request or ""):
        raw = match.group("path").rstrip(".,;，。)]}）】")
        path = _normalize_path(raw)
        if path:
            items.append(
                {
                    "path": path,
                    "display_name": Path(path).name,
                    "source": "mentioned_path",
                    "mime_type": "",
                    "size": Path(path).stat().st_size if Path(path).exists() else None,
                }
            )
    return items


def _extract_attachment_paths(state: dict[str, Any]) -> list[dict[str, Any]]:
    files = state.get("__files__") or state.get("files") or []
    if not isinstance(files, list):
        return []
    items: list[dict[str, Any]] = []
    for item in files:
        if not isinstance(item, dict):
            continue
        raw_path = item.get("path") or item.get("file_path")
        path = _normalize_path(raw_path)
        if not path:
            continue
        size = item.get("size")
        if size is None and Path(path).exists():
            size = Path(path).stat().st_size
        items.append(
            {
                "path": path,
                "display_name": str(item.get("original_name") or item.get("name") or Path(path).name),
                "source": "attachment",
                "mime_type": str(item.get("mime_type") or ""),
                "size": size,
            }
        )
    return items


def _dedupe_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_path: dict[str, dict[str, Any]] = {}
    for item in items:
        path = item.get("path")
        if not path:
            continue
        existing = by_path.get(path, {})
        by_path[path] = {**existing, **item}
    return list(by_path.values())


def _upsert_memory(item: dict[str, Any]) -> str:
    now = int(time() * 1000)
    for existing in _MEMORY_FILE_CONTEXTS:
        if (
            existing.get("workflow_id") == item["workflow_id"]
            and existing.get("thread_id") == item["thread_id"]
            and existing.get("path") == item["path"]
        ):
            existing.update(item)
            existing["updated_at"] = now
            return str(existing["id"])
    item = {
        **item,
        "id": f"p3394_file_{uuid.uuid4().hex[:24]}",
        "created_at": now,
        "updated_at": now,
    }
    _MEMORY_FILE_CONTEXTS.insert(0, item)
    return str(item["id"])


def record_p3394_file_contexts_from_state(
    *,
    workflow_id: str,
    thread_id: str,
    request: str,
    state: dict[str, Any],
) -> list[str]:
    items = _dedupe_items(_extract_attachment_paths(state) + _extract_mentioned_paths(request))
    record_ids: list[str] = []
    path = _default_sqlite_path()
    now = int(time() * 1000)

    for raw in items:
        item_path = str(raw["path"])
        mime_type = str(raw.get("mime_type") or "")
        file_type = _file_type(item_path, mime_type)
        item = {
            "workflow_id": workflow_id,
            "thread_id": thread_id,
            "path": item_path,
            "display_name": str(raw.get("display_name") or Path(item_path).name),
            "source": str(raw.get("source") or "unknown"),
            "file_type": file_type,
            "mime_type": mime_type,
            "size": raw.get("size"),
            "status": _status_for(item_path),
            "preview": _preview_for(item_path, file_type),
            "request": request,
        }
        if not path:
            record_ids.append(_upsert_memory(item))
            continue

        _ensure_schema(path)
        with _connect(path) as conn:
            existing = conn.execute(
                """
                SELECT id, created_at FROM p3394_file_contexts
                WHERE workflow_id = ? AND thread_id = ? AND path = ?
                """,
                (workflow_id, thread_id, item_path),
            ).fetchone()
            if existing:
                record_id = str(existing["id"])
                created_at = int(existing["created_at"] or now)
                conn.execute(
                    """
                    UPDATE p3394_file_contexts
                    SET display_name = ?, source = ?, file_type = ?, mime_type = ?, size = ?,
                        status = ?, preview = ?, request = ?, created_at = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        item["display_name"],
                        item["source"],
                        item["file_type"],
                        item["mime_type"],
                        item["size"],
                        item["status"],
                        item["preview"],
                        item["request"],
                        created_at,
                        now,
                        record_id,
                    ),
                )
            else:
                record_id = f"p3394_file_{uuid.uuid4().hex[:24]}"
                conn.execute(
                    """
                    INSERT INTO p3394_file_contexts (
                        id, workflow_id, thread_id, path, display_name, source, file_type,
                        mime_type, size, status, preview, request, created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record_id,
                        workflow_id,
                        thread_id,
                        item["path"],
                        item["display_name"],
                        item["source"],
                        item["file_type"],
                        item["mime_type"],
                        item["size"],
                        item["status"],
                        item["preview"],
                        item["request"],
                        now,
                        now,
                    ),
                )
            record_ids.append(record_id)
    return record_ids


def list_p3394_file_contexts(workflow_id: str, limit: int = 50) -> list[dict[str, Any]]:
    path = _default_sqlite_path()
    if not path or not path.exists():
        return [
            item
            for item in _MEMORY_FILE_CONTEXTS
            if item.get("workflow_id") == workflow_id
        ][:limit]

    _ensure_schema(path)
    with _connect(path) as conn:
        rows = conn.execute(
            """
            SELECT id, workflow_id, thread_id, path, display_name, source, file_type,
                   mime_type, size, status, preview, request, created_at, updated_at
            FROM p3394_file_contexts
            WHERE workflow_id = ?
            ORDER BY updated_at DESC
            LIMIT ?
            """,
            (workflow_id, limit),
        ).fetchall()
    return [_parse_row(row) for row in rows]
