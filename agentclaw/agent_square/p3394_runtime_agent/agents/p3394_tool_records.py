"""SQLite-backed P3394 tool call records."""

from __future__ import annotations

import json
import os
import re
import sqlite3
import uuid
from pathlib import Path
from time import time
from typing import Any


_MEMORY_TOOL_RECORDS: list[dict[str, Any]] = []


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
            CREATE TABLE IF NOT EXISTS p3394_tool_records (
                id TEXT PRIMARY KEY,
                workflow_id TEXT NOT NULL,
                thread_id TEXT,
                task_id TEXT,
                message_id TEXT,
                tool_call_id TEXT,
                tool_name TEXT,
                tool_arguments TEXT,
                command TEXT,
                cwd TEXT,
                stdout TEXT,
                stderr TEXT,
                exit_code INTEGER,
                status TEXT,
                result_preview TEXT,
                raw_result TEXT,
                duration_ms REAL,
                batch_id TEXT,
                node_id TEXT,
                created_at INTEGER,
                updated_at INTEGER
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_p3394_tool_workflow ON p3394_tool_records(workflow_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_p3394_tool_thread ON p3394_tool_records(thread_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_p3394_tool_updated ON p3394_tool_records(updated_at DESC)"
        )


def _json_dumps(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, default=str)
    except Exception:
        return str(value)


def _stringify(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return _json_dumps(value)


def _parse_json_like(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        return value
    text = _stringify(value).strip()
    if not text or text[0] not in "{[":
        return text
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def _first_string(source: Any, keys: list[str]) -> str:
    if not isinstance(source, dict):
        return ""
    for key in keys:
        value = source.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.rstrip()
    return _json_dumps(value)


def _parse_exit_code(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _strip_exit_line(text: str) -> str:
    return re.sub(r"(?im)\r?\n?\s*exit code\s+-?\d+\s*$", "", text).rstrip()


def _split_marked_shell_output(value: Any) -> dict[str, Any]:
    output = _stringify(value).strip()
    exit_matches = list(re.finditer(r"(?im)^\s*exit code\s+(-?\d+)\s*$", output))
    exit_code = int(exit_matches[-1].group(1)) if exit_matches else None
    marker_pattern = re.compile(r"(?im)^\[(stdout|stderr)\]\s*$")
    markers = list(marker_pattern.finditer(output))

    if not markers:
        cleaned = _strip_exit_line(output)
        if re.match(r"^\[ERROR\]", cleaned, flags=re.IGNORECASE):
            return {
                "stdout": "",
                "stderr": re.sub(r"^\[ERROR\]\s*", "", cleaned, flags=re.IGNORECASE).strip(),
                "exit_code": exit_code,
            }
        return {
            "stdout": "" if cleaned == "(no output)" else cleaned,
            "stderr": "",
            "exit_code": exit_code,
        }

    parts = {"stdout": "", "stderr": ""}
    for index, marker in enumerate(markers):
        key = marker.group(1).lower()
        start = marker.end()
        end = markers[index + 1].start() if index + 1 < len(markers) else len(output)
        section = _strip_exit_line(output[start:end].strip("\r\n"))
        parts[key] = f"{parts[key]}\n{section}".strip() if parts[key] else section

    prefix = output[: markers[0].start()].strip()
    if prefix and re.match(r"^\[ERROR\]", prefix, flags=re.IGNORECASE) and not parts["stderr"]:
        parts["stderr"] = re.sub(r"^\[ERROR\]\s*", "", prefix, flags=re.IGNORECASE).strip()

    return {**parts, "exit_code": exit_code}


def normalize_p3394_tool_record_payload(
    *,
    tool_name: str,
    tool_arguments: Any,
    tool_result: Any,
    status: str,
) -> dict[str, Any]:
    args = _parse_json_like(tool_arguments)
    result = _parse_json_like(tool_result)
    command = _first_string(args, ["command", "cmd", "script"])
    cwd = _first_string(args, ["cwd", "working_dir", "workdir", "workingDirectory"])

    stdout = ""
    stderr = ""
    exit_code = None
    if isinstance(result, dict):
        stdout = _normalize_text(result.get("stdout") or result.get("output") or result.get("result"))
        stderr = _normalize_text(result.get("stderr") or result.get("error"))
        exit_code = _parse_exit_code(
            result.get("exit_code")
            or result.get("exitCode")
            or result.get("returncode")
            or result.get("return_code")
            or result.get("code")
        )
    else:
        split = _split_marked_shell_output(result if result else tool_result)
        stdout = split["stdout"]
        stderr = split["stderr"]
        exit_code = split["exit_code"]

    raw_result = _stringify(tool_result)
    return {
        "tool_name": str(tool_name or ""),
        "tool_arguments": _json_dumps(args) if isinstance(args, (dict, list)) else _stringify(tool_arguments),
        "command": command or str(tool_name or "tool"),
        "cwd": cwd,
        "stdout": stdout,
        "stderr": stderr,
        "exit_code": exit_code,
        "status": str(status or "unknown"),
        "result_preview": " ".join(raw_result.split())[:500],
        "raw_result": raw_result,
    }


def _parse_row(row: sqlite3.Row | dict[str, Any]) -> dict[str, Any]:
    item = dict(row)
    if isinstance(item.get("tool_arguments"), str):
        try:
            item["tool_arguments"] = json.loads(item["tool_arguments"])
        except json.JSONDecodeError:
            pass
    return item


def record_p3394_tool_record(
    *,
    workflow_id: str,
    thread_id: str,
    task_id: str = "",
    message_id: str = "",
    tool_call_id: str = "",
    tool_name: str,
    tool_arguments: Any,
    tool_result: Any,
    status: str,
    duration_ms: float | None = None,
    batch_id: str = "",
    node_id: str = "",
) -> str:
    record_id = f"p3394_tool_{uuid.uuid4().hex[:24]}"
    now = int(time() * 1000)
    normalized = normalize_p3394_tool_record_payload(
        tool_name=tool_name,
        tool_arguments=tool_arguments,
        tool_result=tool_result,
        status=status,
    )
    item = {
        "id": record_id,
        "workflow_id": workflow_id,
        "thread_id": thread_id,
        "task_id": task_id,
        "message_id": message_id,
        "tool_call_id": tool_call_id,
        **normalized,
        "duration_ms": duration_ms,
        "batch_id": batch_id,
        "node_id": node_id,
        "created_at": now,
        "updated_at": now,
    }
    path = _default_sqlite_path()
    if not path:
        _MEMORY_TOOL_RECORDS.insert(0, item)
        return record_id

    _ensure_schema(path)
    with _connect(path) as conn:
        conn.execute(
            """
            INSERT INTO p3394_tool_records (
                id, workflow_id, thread_id, task_id, message_id, tool_call_id,
                tool_name, tool_arguments, command, cwd, stdout, stderr, exit_code,
                status, result_preview, raw_result, duration_ms, batch_id, node_id,
                created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record_id,
                workflow_id,
                thread_id,
                task_id,
                message_id,
                tool_call_id,
                item["tool_name"],
                item["tool_arguments"],
                item["command"],
                item["cwd"],
                item["stdout"],
                item["stderr"],
                item["exit_code"],
                item["status"],
                item["result_preview"],
                item["raw_result"],
                item["duration_ms"],
                item["batch_id"],
                item["node_id"],
                now,
                now,
            ),
        )
    return record_id


def list_p3394_tool_records(workflow_id: str, limit: int = 50) -> list[dict[str, Any]]:
    path = _default_sqlite_path()
    if not path or not path.exists():
        return [
            item
            for item in _MEMORY_TOOL_RECORDS
            if item.get("workflow_id") == workflow_id
        ][:limit]

    _ensure_schema(path)
    with _connect(path) as conn:
        rows = conn.execute(
            """
            SELECT id, workflow_id, thread_id, task_id, message_id, tool_call_id,
                   tool_name, tool_arguments, command, cwd, stdout, stderr, exit_code,
                   status, result_preview, raw_result, duration_ms, batch_id, node_id,
                   created_at, updated_at
            FROM p3394_tool_records
            WHERE workflow_id = ?
            ORDER BY updated_at DESC
            LIMIT ?
            """,
            (workflow_id, limit),
        ).fetchall()
    return [_parse_row(row) for row in rows]
