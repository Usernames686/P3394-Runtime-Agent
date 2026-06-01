"""P3394 file artifact discovery from runtime records."""

from __future__ import annotations

import re
import os
import subprocess
from pathlib import Path
from typing import Any

from agentclaw.agent_square.p3394_runtime_agent.agents.p3394_tool_records import (
    list_p3394_tool_records,
)


_TEXT_PREVIEW_TYPES = {"markdown", "text", "code", "json", "yaml", "csv"}
_PATH_PATTERN = re.compile(
    r"(?P<path>[A-Za-z]:[\\/][^\r\n\"'<>|]+|/(?:[^\s\"'<>|]+/)+[^\s\"'<>|]+)"
)
_RUN_LOG_HINTS = (
    "pytest",
    "npm test",
    "npm run build",
    "pnpm test",
    "pnpm build",
    "vitest",
    "ruff",
    "mypy",
    "passed",
    "failed",
    "ran ",
)


def _normalize_path(value: Any) -> str:
    text = str(value or "").strip().strip("\"'")
    text = text.rstrip(".,;:)]}")
    if not text:
        return ""
    try:
        return str(Path(text).expanduser().resolve())
    except Exception:
        return text


def _file_type(path: str) -> str:
    if Path(path).is_dir():
        return "folder"
    suffix = Path(path).suffix.lower()
    if suffix in {".md", ".markdown"}:
        return "markdown"
    if suffix == ".pdf":
        return "pdf"
    if suffix in {".doc", ".docx"}:
        return "document"
    if suffix in {".ppt", ".pptx"}:
        return "presentation"
    if suffix in {".xls", ".xlsx", ".csv"}:
        return "spreadsheet" if suffix != ".csv" else "csv"
    if suffix == ".json":
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
    if suffix in {".txt", ".log", ".env", ".ini", ".toml"}:
        return "text"
    return suffix.lstrip(".") or "file"


def _preview_for(path: str, file_type: str) -> str:
    if file_type == "folder":
        try:
            names = sorted(item.name for item in Path(path).iterdir())[:20]
        except Exception:
            return ""
        return "\n".join(names)
    if file_type not in _TEXT_PREVIEW_TYPES:
        return ""
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace").strip()[:800]
    except Exception:
        return ""


def _candidate_paths_from_record(record: dict[str, Any]) -> list[str]:
    chunks = [
        record.get("command"),
        record.get("stdout"),
        record.get("stderr"),
        record.get("result_preview"),
        record.get("raw_result"),
    ]
    paths: list[str] = []
    for chunk in chunks:
        text = str(chunk or "")
        for match in _PATH_PATTERN.finditer(text):
            path = _normalize_path(match.group("path"))
            if path and path not in paths:
                paths.append(path)
    return paths


def _record_has_run_log(record: dict[str, Any]) -> bool:
    command = str(record.get("command") or "").lower()
    output = "\n".join(
        str(record.get(key) or "")
        for key in ("stdout", "stderr", "result_preview", "raw_result")
    ).lower()
    command_patterns = (
        r"(^|[;&|]\s*|\s)(pytest|vitest|ruff|mypy)(\s|$)",
        r"\bnpm\s+(test|run\s+build)\b",
        r"\bpnpm\s+(test|build)\b",
    )
    if any(re.search(pattern, command) for pattern in command_patterns):
        return True
    return bool(re.search(r"\b\d+\s+(passed|failed)\b", output) or re.search(r"\bran\s+\w+", output))


def _run_log_artifact(record: dict[str, Any], workflow_id: str) -> dict[str, Any] | None:
    if not _record_has_run_log(record):
        return None
    preview_parts = [
        f"$ {record.get('command') or record.get('tool_name') or 'tool'}",
        str(record.get("stdout") or "").strip(),
        str(record.get("stderr") or "").strip(),
        f"exit_code={record.get('exit_code')}" if record.get("exit_code") is not None else "",
    ]
    preview = "\n".join(part for part in preview_parts if part).strip()
    if not preview:
        return None
    record_id = record.get("id") or "tool"
    return {
        "id": f"{record_id}::run_log",
        "workflow_id": workflow_id,
        "thread_id": record.get("thread_id") or "",
        "task_id": record.get("task_id") or "",
        "tool_record_id": record_id,
        "path": "",
        "display_name": f"{record.get('tool_name') or 'tool'} run log",
        "file_type": "run_log",
        "size": len(preview.encode("utf-8")),
        "status": record.get("status") or "available",
        "preview": preview[:1200],
        "source": "tool_record",
        "command": record.get("command") or "",
        "created_at": record.get("created_at"),
        "updated_at": record.get("updated_at") or record.get("created_at"),
    }


def _open_path_for_os(path: Path) -> None:
    if os.name == "nt":
        os.startfile(str(path))  # type: ignore[attr-defined]
        return
    opener = "open" if sys_platform() == "darwin" else "xdg-open"
    subprocess.Popen([opener, str(path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def sys_platform() -> str:
    import sys

    return sys.platform


def open_p3394_artifact_path(path: str) -> dict[str, Any]:
    target = Path(str(path or "").strip().strip("\"'")).expanduser().resolve()
    if not target.exists():
        return {"success": False, "path": str(target), "error": "path_not_found"}
    _open_path_for_os(target)
    return {
        "success": True,
        "path": str(target),
        "kind": "folder" if target.is_dir() else "file",
    }


def list_p3394_artifacts(workflow_id: str, limit: int = 50) -> list[dict[str, Any]]:
    """Return file artifacts inferred from successful P3394 tool calls."""
    records = list_p3394_tool_records(workflow_id=workflow_id, limit=max(limit * 20, 200))
    by_path: dict[str, dict[str, Any]] = {}
    for record in records:
        run_log = _run_log_artifact(record, workflow_id)
        if run_log:
            by_path[run_log["id"]] = run_log
        for path in _candidate_paths_from_record(record):
            artifact_path = Path(path)
            if not artifact_path.exists():
                continue
            file_type = _file_type(path)
            item = {
                "id": f"{record.get('id', 'tool')}::{path}",
                "workflow_id": workflow_id,
                "thread_id": record.get("thread_id") or "",
                "task_id": record.get("task_id") or "",
                "tool_record_id": record.get("id") or "",
                "path": path,
                "display_name": artifact_path.name,
                "file_type": file_type,
                "size": artifact_path.stat().st_size if artifact_path.is_file() else None,
                "status": "available",
                "preview": _preview_for(path, file_type),
                "source": "tool_record",
                "command": record.get("command") or "",
                "created_at": record.get("created_at"),
                "updated_at": record.get("updated_at") or record.get("created_at"),
            }
            existing = by_path.get(path)
            if not existing or (item.get("updated_at") or 0) >= (existing.get("updated_at") or 0):
                by_path[path] = item

    return sorted(
        by_path.values(),
        key=lambda item: item.get("updated_at") or 0,
        reverse=True,
    )[:limit]
