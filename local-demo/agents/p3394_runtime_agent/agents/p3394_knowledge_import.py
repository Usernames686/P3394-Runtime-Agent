"""Import local files into the P3394 local knowledge and graph stores."""

from __future__ import annotations

import os
import re
import shutil
import uuid
import zipfile
from pathlib import Path
from typing import Any

from agentclaw.agent_square.p3394_runtime_agent.agents.p3394_file_context import (
    record_p3394_file_contexts_from_state,
)
from agentclaw.agent_square.p3394_runtime_agent.agents.p3394_local_memory import (
    add_p3394_knowledge_item,
    add_p3394_memory_relation,
)


_SUPPORTED_SUFFIXES = {
    ".md": "markdown",
    ".markdown": "markdown",
    ".txt": "text",
    ".log": "text",
    ".json": "json",
    ".yml": "yaml",
    ".yaml": "yaml",
    ".csv": "csv",
    ".pdf": "pdf",
    ".docx": "document",
    ".doc": "document",
}
_TEXT_SUFFIXES = {".md", ".markdown", ".txt", ".log", ".json", ".yml", ".yaml", ".csv"}


def _default_upload_dir() -> Path:
    explicit = os.getenv("AGENTCLAW_P3394_IMPORT_UPLOAD_DIR", "").strip()
    if explicit:
        return Path(explicit).expanduser().resolve()
    project_dir = os.getenv("AGENTCLAW_PROJECT_DIR", "").strip()
    if project_dir:
        return Path(project_dir).expanduser().resolve() / ".agentclaw" / "p3394-imports"
    return Path.cwd() / ".agentclaw" / "p3394-imports"


def _resolve_path(value: str) -> Path | None:
    text = str(value or "").strip().strip("\"'")
    if not text:
        return None
    try:
        return Path(text).expanduser().resolve()
    except Exception:
        return None


def _collect_files(paths: list[str], recursive: bool, max_files: int) -> tuple[list[Path], list[dict[str, Any]]]:
    files: list[Path] = []
    skipped: list[dict[str, Any]] = []
    for raw in paths:
        path = _resolve_path(raw)
        if not path or not path.exists():
            skipped.append({"path": str(raw), "reason": "missing"})
            continue
        candidates = []
        if path.is_file():
            candidates = [path]
        elif path.is_dir():
            iterator = path.rglob("*") if recursive else path.glob("*")
            candidates = [item for item in iterator if item.is_file()]
        for candidate in candidates:
            if len(files) >= max_files:
                skipped.append({"path": str(candidate), "reason": "max_files_reached"})
                continue
            if candidate.suffix.lower() not in _SUPPORTED_SUFFIXES:
                skipped.append({"path": str(candidate), "reason": "unsupported_type"})
                continue
            if candidate not in files:
                files.append(candidate)
    return files, skipped


def _read_text_content(path: Path, max_chars: int) -> tuple[str, str]:
    suffix = path.suffix.lower()
    if suffix in _TEXT_SUFFIXES:
        try:
            return path.read_text(encoding="utf-8", errors="replace")[:max_chars], ""
        except Exception as exc:
            return "", f"read_failed: {exc}"

    if suffix == ".pdf":
        try:
            from pdfminer.high_level import extract_text

            return extract_text(str(path))[:max_chars], ""
        except Exception as exc:
            return "", f"pdf_preview_unavailable: {exc}"

    if suffix == ".docx":
        try:
            with zipfile.ZipFile(path) as archive:
                xml = archive.read("word/document.xml").decode("utf-8", errors="replace")
            text = re.sub(r"<[^>]+>", " ", xml)
            text = re.sub(r"\s+", " ", text).strip()
            return text[:max_chars], ""
        except Exception as exc:
            return "", f"docx_preview_unavailable: {exc}"

    return (
        f"{path.name}\n\nImported file path: {path}\nBinary document indexed by path and metadata.",
        "",
    )


def _summarize_content(title: str, content: str, file_type: str) -> str:
    cleaned = re.sub(r"\s+", " ", content or "").strip()
    if not cleaned:
        return f"{title} ({file_type})"
    sentences = re.split(r"(?<=[.!?。！？])\s+", cleaned)
    selected: list[str] = []
    for sentence in sentences:
        if sentence and sentence not in selected:
            selected.append(sentence)
        if len(" ".join(selected)) >= 220:
            break
    summary = " ".join(selected).strip() or cleaned[:260]
    return summary[:420]


def _knowledge_content(summary: str, content: str) -> str:
    body = content.strip()
    if len(body) > 20000:
        body = body[:20000]
    return f"Summary: {summary}\n\nSource content:\n{body}"


def stage_p3394_uploaded_file(filename: str, source_path: Path | None = None) -> Path:
    safe_name = Path(filename or source_path.name).name
    target_dir = _default_upload_dir() / uuid.uuid4().hex[:12]
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / safe_name
    if source_path and source_path.exists():
        shutil.copyfile(source_path, target)
    return target


def import_p3394_local_knowledge(
    *,
    workflow_id: str,
    paths: list[str],
    recursive: bool = True,
    max_files: int = 50,
    max_chars: int = 12000,
    source_mode: str = "local_path",
) -> dict[str, Any]:
    files, skipped = _collect_files(paths, recursive=recursive, max_files=max_files)
    items: list[dict[str, Any]] = []
    contexts: list[str] = []
    for path in files:
        content, warning = _read_text_content(path, max_chars=max_chars)
        file_type = _SUPPORTED_SUFFIXES.get(path.suffix.lower(), "file")
        if not content.strip():
            skipped.append({"path": str(path), "reason": warning or "empty"})
            continue
        summary = _summarize_content(path.name, content, file_type)

        item = add_p3394_knowledge_item(
            workflow_id=workflow_id,
            title=path.name,
            content=_knowledge_content(summary, content),
            source="local_knowledge_import",
            tags=["local-kb", "imported", file_type],
            metadata={
                "path": str(path),
                "file_type": file_type,
                "size": path.stat().st_size,
                "warning": warning,
                "summary": summary,
                "source_mode": source_mode,
            },
        )
        items.append(item)
        contexts.extend(
            record_p3394_file_contexts_from_state(
                workflow_id=workflow_id,
                thread_id="knowledge-import",
                request=f"import local knowledge {path}",
                state={},
            )
        )
        add_p3394_memory_relation(
            workflow_id=workflow_id,
            source_label="本地知识库",
            source_kind="capability",
            relation="contains",
            target_label=path.name,
            target_kind="document",
            evidence=str(path),
            weight=0.9,
        )

    return {
        "success": True,
        "workflow_id": workflow_id,
        "imported_count": len(items),
        "skipped_count": len(skipped),
        "items": items,
        "skipped": skipped,
        "file_context_ids": contexts,
    }
