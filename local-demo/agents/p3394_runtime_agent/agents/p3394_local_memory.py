"""SQLite-backed local knowledge base and memory graph for P3394."""

from __future__ import annotations

import json
import os
import re
import sqlite3
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path
from time import time
from typing import Any


_MEMORY_KNOWLEDGE_ITEMS: list[dict[str, Any]] = []
_MEMORY_GRAPH_NODES: list[dict[str, Any]] = []
_MEMORY_GRAPH_EDGES: list[dict[str, Any]] = []
_MEMORY_DAILY_NOTES: list[dict[str, Any]] = []


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


def _default_daily_memory_dir() -> Path | None:
    explicit = os.getenv("AGENTCLAW_P3394_MEMORY_DIR", "").strip()
    if explicit:
        return Path(explicit).expanduser().resolve()

    data_dir = os.getenv("AGENTCLAW_DATA_DIR", "").strip()
    if data_dir:
        return (Path(data_dir).expanduser() / "p3394-memory").resolve()

    project_dir = os.getenv("AGENTCLAW_PROJECT_DIR", "").strip()
    if project_dir:
        return (Path(project_dir).expanduser() / ".agentclaw" / "p3394-memory").resolve()

    return None


def _connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    return conn


def _dump_json(value: Any) -> str:
    return json.dumps(value or {}, ensure_ascii=False)


def _load_json(value: Any, fallback: Any) -> Any:
    if not isinstance(value, str) or not value:
        return fallback
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return fallback


def _now_ms() -> int:
    return int(time() * 1000)


def _today_key() -> str:
    return datetime.now().date().isoformat()


def _parse_date_key(value: str | None) -> date:
    if not value:
        return datetime.now().date()
    try:
        return date.fromisoformat(value)
    except ValueError:
        return datetime.now().date()


def _clock_label() -> str:
    return datetime.now().strftime("%H:%M")


def _safe_wikilink_label(value: str) -> str:
    return (value or "Untitled").replace("[[", "").replace("]]", "").replace("|", "-").strip() or "Untitled"


def _markdown_tag(value: str) -> str:
    return "#" + "".join(char if char.isalnum() or char in "-_" else "-" for char in value.strip()).strip("-")


def _daily_note_path(workflow_id: str, date_key: str) -> Path | None:
    base = _default_daily_memory_dir()
    if not base:
        return None
    safe_workflow = "".join(char if char.isalnum() or char in "-_" else "-" for char in workflow_id).strip("-")
    return base / safe_workflow / "journals" / f"{date_key}.md"


def _daily_note_header(workflow_id: str, date_key: str) -> str:
    return (
        "---\n"
        "title: Daily Memory\n"
        f"date: {date_key}\n"
        f"workflow: {workflow_id}\n"
        "type: p3394_daily_memory\n"
        "---\n\n"
        f"# Daily Memory {date_key}\n\n"
        "## Memory Entries\n"
    )


def _read_note_preview(path: str | Path | None, max_chars: int = 1200) -> str:
    if not path:
        return ""
    note_path = Path(path)
    if not note_path.exists():
        return ""
    content = note_path.read_text(encoding="utf-8", errors="replace").strip()
    return content[:max_chars]


def _extract_note_wikilinks(content: str) -> list[str]:
    links = []
    for match in re.finditer(r"\[\[([^\]]+)\]\]", content or ""):
        label = match.group(1).split("|", 1)[0].strip()
        if label and label not in links:
            links.append(label)
    return links


def _extract_note_markdown_tags(content: str) -> list[str]:
    tags = []
    for match in re.finditer(r"(?<!\w)#([\w\-]+)", content or ""):
        tag = match.group(1).strip()
        if tag and tag not in tags:
            tags.append(tag)
    return tags


def _ensure_p3394_daily_note_file(workflow_id: str, date_key: str) -> Path | None:
    note_path = _daily_note_path(workflow_id, date_key)
    if not note_path:
        return None
    note_path.parent.mkdir(parents=True, exist_ok=True)
    if not note_path.exists():
        note_path.write_text(_daily_note_header(workflow_id, date_key), encoding="utf-8")
    return note_path


def _ensure_schema(path: Path) -> None:
    with _connect(path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS p3394_knowledge_items (
                id TEXT PRIMARY KEY,
                workflow_id TEXT NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                source TEXT,
                tags TEXT,
                metadata TEXT,
                created_at INTEGER,
                updated_at INTEGER
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_p3394_knowledge_workflow ON p3394_knowledge_items(workflow_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_p3394_knowledge_updated ON p3394_knowledge_items(updated_at DESC)"
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS p3394_memory_graph_nodes (
                id TEXT PRIMARY KEY,
                workflow_id TEXT NOT NULL,
                label TEXT NOT NULL,
                kind TEXT NOT NULL,
                summary TEXT,
                metadata TEXT,
                created_at INTEGER,
                updated_at INTEGER,
                UNIQUE(workflow_id, label, kind)
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_p3394_graph_nodes_workflow ON p3394_memory_graph_nodes(workflow_id)"
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS p3394_memory_graph_edges (
                id TEXT PRIMARY KEY,
                workflow_id TEXT NOT NULL,
                source_node_id TEXT NOT NULL,
                target_node_id TEXT NOT NULL,
                relation TEXT NOT NULL,
                weight REAL,
                evidence TEXT,
                metadata TEXT,
                created_at INTEGER,
                updated_at INTEGER,
                UNIQUE(workflow_id, source_node_id, target_node_id, relation)
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_p3394_graph_edges_workflow ON p3394_memory_graph_edges(workflow_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_p3394_graph_edges_source ON p3394_memory_graph_edges(source_node_id)"
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS p3394_daily_memory_notes (
                id TEXT PRIMARY KEY,
                workflow_id TEXT NOT NULL,
                date_key TEXT NOT NULL,
                title TEXT NOT NULL,
                path TEXT,
                entry_count INTEGER,
                tags TEXT,
                metadata TEXT,
                created_at INTEGER,
                updated_at INTEGER,
                UNIQUE(workflow_id, date_key)
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_p3394_daily_memory_workflow ON p3394_daily_memory_notes(workflow_id, date_key DESC)"
        )


def _parse_knowledge_row(row: sqlite3.Row | dict[str, Any]) -> dict[str, Any]:
    item = dict(row)
    item["tags"] = _load_json(item.get("tags"), [])
    item["metadata"] = _load_json(item.get("metadata"), {})
    return item


def _parse_node_row(row: sqlite3.Row | dict[str, Any]) -> dict[str, Any]:
    item = dict(row)
    item["metadata"] = _load_json(item.get("metadata"), {})
    return item


def _parse_edge_row(row: sqlite3.Row | dict[str, Any]) -> dict[str, Any]:
    item = dict(row)
    item["metadata"] = _load_json(item.get("metadata"), {})
    return item


def _parse_daily_note_row(row: sqlite3.Row | dict[str, Any]) -> dict[str, Any]:
    item = dict(row)
    item["tags"] = _load_json(item.get("tags"), [])
    item["metadata"] = _load_json(item.get("metadata"), {})
    item["preview"] = _read_note_preview(item.get("path"))
    full_content = ""
    if item.get("path") and Path(item["path"]).exists():
        full_content = Path(item["path"]).read_text(encoding="utf-8", errors="replace")
    item["wikilinks"] = _extract_note_wikilinks(full_content)
    item["markdown_tags"] = _extract_note_markdown_tags(full_content)
    return item


def add_p3394_knowledge_item(
    *,
    workflow_id: str,
    title: str,
    content: str,
    source: str = "manual",
    tags: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    now = _now_ms()
    item = {
        "id": f"p3394_knowledge_{uuid.uuid4().hex[:24]}",
        "workflow_id": workflow_id,
        "title": title.strip() or "Untitled",
        "content": content.strip(),
        "source": source.strip() or "manual",
        "tags": list(tags or []),
        "metadata": dict(metadata or {}),
        "created_at": now,
        "updated_at": now,
    }
    path = _default_sqlite_path()
    if not path:
        _MEMORY_KNOWLEDGE_ITEMS.insert(0, item)
        _append_p3394_daily_memory_entry(item)
        return item

    _ensure_schema(path)
    with _connect(path) as conn:
        conn.execute(
            """
            INSERT INTO p3394_knowledge_items (
                id, workflow_id, title, content, source, tags, metadata, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                item["id"],
                workflow_id,
                item["title"],
                item["content"],
                item["source"],
                _dump_json(item["tags"]),
                _dump_json(item["metadata"]),
                now,
                now,
            ),
        )
    _append_p3394_daily_memory_entry(item)
    return item


def list_p3394_knowledge_items(workflow_id: str, limit: int = 50) -> list[dict[str, Any]]:
    path = _default_sqlite_path()
    if not path or not path.exists():
        return [
            item
            for item in _MEMORY_KNOWLEDGE_ITEMS
            if item.get("workflow_id") == workflow_id
        ][:limit]

    _ensure_schema(path)
    with _connect(path) as conn:
        rows = conn.execute(
            """
            SELECT id, workflow_id, title, content, source, tags, metadata, created_at, updated_at
            FROM p3394_knowledge_items
            WHERE workflow_id = ?
            ORDER BY updated_at DESC
            LIMIT ?
            """,
            (workflow_id, limit),
        ).fetchall()
    return [_parse_knowledge_row(row) for row in rows]


def _upsert_p3394_daily_memory_note(
    *,
    workflow_id: str,
    date_key: str,
    path: Path | None,
    tags: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    now = _now_ms()
    note_path = str(path) if path else ""
    entry_count = 0
    if path and path.exists():
        entry_count = path.read_text(encoding="utf-8", errors="replace").count("\n- ")
    note = {
        "id": f"p3394_daily_{uuid.uuid4().hex[:24]}",
        "workflow_id": workflow_id,
        "date_key": date_key,
        "title": "Daily Memory",
        "path": note_path,
        "entry_count": entry_count,
        "tags": list(tags or ["daily-memory", "markdown", "graph"]),
        "metadata": dict(metadata or {}),
        "created_at": now,
        "updated_at": now,
        "preview": _read_note_preview(note_path),
    }
    full_content = ""
    if path and path.exists():
        full_content = path.read_text(encoding="utf-8", errors="replace")
    note["wikilinks"] = _extract_note_wikilinks(full_content)
    note["markdown_tags"] = _extract_note_markdown_tags(full_content)

    sqlite_path = _default_sqlite_path()
    if not sqlite_path:
        for existing in _MEMORY_DAILY_NOTES:
            if existing.get("workflow_id") == workflow_id and existing.get("date_key") == date_key:
                existing.update({
                    "path": note_path,
                    "entry_count": entry_count,
                    "tags": note["tags"],
                    "metadata": note["metadata"],
                    "updated_at": now,
                    "preview": note["preview"],
                })
                return existing
        _MEMORY_DAILY_NOTES.insert(0, note)
        return note

    _ensure_schema(sqlite_path)
    with _connect(sqlite_path) as conn:
        existing = conn.execute(
            """
            SELECT id, created_at
            FROM p3394_daily_memory_notes
            WHERE workflow_id = ? AND date_key = ?
            """,
            (workflow_id, date_key),
        ).fetchone()
        if existing:
            note["id"] = existing["id"]
            note["created_at"] = existing["created_at"]
            conn.execute(
                """
                UPDATE p3394_daily_memory_notes
                SET title = ?, path = ?, entry_count = ?, tags = ?, metadata = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    note["title"],
                    note["path"],
                    note["entry_count"],
                    _dump_json(note["tags"]),
                    _dump_json(note["metadata"]),
                    now,
                    note["id"],
                ),
            )
        else:
            conn.execute(
                """
                INSERT INTO p3394_daily_memory_notes (
                    id, workflow_id, date_key, title, path, entry_count, tags,
                    metadata, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    note["id"],
                    workflow_id,
                    date_key,
                    note["title"],
                    note["path"],
                    note["entry_count"],
                    _dump_json(note["tags"]),
                    _dump_json(note["metadata"]),
                    now,
                    now,
                ),
            )
    _sync_p3394_daily_note_markdown_links(
        workflow_id=workflow_id,
        date_key=date_key,
        wikilinks=note["wikilinks"],
        markdown_tags=note["markdown_tags"],
        evidence_path=note_path,
    )
    return note


def _sync_p3394_daily_note_markdown_links(
    *,
    workflow_id: str,
    date_key: str,
    wikilinks: list[str],
    markdown_tags: list[str],
    evidence_path: str,
) -> None:
    evidence = f"Daily memory markdown index at {evidence_path}" if evidence_path else "Daily memory markdown index"
    for link in wikilinks[:40]:
        if not link or link == date_key:
            continue
        add_p3394_memory_relation(
            workflow_id=workflow_id,
            source_label=date_key,
            source_kind="daily_note",
            relation="mentions",
            target_label=link,
            target_kind="knowledge",
            evidence=evidence,
            weight=0.75,
        )
    for tag in markdown_tags[:40]:
        if not tag:
            continue
        add_p3394_memory_relation(
            workflow_id=workflow_id,
            source_label=date_key,
            source_kind="daily_note",
            relation="tagged",
            target_label=tag,
            target_kind="memory_tag",
            evidence=evidence,
            weight=0.65,
        )


def _append_p3394_daily_memory_entry(item: dict[str, Any]) -> dict[str, Any] | None:
    workflow_id = str(item.get("workflow_id") or "").strip()
    if not workflow_id:
        return None
    date_key = str((item.get("metadata") or {}).get("date_key") or _today_key())
    note_path = _ensure_p3394_daily_note_file(workflow_id, date_key)
    if not note_path:
        return None

    title = _safe_wikilink_label(str(item.get("title") or "Untitled"))
    content = str(item.get("content") or "").strip()
    tags = [str(tag).strip() for tag in item.get("tags") or [] if str(tag).strip()]
    tag_text = " ".join(_markdown_tag(tag) for tag in tags[:6])
    source = str(item.get("source") or "memory").strip()
    entry_id = str(item.get("id") or uuid.uuid4().hex)
    block = (
        f"\n- { _clock_label() } [[{title}]] {tag_text}\n"
        f"  - source:: {source}\n"
        f"  - memory_id:: {entry_id}\n"
        f"  - content:: {content}\n"
    )
    existing = note_path.read_text(encoding="utf-8", errors="replace")
    if f"memory_id:: {entry_id}" not in existing:
        note_path.write_text(existing.rstrip() + block + "\n", encoding="utf-8")

    note = _upsert_p3394_daily_memory_note(
        workflow_id=workflow_id,
        date_key=date_key,
        path=note_path,
        tags=["daily-memory", "markdown", "wikilink"],
        metadata={"pattern": "logseq_foam_style", "source": "p3394"},
    )
    add_p3394_memory_relation(
        workflow_id=workflow_id,
        source_label="每日记忆",
        source_kind="daily_memory",
        relation="contains",
        target_label=date_key,
        target_kind="daily_note",
        evidence=f"Daily memory journal at {note_path}",
        weight=1.2,
    )
    add_p3394_memory_relation(
        workflow_id=workflow_id,
        source_label=date_key,
        source_kind="daily_note",
        relation="records",
        target_label=title,
        target_kind="knowledge",
        evidence=content,
        weight=1.0,
    )
    category = str((item.get("metadata") or {}).get("memory_category") or (tags[0] if tags else "")).strip()
    if category:
        add_p3394_memory_relation(
            workflow_id=workflow_id,
            source_label=date_key,
            source_kind="daily_note",
            relation="indexes",
            target_label=category,
            target_kind="memory_category",
            evidence=title,
            weight=0.8,
        )
    return note


def list_p3394_daily_memory_notes(workflow_id: str, limit: int = 30) -> list[dict[str, Any]]:
    path = _default_sqlite_path()
    if not path or not path.exists():
        return [
            item
            for item in _MEMORY_DAILY_NOTES
            if item.get("workflow_id") == workflow_id
        ][:limit]

    _ensure_schema(path)
    with _connect(path) as conn:
        rows = conn.execute(
            """
            SELECT id, workflow_id, date_key, title, path, entry_count, tags, metadata, created_at, updated_at
            FROM p3394_daily_memory_notes
            WHERE workflow_id = ?
            ORDER BY date_key DESC, updated_at DESC
            LIMIT ?
            """,
            (workflow_id, limit),
        ).fetchall()
    return [_parse_daily_note_row(row) for row in rows]


def get_p3394_daily_memory_timeline(
    workflow_id: str,
    *,
    days: int = 7,
    end_date: str | None = None,
) -> list[dict[str, Any]]:
    bounded_days = max(1, min(int(days or 7), 90))
    end = _parse_date_key(end_date)
    notes: list[dict[str, Any]] = []
    for offset in range(bounded_days):
        date_key = (end - timedelta(days=offset)).isoformat()
        note_path = _ensure_p3394_daily_note_file(workflow_id, date_key)
        note = _upsert_p3394_daily_memory_note(
            workflow_id=workflow_id,
            date_key=date_key,
            path=note_path,
            tags=["daily-memory", "markdown", "timeline"],
            metadata={"pattern": "logseq_foam_style", "source": "timeline"},
        )
        add_p3394_memory_relation(
            workflow_id=workflow_id,
            source_label="每日记忆",
            source_kind="daily_memory",
            relation="contains",
            target_label=date_key,
            target_kind="daily_note",
            evidence=f"Daily memory timeline note at {note_path}",
            weight=1.0,
        )
        notes.append(note)
    return notes


def generate_p3394_daily_memory_note(
    *,
    workflow_id: str,
    title: str = "Manual daily memory",
    content: str = "Manual daily memory checkpoint.",
    tags: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    item = add_p3394_knowledge_item(
        workflow_id=workflow_id,
        title=title,
        content=content,
        source="daily_memory",
        tags=list(tags or ["daily-memory"]),
        metadata={**dict(metadata or {}), "memory_category": "daily-memory"},
    )
    notes = list_p3394_daily_memory_notes(workflow_id, limit=1)
    return {"knowledge": item, "note": notes[0] if notes else None}


def search_p3394_knowledge_items(
    *,
    workflow_id: str,
    query: str,
    limit: int = 20,
) -> list[dict[str, Any]]:
    needle = query.strip().lower()
    if not needle:
        return list_p3394_knowledge_items(workflow_id, limit=limit)

    def score_item(item: dict[str, Any]) -> int:
        haystacks = [
            str(item.get("title") or ""),
            str(item.get("content") or ""),
            " ".join(str(tag) for tag in item.get("tags") or []),
            str(item.get("source") or ""),
        ]
        text = "\n".join(haystacks).lower()
        return text.count(needle)

    path = _default_sqlite_path()
    if not path or not path.exists():
        matches = [
            item
            for item in _MEMORY_KNOWLEDGE_ITEMS
            if item.get("workflow_id") == workflow_id and score_item(item) > 0
        ]
        return sorted(matches, key=lambda item: (score_item(item), item.get("updated_at", 0)), reverse=True)[:limit]

    _ensure_schema(path)
    like = f"%{query.strip()}%"
    with _connect(path) as conn:
        rows = conn.execute(
            """
            SELECT id, workflow_id, title, content, source, tags, metadata, created_at, updated_at
            FROM p3394_knowledge_items
            WHERE workflow_id = ?
              AND (title LIKE ? OR content LIKE ? OR source LIKE ? OR tags LIKE ?)
            ORDER BY updated_at DESC
            LIMIT ?
            """,
            (workflow_id, like, like, like, like, limit),
        ).fetchall()
    items = [_parse_knowledge_row(row) for row in rows]
    return sorted(items, key=lambda item: (score_item(item), item.get("updated_at", 0)), reverse=True)


def upsert_p3394_memory_node(
    *,
    workflow_id: str,
    label: str,
    kind: str = "concept",
    summary: str = "",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    now = _now_ms()
    label = label.strip()
    kind = kind.strip() or "concept"
    if not label:
        raise ValueError("Memory node label is required")

    path = _default_sqlite_path()
    if not path:
        for item in _MEMORY_GRAPH_NODES:
            if item.get("workflow_id") == workflow_id and item.get("label") == label and item.get("kind") == kind:
                item.update({"summary": summary, "metadata": dict(metadata or {}), "updated_at": now})
                return item
        item = {
            "id": f"p3394_node_{uuid.uuid4().hex[:24]}",
            "workflow_id": workflow_id,
            "label": label,
            "kind": kind,
            "summary": summary,
            "metadata": dict(metadata or {}),
            "created_at": now,
            "updated_at": now,
        }
        _MEMORY_GRAPH_NODES.insert(0, item)
        return item

    _ensure_schema(path)
    with _connect(path) as conn:
        existing = conn.execute(
            """
            SELECT id, workflow_id, label, kind, summary, metadata, created_at, updated_at
            FROM p3394_memory_graph_nodes
            WHERE workflow_id = ? AND label = ? AND kind = ?
            """,
            (workflow_id, label, kind),
        ).fetchone()
        if existing:
            node_id = existing["id"]
            created_at = existing["created_at"]
            conn.execute(
                """
                UPDATE p3394_memory_graph_nodes
                SET summary = ?, metadata = ?, updated_at = ?
                WHERE id = ?
                """,
                (summary, _dump_json(metadata), now, node_id),
            )
        else:
            node_id = f"p3394_node_{uuid.uuid4().hex[:24]}"
            created_at = now
            conn.execute(
                """
                INSERT INTO p3394_memory_graph_nodes (
                    id, workflow_id, label, kind, summary, metadata, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (node_id, workflow_id, label, kind, summary, _dump_json(metadata), now, now),
            )
    return {
        "id": node_id,
        "workflow_id": workflow_id,
        "label": label,
        "kind": kind,
        "summary": summary,
        "metadata": dict(metadata or {}),
        "created_at": created_at,
        "updated_at": now,
    }


def list_p3394_memory_nodes(workflow_id: str, limit: int = 100) -> list[dict[str, Any]]:
    path = _default_sqlite_path()
    if not path or not path.exists():
        return [
            item
            for item in _MEMORY_GRAPH_NODES
            if item.get("workflow_id") == workflow_id
        ][:limit]

    _ensure_schema(path)
    with _connect(path) as conn:
        rows = conn.execute(
            """
            SELECT id, workflow_id, label, kind, summary, metadata, created_at, updated_at
            FROM p3394_memory_graph_nodes
            WHERE workflow_id = ?
            ORDER BY updated_at DESC
            LIMIT ?
            """,
            (workflow_id, limit),
        ).fetchall()
    return [_parse_node_row(row) for row in rows]


def upsert_p3394_memory_edge(
    *,
    workflow_id: str,
    source_node_id: str,
    target_node_id: str,
    relation: str,
    weight: float = 1.0,
    evidence: str = "",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    now = _now_ms()
    relation = relation.strip() or "related_to"
    path = _default_sqlite_path()
    if not path:
        for item in _MEMORY_GRAPH_EDGES:
            if (
                item.get("workflow_id") == workflow_id
                and item.get("source_node_id") == source_node_id
                and item.get("target_node_id") == target_node_id
                and item.get("relation") == relation
            ):
                item.update({"weight": float(weight), "evidence": evidence, "metadata": dict(metadata or {}), "updated_at": now})
                return item
        item = {
            "id": f"p3394_edge_{uuid.uuid4().hex[:24]}",
            "workflow_id": workflow_id,
            "source_node_id": source_node_id,
            "target_node_id": target_node_id,
            "relation": relation,
            "weight": float(weight),
            "evidence": evidence,
            "metadata": dict(metadata or {}),
            "created_at": now,
            "updated_at": now,
        }
        _MEMORY_GRAPH_EDGES.insert(0, item)
        return item

    _ensure_schema(path)
    with _connect(path) as conn:
        existing = conn.execute(
            """
            SELECT id, created_at
            FROM p3394_memory_graph_edges
            WHERE workflow_id = ? AND source_node_id = ? AND target_node_id = ? AND relation = ?
            """,
            (workflow_id, source_node_id, target_node_id, relation),
        ).fetchone()
        if existing:
            edge_id = existing["id"]
            created_at = existing["created_at"]
            conn.execute(
                """
                UPDATE p3394_memory_graph_edges
                SET weight = ?, evidence = ?, metadata = ?, updated_at = ?
                WHERE id = ?
                """,
                (float(weight), evidence, _dump_json(metadata), now, edge_id),
            )
        else:
            edge_id = f"p3394_edge_{uuid.uuid4().hex[:24]}"
            created_at = now
            conn.execute(
                """
                INSERT INTO p3394_memory_graph_edges (
                    id, workflow_id, source_node_id, target_node_id, relation, weight,
                    evidence, metadata, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    edge_id,
                    workflow_id,
                    source_node_id,
                    target_node_id,
                    relation,
                    float(weight),
                    evidence,
                    _dump_json(metadata),
                    now,
                    now,
                ),
            )
    return {
        "id": edge_id,
        "workflow_id": workflow_id,
        "source_node_id": source_node_id,
        "target_node_id": target_node_id,
        "relation": relation,
        "weight": float(weight),
        "evidence": evidence,
        "metadata": dict(metadata or {}),
        "created_at": created_at,
        "updated_at": now,
    }


def list_p3394_memory_edges(workflow_id: str, limit: int = 100) -> list[dict[str, Any]]:
    path = _default_sqlite_path()
    if not path or not path.exists():
        return [
            item
            for item in _MEMORY_GRAPH_EDGES
            if item.get("workflow_id") == workflow_id
        ][:limit]

    _ensure_schema(path)
    with _connect(path) as conn:
        rows = conn.execute(
            """
            SELECT id, workflow_id, source_node_id, target_node_id, relation, weight,
                   evidence, metadata, created_at, updated_at
            FROM p3394_memory_graph_edges
            WHERE workflow_id = ?
            ORDER BY updated_at DESC
            LIMIT ?
            """,
            (workflow_id, limit),
        ).fetchall()
    return [_parse_edge_row(row) for row in rows]


def add_p3394_memory_relation(
    *,
    workflow_id: str,
    source_label: str,
    relation: str,
    target_label: str,
    source_kind: str = "concept",
    target_kind: str = "concept",
    evidence: str = "",
    weight: float = 1.0,
) -> dict[str, Any]:
    source = upsert_p3394_memory_node(
        workflow_id=workflow_id,
        label=source_label,
        kind=source_kind,
        summary=evidence,
        metadata={"source": "relation"},
    )
    target = upsert_p3394_memory_node(
        workflow_id=workflow_id,
        label=target_label,
        kind=target_kind,
        summary=evidence,
        metadata={"source": "relation"},
    )
    edge = upsert_p3394_memory_edge(
        workflow_id=workflow_id,
        source_node_id=source["id"],
        target_node_id=target["id"],
        relation=relation,
        evidence=evidence,
        weight=weight,
        metadata={"source_label": source["label"], "target_label": target["label"]},
    )
    return {"source": source, "target": target, "edge": edge}


def get_p3394_memory_graph_summary(workflow_id: str, limit: int = 100) -> dict[str, Any]:
    nodes = list_p3394_memory_nodes(workflow_id, limit=limit)
    edges = list_p3394_memory_edges(workflow_id, limit=limit)
    node_by_id = {item["id"]: item for item in nodes}
    readable_edges = []
    for edge in edges:
        source = node_by_id.get(edge.get("source_node_id"), {})
        target = node_by_id.get(edge.get("target_node_id"), {})
        readable_edges.append(
            {
                **edge,
                "source_label": source.get("label") or edge.get("metadata", {}).get("source_label"),
                "target_label": target.get("label") or edge.get("metadata", {}).get("target_label"),
            }
        )
    return {
        "node_count": len(nodes),
        "edge_count": len(edges),
        "nodes": nodes,
        "edges": readable_edges,
    }


def get_p3394_local_memory_summary(workflow_id: str, limit: int = 50) -> dict[str, Any]:
    knowledge = list_p3394_knowledge_items(workflow_id, limit=limit)
    graph = get_p3394_memory_graph_summary(workflow_id, limit=limit)
    daily_notes = list_p3394_daily_memory_notes(workflow_id, limit=min(limit, 30))
    return {
        "workflow_id": workflow_id,
        "knowledge_count": len(knowledge),
        "knowledge": knowledge,
        "daily_memory_count": len(daily_notes),
        "daily_memory": daily_notes,
        "graph": graph,
    }
