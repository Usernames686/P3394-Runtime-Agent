"""Admin API for the AgentClaw-hosted P3394 runtime."""

from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, Form, Query, UploadFile
from pydantic import BaseModel, Field

from agentclaw.agent_square.p3394_runtime_agent.agents.p3394_artifacts import (
    list_p3394_artifacts,
    open_p3394_artifact_path,
)
from agentclaw.agent_square.p3394_runtime_agent.agents.p3394_execution_records import (
    list_p3394_execution_records,
)
from agentclaw.agent_square.p3394_runtime_agent.agents.p3394_execution_summary import (
    list_p3394_execution_summary,
)
from agentclaw.agent_square.p3394_runtime_agent.agents.p3394_file_context import (
    list_p3394_file_contexts,
)
from agentclaw.agent_square.p3394_runtime_agent.agents.p3394_knowledge_import import (
    import_p3394_local_knowledge,
    stage_p3394_uploaded_file,
)
from agentclaw.agent_square.p3394_runtime_agent.agents.p3394_task_history import (
    list_p3394_task_history,
)
from agentclaw.agent_square.p3394_runtime_agent.agents.p3394_tool_records import (
    list_p3394_tool_records,
)
from agentclaw.agent_square.p3394_runtime_agent.agents.p3394_local_memory import (
    add_p3394_knowledge_item,
    add_p3394_memory_relation,
    generate_p3394_daily_memory_note,
    get_p3394_daily_memory_timeline,
    get_p3394_memory_graph_summary,
    get_p3394_local_memory_summary,
    list_p3394_daily_memory_notes,
    list_p3394_knowledge_items,
    search_p3394_knowledge_items,
    upsert_p3394_memory_node,
)


router = APIRouter(prefix="/p3394", tags=["p3394"])


class P3394KnowledgeCreateRequest(BaseModel):
    workflow_id: str = Field(default="p3394_runtime_agent", min_length=1)
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1)
    source: str = Field(default="manual", max_length=200)
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class P3394KnowledgeImportRequest(BaseModel):
    workflow_id: str = Field(default="p3394_runtime_agent", min_length=1)
    paths: list[str] = Field(default_factory=list, min_length=1)
    recursive: bool = True
    max_files: int = Field(default=50, ge=1, le=500)
    max_chars: int = Field(default=12000, ge=500, le=200000)


class P3394OpenPathRequest(BaseModel):
    path: str = Field(min_length=1)


class P3394MemoryNodeCreateRequest(BaseModel):
    workflow_id: str = Field(default="p3394_runtime_agent", min_length=1)
    label: str = Field(min_length=1, max_length=160)
    kind: str = Field(default="concept", max_length=80)
    summary: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class P3394MemoryRelationCreateRequest(BaseModel):
    workflow_id: str = Field(default="p3394_runtime_agent", min_length=1)
    source_label: str = Field(min_length=1, max_length=160)
    relation: str = Field(default="related_to", min_length=1, max_length=100)
    target_label: str = Field(min_length=1, max_length=160)
    source_kind: str = Field(default="concept", max_length=80)
    target_kind: str = Field(default="concept", max_length=80)
    evidence: str = ""
    weight: float = Field(default=1.0, ge=0)


class P3394DailyMemoryGenerateRequest(BaseModel):
    title: str = Field(default="Manual daily memory", min_length=1, max_length=200)
    content: str = Field(default="Manual daily memory checkpoint.", min_length=1)
    tags: list[str] = Field(default_factory=lambda: ["daily-memory"])
    metadata: dict[str, Any] = Field(default_factory=dict)


@router.get("/task-history", summary="List P3394 task history")
async def list_task_history(
    workflow_id: str = Query("p3394_runtime_agent", min_length=1),
    limit: int = Query(20, ge=1, le=100),
):
    """Return persisted P3394 route and internal role-plan history."""
    tasks = list_p3394_task_history(workflow_id=workflow_id, limit=limit)
    return {
        "workflow_id": workflow_id,
        "count": len(tasks),
        "tasks": tasks,
    }


@router.get("/execution-records", summary="List P3394 execution records")
async def list_execution_records(
    workflow_id: str = Query("p3394_runtime_agent", min_length=1),
    limit: int = Query(20, ge=1, le=100),
):
    """Return persisted P3394 execution records for the workbench side panel."""
    records = list_p3394_execution_records(workflow_id=workflow_id, limit=limit)
    return {
        "workflow_id": workflow_id,
        "count": len(records),
        "records": records,
    }


@router.get("/execution-summary", summary="List readable P3394 execution summaries")
async def list_execution_summary(
    workflow_id: str = Query("p3394_runtime_agent", min_length=1),
    limit: int = Query(20, ge=1, le=100),
):
    """Return route, role, tool, file, and artifact details grouped by run."""
    records = list_p3394_execution_summary(workflow_id=workflow_id, limit=limit)
    return {
        "workflow_id": workflow_id,
        "count": len(records),
        "records": records,
    }


@router.get("/knowledge", summary="List or search P3394 local knowledge")
async def list_local_knowledge(
    workflow_id: str = Query("p3394_runtime_agent", min_length=1),
    q: str = Query("", alias="q"),
    limit: int = Query(50, ge=1, le=200),
):
    """Return local SQLite-backed P3394 knowledge items."""
    if q.strip():
        items = search_p3394_knowledge_items(workflow_id=workflow_id, query=q, limit=limit)
    else:
        items = list_p3394_knowledge_items(workflow_id=workflow_id, limit=limit)
    return {
        "workflow_id": workflow_id,
        "query": q,
        "count": len(items),
        "items": items,
    }


@router.post("/knowledge", summary="Create a P3394 local knowledge item")
async def create_local_knowledge(body: P3394KnowledgeCreateRequest):
    """Persist a local knowledge item in the P3394 SQLite store."""
    item = add_p3394_knowledge_item(**body.model_dump())
    return {
        "success": True,
        "item": item,
    }


@router.post("/knowledge/import", summary="Import local files into P3394 local knowledge")
async def import_local_knowledge(body: P3394KnowledgeImportRequest):
    """Index local markdown/text/pdf/doc files into P3394 memory and graph."""
    return import_p3394_local_knowledge(**body.model_dump())


@router.post("/knowledge/import-files", summary="Upload files into P3394 local knowledge")
async def import_uploaded_knowledge(
    workflow_id: str = Form(default="p3394_runtime_agent"),
    recursive: bool = Form(default=True),
    max_files: int = Form(default=50),
    files: list[UploadFile] = File(...),
):
    """Persist uploaded files locally, then import them into P3394 memory and graph."""
    staged_paths = []
    for upload in files:
        source_name = upload.filename or "uploaded-file"
        temp_path = stage_p3394_uploaded_file(source_name)
        with temp_path.open("wb") as handle:
            while chunk := await upload.read(1024 * 1024):
                handle.write(chunk)
        staged_paths.append(str(temp_path))
    return import_p3394_local_knowledge(
        workflow_id=workflow_id,
        paths=staged_paths,
        recursive=recursive,
        max_files=max_files,
        source_mode="uploaded_file",
    )


@router.get("/memory-graph", summary="Get P3394 memory graph")
async def get_memory_graph(
    workflow_id: str = Query("p3394_runtime_agent", min_length=1),
    limit: int = Query(100, ge=1, le=500),
):
    """Return graph nodes and relations from the local P3394 memory graph."""
    graph = get_p3394_memory_graph_summary(workflow_id=workflow_id, limit=limit)
    return {
        "workflow_id": workflow_id,
        **graph,
    }


@router.get("/memory", summary="Get P3394 local memory summary")
async def get_local_memory(
    workflow_id: str = Query("p3394_runtime_agent", min_length=1),
    limit: int = Query(50, ge=1, le=200),
):
    """Return local knowledge and memory graph summary."""
    return get_p3394_local_memory_summary(workflow_id=workflow_id, limit=limit)


@router.get("/daily-memory", summary="List P3394 daily memory markdown notes")
async def list_daily_memory(
    workflow_id: str = Query("p3394_runtime_agent", min_length=1),
    limit: int = Query(30, ge=1, le=100),
):
    """Return Logseq/Foam-style daily markdown memory notes."""
    notes = list_p3394_daily_memory_notes(workflow_id=workflow_id, limit=limit)
    return {
        "workflow_id": workflow_id,
        "count": len(notes),
        "notes": notes,
    }


@router.post("/daily-memory/generate", summary="Generate today's P3394 daily memory note")
async def generate_daily_memory(
    body: P3394DailyMemoryGenerateRequest,
    workflow_id: str = Query("p3394_runtime_agent", min_length=1),
):
    """Create a daily markdown memory checkpoint and link it into the graph."""
    result = generate_p3394_daily_memory_note(
        workflow_id=workflow_id,
        **body.model_dump(),
    )
    return {
        "success": True,
        **result,
    }


@router.get("/daily-memory/timeline", summary="Get P3394 daily memory timeline")
async def get_daily_memory_timeline(
    workflow_id: str = Query("p3394_runtime_agent", min_length=1),
    days: int = Query(7, ge=1, le=90),
    end_date: str = Query("", max_length=10),
):
    """Backfill and return a recent daily markdown memory timeline."""
    notes = get_p3394_daily_memory_timeline(
        workflow_id=workflow_id,
        days=days,
        end_date=end_date or None,
    )
    return {
        "workflow_id": workflow_id,
        "days": days,
        "count": len(notes),
        "notes": notes,
    }


@router.post("/memory-graph/nodes", summary="Create or update a P3394 memory node")
async def create_memory_node(body: P3394MemoryNodeCreateRequest):
    """Create or update a memory graph node."""
    node = upsert_p3394_memory_node(**body.model_dump())
    return {
        "success": True,
        "node": node,
    }


@router.post("/memory-graph/relations", summary="Create or update a P3394 memory relation")
async def create_memory_relation(body: P3394MemoryRelationCreateRequest):
    """Create or update a memory graph relation using labels."""
    relation = add_p3394_memory_relation(**body.model_dump())
    return {
        "success": True,
        "relation": relation,
    }


@router.post("/memory-graph/seed-demo", summary="Seed a large P3394 memory graph")
async def seed_memory_graph(
    workflow_id: str = Query("p3394_runtime_agent", min_length=1),
):
    """Create a dense starter atlas so the local memory page feels like a real graph."""
    relation_specs = [
        ("你", "person", "owns", "P3394 Agent Platform", "project", "本地平台包装为用户自己的 P3394 项目。"),
        ("你", "person", "prefers", "AgentClaw 原版界面", "concept", "用户明确希望界面和 AgentClaw 一样，简洁好用。"),
        ("你", "person", "wants", "可执行命令的 MLL Agent", "capability", "用户要求 P3394 接入模型并能执行命令。"),
        ("你", "person", "wants", "本地知识库", "capability", "用户要求搞一个本地知识库和记忆图谱。"),
        ("P3394 Agent Platform", "project", "runs_on", "AgentClaw", "runtime", "AgentClaw 提供工作流、工具执行、管理 API 和原生聊天界面。"),
        ("P3394 Agent Platform", "project", "contains", "P3394 Runtime Agent", "agent", "平台默认主智能体是 P3394 Runtime Agent。"),
        ("P3394 Agent Platform", "project", "contains", "记忆图谱", "capability", "左侧导航新增独立记忆图谱入口。"),
        ("P3394 Agent Platform", "project", "contains", "模板库", "capability", "模板库保留为可导入智能体入口。"),
        ("P3394 Agent Platform", "project", "contains", "底座助手", "agent", "底座助手保留 AgentClaw 原生能力。"),
        ("P3394 Runtime Agent", "agent", "stores_memory_in", "SQLite 本地记忆库", "database", "记忆图谱和知识条目落在 local-demo/.agentclaw/agentclaw-local.db。"),
        ("P3394 Runtime Agent", "agent", "uses", "命令执行工具", "tool", "运行时可以调用本地命令工具完成任务。"),
        ("P3394 Runtime Agent", "agent", "uses", "文件上下文", "capability", "运行时会记录用户提到或上传的文件上下文。"),
        ("P3394 Runtime Agent", "agent", "uses", "任务历史", "database", "任务路由和角色计划会落到本地记录。"),
        ("P3394 Runtime Agent", "agent", "uses", "工具调用记录", "database", "工具调用参数、输出和退出码会被记录。"),
        ("P3394 Runtime Agent", "agent", "reads", "P3394-v0.9.0-combined(2).md", "document", "本地 P3394 文档是运行时架构参考。"),
        ("P3394-v0.9.0-combined(2).md", "document", "describes", "UMF 消息", "concept", "P3394 文档强调统一消息格式。"),
        ("P3394-v0.9.0-combined(2).md", "document", "describes", "Capability Router", "process", "P3394 文档强调能力路由。"),
        ("P3394-v0.9.0-combined(2).md", "document", "describes", "Session State", "concept", "P3394 文档强调会话状态。"),
        ("P3394-v0.9.0-combined(2).md", "document", "describes", "Audit Trail", "database", "P3394 文档强调审计轨迹。"),
        ("记忆图谱", "capability", "renders_with", "Sigma.js", "tool", "Sigma.js 提供 WebGL 大图谱渲染。"),
        ("记忆图谱", "capability", "models_with", "Graphology", "tool", "Graphology 提供 JavaScript 图数据结构。"),
        ("记忆图谱", "capability", "persists_to", "SQLite 本地记忆库", "database", "图谱节点、边和知识条目都保存在本地 SQLite。"),
        ("Sigma.js", "tool", "supports", "WebGL 大图渲染", "capability", "Sigma.js 适合在浏览器里渲染大量节点和边。"),
        ("Graphology", "tool", "supports", "图数据结构", "capability", "Graphology 管理节点、边、属性和遍历。"),
        ("SQLite 本地记忆库", "database", "has_table", "p3394_knowledge_items", "database", "本地知识条目表。"),
        ("SQLite 本地记忆库", "database", "has_table", "p3394_memory_graph_nodes", "database", "记忆图谱节点表。"),
        ("SQLite 本地记忆库", "database", "has_table", "p3394_memory_graph_edges", "database", "记忆图谱关系表。"),
        ("命令执行工具", "tool", "writes", "工具调用记录", "database", "命令执行结果会进入工具记录。"),
        ("文件上下文", "capability", "feeds", "P3394 Runtime Agent", "agent", "文件上下文帮助运行时理解用户任务。"),
        ("任务历史", "database", "feeds", "P3394 Agent 页面", "capability", "页面侧栏可读取任务历史。"),
        ("工具调用记录", "database", "feeds", "P3394 Agent 页面", "capability", "页面侧栏可读取工具调用明细。"),
        ("模型配置", "capability", "feeds", "P3394 Runtime Agent", "agent", "系统配置里的模型会被运行时调用。"),
        ("P3394 Agent 页面", "capability", "opens", "AgentClaw 原版聊天", "capability", "主智能体页面复用 AgentClaw 原生聊天体验。"),
        ("模板库", "capability", "imports", "内置 Agent", "agent", "模板可以导入为可运行智能体。"),
        ("底座助手", "agent", "represents", "AgentClaw", "runtime", "底座助手展示原版底座能力。"),
        ("本地知识库", "capability", "contains", "项目偏好", "concept", "保存用户对界面、运行方式和能力边界的偏好。"),
        ("本地知识库", "capability", "contains", "架构事实", "concept", "保存 P3394/AgentClaw 架构事实。"),
        ("本地知识库", "capability", "contains", "执行记忆", "concept", "保存命令执行、文件上下文和调试记录。"),
        ("项目偏好", "concept", "links_to", "你", "person", "偏好来自用户反馈。"),
        ("架构事实", "concept", "links_to", "P3394-v0.9.0-combined(2).md", "document", "架构事实来自本地 P3394 文档。"),
        ("执行记忆", "concept", "links_to", "工具调用记录", "database", "执行记忆来自工具调用记录。"),
    ]
    relations = [
        add_p3394_memory_relation(
            workflow_id=workflow_id,
            source_label=source_label,
            source_kind=source_kind,
            relation=relation,
            target_label=target_label,
            target_kind=target_kind,
            evidence=evidence,
        )
        for source_label, source_kind, relation, target_label, target_kind, evidence in relation_specs
    ]
    knowledge_specs = [
        (
            "P3394 平台定位",
            "P3394 Agent Platform 是基于 AgentClaw 包装出来的本地通用智能体平台，默认主智能体是 P3394 Runtime Agent。",
            ["p3394", "platform", "agentclaw"],
        ),
        (
            "记忆图谱定位",
            "记忆图谱用于把用户偏好、项目事实、能力、工具、文档和执行记录连接成可探索的本地知识网络。",
            ["memory-graph", "sigma", "sqlite"],
        ),
        (
            "用户偏好",
            "用户更喜欢 AgentClaw 原版风格的简洁界面，同时希望 P3394 能接入模型、执行命令并保留本地记忆。",
            ["preference", "ux", "runtime"],
        ),
    ]
    for title, content, tags in knowledge_specs:
        add_p3394_knowledge_item(
            workflow_id=workflow_id,
            title=title,
            content=content,
            source="seed-demo",
            tags=tags,
        )
    graph = get_p3394_memory_graph_summary(workflow_id=workflow_id, limit=500)
    return {
        "success": True,
        "workflow_id": workflow_id,
        "seeded_relations": len(relations),
        **graph,
    }


@router.get("/file-context", summary="List P3394 file context")
async def list_file_context(
    workflow_id: str = Query("p3394_runtime_agent", min_length=1),
    limit: int = Query(20, ge=1, le=100),
):
    """Return persisted files referenced or attached during P3394 runs."""
    contexts = list_p3394_file_contexts(workflow_id=workflow_id, limit=limit)
    return {
        "workflow_id": workflow_id,
        "count": len(contexts),
        "contexts": contexts,
    }


@router.get("/artifacts", summary="List P3394 file artifacts")
async def list_artifacts(
    workflow_id: str = Query("p3394_runtime_agent", min_length=1),
    limit: int = Query(20, ge=1, le=100),
):
    """Return files that P3394 appears to have created or modified."""
    artifacts = list_p3394_artifacts(workflow_id=workflow_id, limit=limit)
    return {
        "workflow_id": workflow_id,
        "count": len(artifacts),
        "artifacts": artifacts,
    }


@router.post("/open-path", summary="Open a P3394 artifact path locally")
async def open_path(body: P3394OpenPathRequest):
    """Open a local file or folder path on the host machine."""
    return open_p3394_artifact_path(body.path)


@router.get("/tool-records", summary="List P3394 tool records")
async def list_tool_records(
    workflow_id: str = Query("p3394_runtime_agent", min_length=1),
    limit: int = Query(20, ge=1, le=100),
):
    """Return persisted P3394 tool-call records with command output details."""
    records = list_p3394_tool_records(workflow_id=workflow_id, limit=limit)
    return {
        "workflow_id": workflow_id,
        "count": len(records),
        "records": records,
    }
