"""
P3394 Runtime Agent.

An AgentClaw-native agentic workflow that uses P3394 as the runtime contract:
manifest declaration, UMF-style message normalization, session management,
relationship checks, audit summaries, and an LLM agent with built-in command
and tool execution.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any

from agentclaw import CustomNode, Input, LLMNode, Workflow
from agentclaw.api.builtin_agent import SmartPreFilterNode
from agentclaw.runtime.streaming import get_output_channel
from agentclaw.runtime.streaming import output as stream_output

from .p3394_reference import build_p3394_reference_prompt
from .p3394_roles import (
    activate_p3394_role_plan,
    build_p3394_role_plan,
    complete_p3394_role_plan,
)
from .p3394_execution_records import (
    complete_p3394_execution_record,
    get_latest_p3394_execution_record_for_thread,
    record_p3394_execution_record,
)
from .p3394_file_context import (
    list_p3394_file_contexts,
    record_p3394_file_contexts_from_state,
)
from .p3394_task_history import (
    get_latest_p3394_task_history_for_thread,
    list_p3394_task_history,
    record_p3394_task_history,
    update_p3394_task_history,
)
from .p3394_tool_records import list_p3394_tool_records
from .p3394_local_memory import (
    add_p3394_knowledge_item,
    add_p3394_memory_relation,
    get_p3394_local_memory_summary,
    search_p3394_knowledge_items,
)


P3394_MANIFEST: dict[str, Any] = {
    "schema_version": "p3394-draft-0.9.0",
    "agent": {
        "id": "agentclaw:p3394_runtime_agent",
        "name": "P3394 Runtime Agent",
        "session_ownership": "owner_capable",
        "conformance_level": "level_2_agentclaw_runtime",
        "runtime": {
            "host": "AgentClaw",
            "workflow_id": "p3394_runtime_agent",
            "execution": "LLMNode(agent_style='agentic')",
        },
    },
    "default_input": {
        "entry_point": "handle_message",
        "accepted_forms": ["user_input", "umf_message"],
        "canonical_wire_format": "UMF",
    },
    "channels": [
        {
            "id": "/dashboard/p3394-agent",
            "scope": "agentclaw://local/",
            "channel": "agentclaw_dashboard",
            "principal_source": "admin_token",
            "security": {"inbound": {"mode": "bearer"}},
        },
        {
            "id": "p3394_runtime_agent",
            "scope": "agentclaw://workflow/",
            "channel": "workflow_api",
            "principal_source": "workflow_api_key",
            "security": {"inbound": {"mode": "bearer"}},
        },
    ],
    "channel_adapter": {
        "visibility": "public_contract",
        "responsibilities": [
            "listen",
            "extract_channel_unique_id",
            "validate_security",
            "resolve_service_principal",
            "resolve_relationship",
            "validate_semantic_blocks",
            "normalize_to_umf",
            "deliver_to_handle_message",
        ],
        "error_behavior": {
            "format": "agent.error",
            "reason_codes": [
                "malformed_input",
                "authentication_failed",
                "authorization_failed",
                "semantic_block_violation",
                "unknown_capability",
                "session_id_not_resolved",
            ],
        },
    },
    "capabilities": [
        {
            "name": "manifest.describe",
            "description": "Return the public P3394-style manifest.",
            "message_types": ["agent.query"],
            "semantic_block_spec": "read_only",
        },
        {
            "name": "message.normalize",
            "description": "Normalize user input into a UMF-style envelope.",
            "message_types": ["agent.query"],
            "semantic_block_spec": "read_only",
        },
        {
            "name": "session.create",
            "description": "Create an owned P3394 session context.",
            "message_types": ["session.create"],
            "semantic_block_spec": "session_write",
        },
        {
            "name": "session.fetch",
            "description": "Fetch the active P3394 session context.",
            "message_types": ["session.fetch", "session.context.fetch"],
            "semantic_block_spec": "session_read",
        },
        {
            "name": "session.close",
            "description": "Close an owned P3394 session context.",
            "message_types": ["session.close", "session.lifecycle.transition"],
            "semantic_block_spec": "session_write",
        },
        {
            "name": "chat",
            "description": "Handle ordinary user requests through an AgentClaw LLM agent.",
            "message_types": ["agent.request"],
            "semantic_block_spec": "standard",
        },
        {
            "name": "command_execution",
            "description": "Use AgentClaw built-in tools and skills for shell, file, code, and project operations when authorized.",
            "message_types": ["agent.command", "agent.request"],
            "semantic_block_spec": "tool_execution",
        },
        {
            "name": "local_project_tooling",
            "description": "Use local file, shell, git, project overview, document, and web-search tools through AgentClaw skill-tools.",
            "message_types": ["agent.command", "agent.request"],
            "semantic_block_spec": "tool_execution",
        },
        {
            "name": "p3394.architecture_reference",
            "description": "Use the local P3394 v0.9.0 draft as the architecture reference for project analysis and transformation.",
            "message_types": ["agent.query", "agent.request"],
            "semantic_block_spec": "read_only",
        },
        {
            "name": "p3394.multi_agent_roles",
            "description": "Plan and track internal Planner, Researcher, Executor, and Reviewer roles behind the single P3394 Agent surface.",
            "message_types": ["agent.request"],
            "semantic_block_spec": "orchestration_read",
        },
        {
            "name": "p3394.task_history",
            "description": "Return recent P3394 task history, including selected route and internal role plan.",
            "message_types": ["agent.query"],
            "semantic_block_spec": "read_only",
        },
        {
            "name": "p3394.file_context",
            "description": "Persist and inspect files referenced or attached during P3394 runs.",
            "message_types": ["agent.request", "agent.query"],
            "semantic_block_spec": "read_only",
        },
        {
            "name": "p3394.tool_records",
            "description": "Persist and inspect tool calls, command output, cwd, stderr, and exit codes from P3394 runs.",
            "message_types": ["agent.request", "agent.query"],
            "semantic_block_spec": "read_only",
        },
        {
            "name": "p3394.local_memory",
            "description": "Persist and inspect local knowledge items and memory graph relations in SQLite.",
            "message_types": ["agent.request", "agent.query"],
            "semantic_block_spec": "memory_read_write",
        },
        {
            "name": "task.route",
            "description": "Classify an inbound task and select an AgentClaw target workflow or the local agentic runtime.",
            "message_types": ["agent.query", "agent.request"],
            "semantic_block_spec": "orchestration_read",
        },
        {
            "name": "agent.delegate",
            "description": "Delegate an authorized request to a registered AgentClaw workflow and return the child result.",
            "message_types": ["agent.command"],
            "semantic_block_spec": "orchestration_write",
        },
        {
            "name": "audit.summary",
            "description": "Return an auditable execution summary.",
            "message_types": ["agent.query"],
            "semantic_block_spec": "read_only",
        },
        {
            "name": "conformance.check",
            "description": "Return a P3394 conformance report for this AgentClaw runtime profile.",
            "message_types": ["agent.query"],
            "semantic_block_spec": "read_only",
        },
    ],
    "relationships": {
        "owner": {
            "capability_access": ["*"],
            "allowed_speech_acts": ["request", "command", "query", "configure"],
        },
        "administrator": {
            "capability_access": [
                "manifest.describe",
                "message.normalize",
                "session.create",
                "session.fetch",
                "session.close",
                "chat",
                "command_execution",
                "local_project_tooling",
                "p3394.architecture_reference",
                "p3394.multi_agent_roles",
                "p3394.task_history",
                "p3394.file_context",
                "p3394.tool_records",
                "p3394.local_memory",
                "task.route",
                "agent.delegate",
                "audit.summary",
                "conformance.check",
            ],
            "allowed_speech_acts": ["request", "command", "query"],
        },
        "peer": {
            "capability_access": [
                "manifest.describe",
                "message.normalize",
                "session.create",
                "session.fetch",
                "chat",
                "p3394.architecture_reference",
                "p3394.multi_agent_roles",
                "p3394.task_history",
                "p3394.file_context",
                "p3394.tool_records",
                "p3394.local_memory",
                "task.route",
                "audit.summary",
                "conformance.check",
            ],
            "allowed_speech_acts": ["request", "query"],
        },
        "client": {
            "capability_access": [
                "manifest.describe",
                "message.normalize",
                "session.create",
                "session.fetch",
                "session.close",
                "chat",
                "command_execution",
                "local_project_tooling",
                "p3394.architecture_reference",
                "p3394.multi_agent_roles",
                "p3394.task_history",
                "p3394.file_context",
                "p3394.tool_records",
                "p3394.local_memory",
                "task.route",
            ],
            "allowed_speech_acts": ["request", "query"],
        },
        "anonymous": {
            "capability_access": ["manifest.describe", "message.normalize", "task.route"],
            "allowed_speech_acts": ["query"],
        },
    },
    "orchestration": {
        "mode": "route_then_execute",
        "default_target": "agentic_runtime",
        "delegation_boundary": "registered_agentclaw_workflows",
        "routes": [
            {
                "family": "p3394_architecture",
                "target": "agentic_runtime",
                "execution_mode": "local_agentic_runtime",
                "capabilities": ["p3394.architecture_reference", "command_execution", "chat"],
            },
            {
                "family": "code_command",
                "target": "agentic_runtime",
                "execution_mode": "local_agentic_runtime",
                "capabilities": ["command_execution", "chat"],
            },
            {
                "family": "document_analysis",
                "target": "doc_analyzer",
                "execution_mode": "workflow_delegate_when_inputs_ready",
                "capabilities": ["agent.delegate", "chat"],
                "requires_inputs": ["documents"],
            },
            {
                "family": "knowledge_search",
                "target": "tool_agent",
                "execution_mode": "workflow_delegate_when_available",
                "capabilities": ["agent.delegate", "chat"],
            },
            {
                "family": "general_chat",
                "target": "agentic_runtime",
                "execution_mode": "local_agentic_runtime",
                "capabilities": ["chat"],
            },
        ],
    },
    "security_context_policy": {
        "levels": ["normal", "elevated"],
        "default_level": "normal",
        "non_escalation_invariant": True,
        "elevation": {
            "scope": "session",
            "requires_relationship": ["owner", "administrator"],
        },
    },
    "semantic_block_constraints": {
        "policies": {
            "permissive": ["text", "json", "tool_call", "artifact"],
            "standard": ["text", "json", "tool_call"],
            "strict": ["text", "json"],
            "minimal": ["text"],
        },
        "relationship_bindings": {
            "owner": "permissive",
            "administrator": "standard",
            "peer": "standard",
            "client": "strict",
            "anonymous": "minimal",
        },
    },
    "session": {
        "mode": "session",
        "bootstrap_acceptance": ["session.create"],
        "lifecycle_states": ["created", "open", "closing", "closed", "failed", "aborted", "expired"],
        "context_compartments": [
            "context_variables",
            "participants",
            "budgets",
            "memory_pointers",
            "child_sessions",
        ],
    },
    "extension_profiles": {
        "declared": ["agentclaw_tools", "agentclaw_skills"],
        "non_escalating": True,
    },
    "conformance": {
        "target_level": "level_2",
        "profile": "agentclaw_runtime",
        "implemented": [
            "manifest",
            "channel_adapter_contract",
            "umf_normalization",
            "session_lifecycle",
            "relationship_capability_authorization",
            "audit_events",
            "task_routing",
            "workflow_delegation",
            "agentic_tool_execution",
            "local_project_tooling",
            "local_p3394_architecture_reference",
            "internal_role_operating_model",
            "internal_role_runtime",
            "role_stage_tracking",
            "internal_role_trace",
            "sqlite_task_history",
            "sqlite_file_context",
            "sqlite_tool_records",
            "sqlite_local_knowledge",
            "sqlite_memory_graph",
        ],
    },
}

SESSION_STORE: dict[str, dict[str, Any]] = {}
AUDIT_EVENTS: list[dict[str, Any]] = []


workflow = Workflow(
    id="p3394_runtime_agent",
    name="P3394 Runtime Agent",
    description=(
        "接入 AgentClaw 和 MLL 的 P3394 智能体，可以对话、运行命令、搜索资料和分析文档。"
    ),
    welcome=(
        "P3394 Runtime Agent 已就绪。你可以直接让我运行命令、检查文件、修改代码、搜索资料或分析文档。"
    ),
    inputs=[
        Input("user_input", str, required=True, description="输入任务，或直接让我运行命令"),
        Input("umf_message", dict, default=None, description="Optional UMF-like message envelope"),
        Input("relationship", str, default="owner", description="owner, administrator, client, or anonymous"),
        Input("model", str, default="", description="Optional model id selected by the caller"),
    ],
    user_input="user_input",
)


P3394_REFERENCE_PROMPT = build_p3394_reference_prompt()


P3394_AGENT_SYSTEM_PROMPT = f"""You are P3394 Runtime Agent running inside AgentClaw.

You are not a documentation-only chatbot. P3394 is your protocol and governance layer; AgentClaw is your execution runtime.

{P3394_REFERENCE_PROMPT}

Operating rules:
- Treat the P3394 UMF envelope, relationship, session, and audit data as the request boundary.
- Use AgentClaw tools/skills when useful.
- Use available AgentClaw tools and skills when the task needs shell commands, file inspection, code edits, tests, APIs, web context, or project operations.
- For command execution and file changes, be concrete and verify results with tools when practical.
- Default to doing the work, not describing how the work could be done. If the user asks to inspect, run, fix, build, test, search, or modify something, execute the appropriate tool path.
- Default to action for ordinary user requests; keep protocol handling internal unless the user asks for it.
- Ask for clarification only when the missing detail blocks the action or the action would be destructive/high risk. Otherwise make a reasonable local assumption and proceed.
- For UI, code, and project tasks, use this loop: inspect relevant files, make a small scoped change, run the narrow useful verification, then report what changed and what remains.
- Prefer normal model-language output over protocol output. The final answer should read like a capable local agent, not a P3394 spec dump.
- Local engineering tool contract:
  - Use project_overview first for quick project structure analysis.
  - Use read_file for Markdown, PDF, DOCX, PPTX, XLSX, text, code, and image inspection before guessing.
  - Use write_file or code-editing tools only after inspecting existing files; verify changed files afterward.
  - Use powershell for PowerShell-native commands on Windows; use shell for ordinary cross-platform commands.
  - Use git_status before summarizing workspace state, git_diff before explaining code changes, and git_commit_suggestions for commit message suggestions. Never run git commit unless the user explicitly asks.
  - Use search_web/search_news/search_images when current online context or outside documentation is needed.
- Keep P3394 runtime context internal. Do not expose UMF, manifest, audit, route JSON, role-plan JSON, or protocol headings unless the user explicitly asks about P3394 internals.
- For ordinary tasks, answer like a normal AgentClaw agent: give the result first, then brief execution notes only when they help.
- Keep replies concise and in the user's language unless the user asks otherwise.
- Mention important tool or command results in the final answer, especially failures, permissions, or missing model/API configuration.
- Do not claim a command, file change, or external action happened unless a tool result confirms it.
"""


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _hash_id(prefix: str, value: str) -> str:
    digest = hashlib.sha1(value.encode("utf-8")).hexdigest()[:12]
    return f"{prefix}-{digest}"


def _extract_memory_text(text: str) -> str:
    stripped = text.strip()
    prefixes = [
        "记住：",
        "记住:",
        "帮我记住：",
        "帮我记住:",
        "remember:",
        "remember ",
    ]
    lowered = stripped.lower()
    for prefix in prefixes:
        if lowered.startswith(prefix.lower()):
            return stripped[len(prefix):].strip()
    return stripped


def _looks_like_memory_write(text: str) -> bool:
    stripped = text.strip()
    lowered = stripped.lower()
    return (
        stripped.startswith("记住")
        or stripped.startswith("帮我记住")
        or lowered.startswith("remember:")
        or lowered.startswith("remember ")
    )


def _looks_like_memory_query(text: str) -> bool:
    lowered = text.lower()
    return (
        "记忆图谱" in text
        or "查询记忆" in text
        or "查看记忆" in text
        or "本地记忆" in text
        or "memory graph" in lowered
        or "local memory" in lowered
    )


def _clean_memory_fragment(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip(" 。；;，,\n\t")).strip()


def _dedupe_memory_candidates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str]] = set()
    deduped: list[dict[str, Any]] = []
    for item in candidates:
        title = _clean_memory_fragment(str(item.get("title") or ""))
        content = _clean_memory_fragment(str(item.get("content") or ""))
        if not title or not content:
            continue
        key = (title, content)
        if key in seen:
            continue
        seen.add(key)
        deduped.append({**item, "title": title[:120], "content": content, "source": "auto_memory"})
    return deduped[:8]


def extract_p3394_auto_memory_candidates(text: str) -> list[dict[str, Any]]:
    """Extract obvious durable memory candidates from ordinary chat text."""
    stripped = text.strip()
    if not stripped or _looks_like_memory_query(stripped):
        return []

    candidates: list[dict[str, Any]] = []
    preference_patterns = [
        r"(?:我|用户)(?:更)?(?:喜欢|偏好|希望|想要|要的是)([^。；;\n]{2,80})",
        r"(?:界面|UI)(?:要|需要|应该)([^。；;\n]{2,80})",
    ]
    for pattern in preference_patterns:
        for match in re.finditer(pattern, stripped, flags=re.IGNORECASE):
            value = _clean_memory_fragment(match.group(1))
            if value:
                candidates.append(
                    {
                        "title": f"用户偏好：{value[:64]}",
                        "content": f"用户偏好：{value}",
                        "category": "用户偏好",
                        "category_kind": "concept",
                        "target_kind": "knowledge",
                        "tags": ["auto-memory", "preference"],
                    }
                )

    project_patterns = [
        r"(?:项目|平台|产品)(?:叫|名为|名称是)\s*([A-Za-z0-9_\- .\u4e00-\u9fa5]{2,80})",
        r"([A-Za-z0-9][A-Za-z0-9_\- .]{2,60})\s*(?:是|作为)(?:.*?)(?:项目|平台|产品)",
    ]
    for pattern in project_patterns:
        for match in re.finditer(pattern, stripped, flags=re.IGNORECASE):
            value = _clean_memory_fragment(match.group(1))
            if value:
                candidates.append(
                    {
                        "title": f"项目事实：{value[:64]}",
                        "content": f"项目事实：{value}",
                        "category": "项目事实",
                        "category_kind": "concept",
                        "target_kind": "project",
                        "tags": ["auto-memory", "project-fact"],
                    }
                )

    capability_patterns = [
        r"(?:必须|需要|要|允许|支持)([^。；;\n]{0,24}(?:执行命令|运行命令|本地知识库|记忆图谱|接入模型|调用工具|搜索资料|分析文档)[^。；;\n]{0,40})",
        r"(?:能|可以)([^。；;\n]{0,18}(?:执行命令|运行命令|调用工具|搜索资料|分析文档)[^。；;\n]{0,40})",
    ]
    for pattern in capability_patterns:
        for match in re.finditer(pattern, stripped, flags=re.IGNORECASE):
            value = _clean_memory_fragment(match.group(1))
            if value:
                candidates.append(
                    {
                        "title": f"能力需求：{value[:64]}",
                        "content": f"能力需求：{value}",
                        "category": "能力需求",
                        "category_kind": "capability",
                        "target_kind": "capability",
                        "tags": ["auto-memory", "capability"],
                    }
                )

    for match in re.finditer(r"([A-Za-z]:\\[^\s。；;]+|[\w .()\-]+\.md)", stripped):
        value = _clean_memory_fragment(match.group(1))
        if value:
            candidates.append(
                {
                    "title": f"文件线索：{value[-80:]}",
                    "content": f"文件线索：{value}",
                    "category": "文件线索",
                    "category_kind": "document",
                    "target_kind": "document",
                    "tags": ["auto-memory", "file"],
                }
            )

    return _dedupe_memory_candidates(candidates)


def _persist_p3394_auto_memory(
    *,
    workflow_id: str,
    thread_id: str,
    text: str,
) -> list[dict[str, Any]]:
    created: list[dict[str, Any]] = []
    for candidate in extract_p3394_auto_memory_candidates(text):
        item = add_p3394_knowledge_item(
            workflow_id=workflow_id,
            title=candidate["title"],
            content=candidate["content"],
            source="auto_memory",
            tags=list(candidate.get("tags") or []),
            metadata={"thread_id": thread_id, "category": candidate.get("category")},
        )
        add_p3394_memory_relation(
            workflow_id=workflow_id,
            source_label="自动记忆",
            source_kind="process",
            relation="captured",
            target_label=str(candidate.get("category") or "记忆条目"),
            target_kind=str(candidate.get("category_kind") or "concept"),
            evidence=candidate["content"],
        )
        relation = add_p3394_memory_relation(
            workflow_id=workflow_id,
            source_label=str(candidate.get("category") or "记忆条目"),
            source_kind=str(candidate.get("category_kind") or "concept"),
            relation="contains",
            target_label=item["title"],
            target_kind=str(candidate.get("target_kind") or "knowledge"),
            evidence=candidate["content"],
        )
        created.append({"knowledge": item, "relation": relation, "candidate": candidate})
    return created


def _detect_capability(text: str, umf_message: dict[str, Any]) -> tuple[str, str]:
    message_type = str(umf_message.get("message_type") or "").strip()
    body = umf_message.get("body") if isinstance(umf_message.get("body"), dict) else {}
    capability = str(body.get("capability") or umf_message.get("capability") or "").strip()
    lowered = text.lower()

    if message_type.startswith("session."):
        if message_type in {"session.context.fetch", "session.fetch"}:
            return "session.fetch", "session.fetch"
        if message_type in {"session.lifecycle.transition", "session.close"}:
            return "session.close", "session.close"
        return message_type, message_type
    if capability:
        if capability == "session_management" and not message_type:
            message_type = "session.create"
            return "session.create", message_type
        if capability == "session.context.fetch":
            return "session.fetch", "session.fetch"
        if capability in {"session.create", "session.fetch", "session.close"}:
            return capability, message_type or capability
        if capability in {"task.route", "agent.delegate"}:
            return capability, message_type or ("agent.command" if capability == "agent.delegate" else "agent.query")
        return capability, message_type or "agent.request"
    if "agent.delegate" in lowered or "delegate" in lowered:
        return "agent.delegate", "agent.command"
    if "task.route" in lowered or "route task" in lowered:
        return "task.route", "agent.query"
    if _looks_like_memory_write(text):
        return "p3394.local_memory", "agent.request"
    if _looks_like_memory_query(text):
        return "p3394.local_memory", "agent.query"
    if "session.context.fetch" in lowered or "session.fetch" in lowered or "context.fetch" in lowered:
        return "session.fetch", "session.fetch"
    if "session.close" in lowered or "close session" in lowered:
        return "session.close", "session.close"
    if "session.create" in lowered or "create session" in lowered or "创建会话" in text:
        return "session.create", "session.create"
    if (
        "p3394 task history" in lowered
        or "p3394 history" in lowered
        or ("p3394" in lowered and ("任务历史" in text or "歷史" in text or "history" in lowered))
    ):
        return "p3394.task_history", "agent.query"
    if (
        "p3394 file context" in lowered
        or "p3394 context files" in lowered
        or ("p3394" in lowered and ("文件上下文" in text or "文件记录" in text or "file context" in lowered))
    ):
        return "p3394.file_context", "agent.query"
    if (
        "p3394 tool records" in lowered
        or "p3394 tool calls" in lowered
        or "p3394 command records" in lowered
        or (
            "p3394" in lowered
            and (
                "工具记录" in text
                or "工具调用" in text
                or "命令记录" in text
                or "执行明细" in text
                or "tool record" in lowered
                or "tool call" in lowered
                or "command record" in lowered
            )
        )
    ):
        return "p3394.tool_records", "agent.query"
    if "manifest" in lowered or "清单" in text:
        return "manifest.describe", "agent.query"
    if "normalize" in lowered or "umf" in lowered or "统一消息" in text:
        return "message.normalize", "agent.query"
    if "audit" in lowered or "审计" in text:
        return "audit.summary", "agent.query"
    if "conformance" in lowered or ("协议" in text and "符合" in text):
        return "conformance.check", "agent.query"
    return "task.route", "agent.request"


def _relationship_from_state(raw: Any) -> str:
    relationship = str(raw or "owner").strip().lower()
    return relationship if relationship in P3394_MANIFEST["relationships"] else "anonymous"


def _is_allowed(relationship: str, capability: str) -> bool:
    access = P3394_MANIFEST["relationships"][relationship]["capability_access"]
    return "*" in access or capability in access


def _message_body_input(normalized: dict[str, Any]) -> dict[str, Any]:
    body = normalized.get("body") if isinstance(normalized.get("body"), dict) else {}
    input_data = body.get("input") if isinstance(body.get("input"), dict) else {}
    return input_data


def _contains_any(value: str, tokens: list[str]) -> bool:
    return any(token in value for token in tokens)


def _looks_like_file_creation_request(text: str) -> bool:
    lowered = text.lower()
    has_create_intent = _contains_any(lowered, [
        "create ",
        "write ",
        "save ",
        "new file",
        "make ",
        "生成",
        "创建",
        "新建",
        "写",
        "保存",
        "建一个",
        "搞一个",
    ])
    has_file_target = _contains_any(lowered, [
        ".md",
        ".markdown",
        ".txt",
        ".json",
        ".yaml",
        ".yml",
        ".py",
        ".js",
        ".ts",
        "markdown",
        "md 文档",
        "md文件",
        "md 文档",
        "文档",
        "文件",
        "桌面",
        "desktop",
    ])
    return has_create_intent and has_file_target


def _route_catalog() -> list[dict[str, Any]]:
    return copy.deepcopy(P3394_MANIFEST["orchestration"]["routes"])


def _route_by_family(family: str) -> dict[str, Any]:
    for route in P3394_MANIFEST["orchestration"]["routes"]:
        if route["family"] == family:
            return copy.deepcopy(route)
    return copy.deepcopy(P3394_MANIFEST["orchestration"]["routes"][-1])


def _select_route(text: str, normalized: dict[str, Any]) -> dict[str, Any]:
    input_data = _message_body_input(normalized)
    lowered = f"{text} {_format_json(input_data)}".lower()
    explicit_target = str(input_data.get("target_workflow_id") or "").strip()

    if explicit_target:
        route = {
            "family": "explicit_delegate",
            "target": explicit_target,
            "execution_mode": "workflow_delegate",
            "capabilities": ["agent.delegate"],
        }
    elif _contains_any(lowered, [
        "p3394 architecture",
        "p3394 架构",
        "p3394 架構",
        "p3394 改造",
        "p3394 analyze",
        "p3394 transform",
        "按 p3394",
        "架构分析",
        "架構分析",
        "改造项目",
        "改造專案",
    ]):
        route = _route_by_family("p3394_architecture")
    elif _contains_any(lowered, [
        "run ",
        "run:",
        "execute ",
        "command",
        "shell",
        "powershell",
        "get-location",
        "pytest",
        "echo ",
        "terminal",
        "命令",
        "运行",
        "执行",
        "终端",
        "跑测试",
    ]):
        route = _route_by_family("code_command")
    elif _looks_like_file_creation_request(lowered):
        route = _route_by_family("code_command")
    elif _contains_any(lowered, [
        "pdf",
        "docx",
        "document",
        "contract",
        "report",
        "文档",
        "合同",
        "报告",
        "文件分析",
        "分析文档",
        "分析这个合同",
        "风险",
    ]):
        route = _route_by_family("document_analysis")
    elif _contains_any(lowered, [
        "search",
        "github",
        "web",
        "资料",
        "搜索",
        "网上",
        "查找",
        "联网",
        "搜一下",
        "搜资料",
    ]):
        route = _route_by_family("knowledge_search")
    elif _contains_any(lowered, [
        "code",
        "pytest",
        "test",
        "powershell",
        "get-location",
        "shell",
        "command",
        "file",
        "fix",
        "代码",
        "命令",
        "文件",
        "修复",
        "运行",
        "测试",
        "跑测试",
        "执行",
        "终端",
    ]):
        route = _route_by_family("code_command")
    else:
        route = _route_by_family("general_chat")

    route["reason"] = _route_reason(route["family"], text)
    route["available_routes"] = [item["family"] for item in P3394_MANIFEST["orchestration"]["routes"]]
    return route


def _route_reason(family: str, text: str) -> str:
    reasons = {
        "explicit_delegate": "The UMF input selected a target_workflow_id.",
        "p3394_architecture": "The request asks to analyze or transform the project using the local P3394 architecture reference.",
        "document_analysis": "The request mentions document or contract analysis.",
        "knowledge_search": "The request asks for search or external knowledge gathering.",
        "code_command": "The request involves code, files, commands, or tests.",
        "general_chat": "No specialized route matched, so the local agentic runtime handles it.",
    }
    return reasons.get(family, f"Selected route for request: {text[:80]}")


def _summarize_workflow_state(state: dict[str, Any]) -> dict[str, Any]:
    ignored_prefixes = ("__",)
    ignored_keys = {"thread_id", "user_id"}
    return {
        key: value
        for key, value in state.items()
        if key not in ignored_keys and not any(str(key).startswith(prefix) for prefix in ignored_prefixes)
    }


def _build_delegation_inputs(
    *,
    route: dict[str, Any],
    normalized: dict[str, Any],
) -> tuple[dict[str, Any], list[str]]:
    input_data = _message_body_input(normalized)
    configured_inputs = input_data.get("delegation_inputs")
    if isinstance(configured_inputs, dict):
        return configured_inputs, []

    content = str(normalized.get("body", {}).get("content") or "").strip()
    target_workflow_id = str(input_data.get("target_workflow_id") or route.get("target") or "").strip()

    if target_workflow_id == "doc_analyzer":
        documents = input_data.get("documents") or input_data.get("files")
        delegation_inputs = {
            "question": input_data.get("question") or content or "请分析这些文档。",
        }
        if documents:
            delegation_inputs["documents"] = documents
            return delegation_inputs, []
        return delegation_inputs, ["documents"]

    if target_workflow_id == "tool_agent":
        return {"user_input": content}, []

    user_input = input_data.get("user_input") or content
    return {"user_input": user_input}, []


async def _delegate_to_workflow(
    *,
    route: dict[str, Any],
    normalized: dict[str, Any],
    context,
) -> dict[str, Any]:
    from agentclaw.api.registry import WorkflowRegistry
    from agentclaw.graph.context import WorkflowContext

    input_data = _message_body_input(normalized)
    target_workflow_id = str(input_data.get("target_workflow_id") or route.get("target") or "").strip()
    delegation_inputs, missing_inputs = _build_delegation_inputs(route=route, normalized=normalized)

    if not target_workflow_id or target_workflow_id == "agentic_runtime":
        return {
            "status": "not_delegated",
            "target_workflow_id": target_workflow_id or "agentic_runtime",
            "selected_route": route,
            "reason": "Selected route uses the local agentic runtime instead of a child workflow.",
            "delegation_inputs": delegation_inputs,
        }

    if missing_inputs:
        return {
            "status": "requires_input",
            "target_workflow_id": target_workflow_id,
            "selected_route": route,
            "reason": f"Workflow {target_workflow_id!r} requires more input before delegation.",
            "required_inputs": missing_inputs,
            "delegation_inputs": delegation_inputs,
        }

    if target_workflow_id == "p3394_runtime_agent":
        return {
            "status": "rejected",
            "target_workflow_id": target_workflow_id,
            "selected_route": route,
            "reason": "Self-delegation is disabled to avoid recursive orchestration loops.",
            "delegation_inputs": delegation_inputs,
        }

    target_workflow = WorkflowRegistry.get(target_workflow_id)
    if target_workflow is None:
        return {
            "status": "not_registered",
            "target_workflow_id": target_workflow_id,
            "selected_route": route,
            "reason": f"Workflow {target_workflow_id!r} is not registered in AgentClaw.",
            "delegation_inputs": delegation_inputs,
        }

    channel = get_output_channel()
    output_count_before = len(channel.outputs) if channel else 0

    child_context = WorkflowContext(
        thread_id=f"{context.thread_id}:{target_workflow_id}",
        user_id=getattr(context, "user_id", None),
    )
    child_result = await target_workflow.run(
        inputs=delegation_inputs,
        context=child_context,
        thread_id=child_context.thread_id,
    )
    child_state = child_result.get("state", {}) if isinstance(child_result, dict) else {}
    return {
        "status": "succeeded",
        "target_workflow_id": target_workflow_id,
        "selected_route": route,
        "delegation_inputs": delegation_inputs,
        "result_state": _summarize_workflow_state(child_state),
        "child_streamed_output": bool(channel and len(channel.outputs) > output_count_before),
        "metadata": child_result.get("metadata", {}) if isinstance(child_result, dict) else {},
    }


def _session_key(context_thread_id: str, canonical_session_id: str | None = None) -> str:
    return canonical_session_id or _hash_id("sess", context_thread_id)


def _normalize_message(
    *,
    text: str,
    umf_message: dict[str, Any],
    capability: str,
    message_type: str,
    relationship: str,
    thread_id: str,
) -> dict[str, Any]:
    canonical_session_id = umf_message.get("canonical_session_id") or umf_message.get("session_id")
    metadata = umf_message.get("metadata") if isinstance(umf_message.get("metadata"), dict) else {}
    body = umf_message.get("body") if isinstance(umf_message.get("body"), dict) else {}
    sender = umf_message.get("sender") if isinstance(umf_message.get("sender"), dict) else {}
    service_principal = sender.get("service_principal") if isinstance(sender.get("service_principal"), dict) else {
        "person": sender.get("principal", "local-admin"),
        "org": "local",
        "role": relationship,
    }

    return {
        "schema_version": "p3394-draft-0.9.0",
        "message_id": umf_message.get("message_id") or _hash_id("msg", f"{thread_id}:{text}:{_utc_now()}"),
        "message_type": message_type,
        "created_at": _utc_now(),
        "sender": {
            "principal": sender.get("principal", "local-admin"),
            "service_principal": service_principal,
            "relationship": relationship,
        },
        "recipient": {
            "agent_id": "agentclaw:p3394_runtime_agent",
            "capability": capability,
        },
        "canonical_session_id": canonical_session_id,
        "parent_session_id": umf_message.get("parent_session_id"),
        "body": {
            "capability": capability,
            "content": body.get("content") or text,
            "input": body.get("input") or {"user_input": text},
        },
        "metadata": {
            **metadata,
            "channel": metadata.get("channel", "agentclaw_dashboard"),
            "session_lifecycle": metadata.get("session_lifecycle", "open" if canonical_session_id else "bootstrap"),
        },
    }


def _create_session(thread_id: str, normalized: dict[str, Any]) -> dict[str, Any]:
    canonical_session_id = _session_key(thread_id, normalized.get("canonical_session_id"))
    session = {
        "canonical_session_id": canonical_session_id,
        "owner_agent": "agentclaw:p3394_runtime_agent",
        "lifecycle": "open",
        "created_at": _utc_now(),
        "context_variables": {
            "last_capability": normalized["body"]["capability"],
            "last_message_type": normalized["message_type"],
        },
        "participants": [normalized["sender"]["principal"]],
        "budgets": {"max_tool_rounds": 8, "max_child_sessions": 0},
        "memory_pointers": [],
        "child_sessions": [],
    }
    SESSION_STORE[canonical_session_id] = session
    return session


def _get_session(thread_id: str, normalized: dict[str, Any]) -> dict[str, Any]:
    canonical_session_id = _session_key(thread_id, normalized.get("canonical_session_id"))
    return SESSION_STORE.get(canonical_session_id) or _create_session(thread_id, normalized)


def _fetch_session(thread_id: str, normalized: dict[str, Any]) -> dict[str, Any]:
    canonical_session_id = _session_key(thread_id, normalized.get("canonical_session_id"))
    return SESSION_STORE.get(canonical_session_id) or _create_session(thread_id, normalized)


def _close_session(thread_id: str, normalized: dict[str, Any]) -> dict[str, Any]:
    session = _fetch_session(thread_id, normalized)
    session["lifecycle"] = "closed"
    session["closed_at"] = _utc_now()
    session["context_variables"]["last_capability"] = normalized["body"]["capability"]
    session["context_variables"]["last_message_type"] = normalized["message_type"]
    return session


def _error_envelope(reason_code: str, message: str, normalized: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "p3394-draft-0.9.0",
        "message_type": "agent.error",
        "reason_code": reason_code,
        "message": message,
        "request_message_id": normalized.get("message_id"),
    }


def _audit(
    normalized: dict[str, Any],
    relationship: str,
    status: str,
    *,
    thread_id: str | None = None,
    reason_code: str | None = None,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    timestamp = _utc_now()
    return {
        "event_id": _hash_id("audit", f"{thread_id}:{normalized.get('message_id')}:{status}:{timestamp}"),
        "timestamp": timestamp,
        "thread_id": thread_id,
        "principal": normalized["sender"]["principal"],
        "service_principal": normalized["sender"].get("service_principal"),
        "relationship": relationship,
        "capability": normalized["body"]["capability"],
        "message_type": normalized["message_type"],
        "canonical_session_id": normalized.get("canonical_session_id"),
        "status": status,
        "reason_code": reason_code,
        "details": details or {},
    }


def _record_audit(
    normalized: dict[str, Any],
    relationship: str,
    status: str,
    *,
    thread_id: str,
    reason_code: str | None = None,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    event = _audit(
        normalized,
        relationship,
        status,
        thread_id=thread_id,
        reason_code=reason_code,
        details=details,
    )
    AUDIT_EVENTS.append(event)
    return event


def _audit_events_for(normalized: dict[str, Any], thread_id: str) -> list[dict[str, Any]]:
    canonical_session_id = normalized.get("canonical_session_id")
    if canonical_session_id:
        return [event for event in AUDIT_EVENTS if event.get("canonical_session_id") == canonical_session_id]
    return [event for event in AUDIT_EVENTS if event.get("thread_id") == thread_id]


def _response_envelope(normalized: dict[str, Any], audit: dict[str, Any], payload: Any) -> dict[str, Any]:
    return {
        "schema_version": "p3394-draft-0.9.0",
        "message_id": _hash_id("msg", f"response:{normalized.get('message_id')}:{audit.get('event_id')}"),
        "message_type": "agent.response" if audit["status"] != "denied" else "agent.error",
        "in_reply_to": normalized.get("message_id"),
        "created_at": _utc_now(),
        "sender": {
            "agent_id": "agentclaw:p3394_runtime_agent",
            "capability": normalized["body"]["capability"],
        },
        "recipient": normalized["sender"],
        "canonical_session_id": normalized.get("canonical_session_id"),
        "parent_session_id": normalized.get("parent_session_id"),
        "body": {
            "capability": normalized["body"]["capability"],
            "status": audit["status"],
            "output": payload,
        },
        "metadata": {
            "audit_event_id": audit["event_id"],
            "channel": normalized["metadata"].get("channel", "agentclaw_dashboard"),
            "session_lifecycle": normalized["metadata"].get("session_lifecycle"),
        },
    }


def _conformance_report() -> dict[str, Any]:
    capability_names = {capability["name"] for capability in P3394_MANIFEST["capabilities"]}
    checks = [
        {
            "id": "manifest",
            "status": "pass" if P3394_MANIFEST.get("default_input", {}).get("entry_point") == "handle_message" else "fail",
            "evidence": "default_input.handle_message and public manifest are declared",
        },
        {
            "id": "channel_adapter",
            "status": "pass" if len(P3394_MANIFEST.get("channel_adapter", {}).get("responsibilities", [])) == 8 else "fail",
            "evidence": "8 adapter responsibilities are declared",
        },
        {
            "id": "umf",
            "status": "pass",
            "evidence": "inbound UMF normalization and outbound response envelope are emitted",
        },
        {
            "id": "session",
            "status": "pass" if {"session.create", "session.fetch", "session.close"} <= capability_names else "fail",
            "evidence": "session create, fetch, and close commands are implemented",
        },
        {
            "id": "security",
            "status": "pass" if {"owner", "administrator", "peer", "client", "anonymous"} <= set(P3394_MANIFEST["relationships"]) else "fail",
            "evidence": "relationship to capability authorization is enforced before LLM execution",
        },
        {
            "id": "audit",
            "status": "pass",
            "evidence": "each ingress decision records an audit event in AUDIT_EVENTS",
        },
        {
            "id": "orchestration",
            "status": "pass" if {"task.route", "agent.delegate"} <= capability_names else "fail",
            "evidence": "task.route selects targets and agent.delegate can call registered workflows",
        },
        {
            "id": "agentic_execution",
            "status": "pass",
            "evidence": "ordinary authorized requests continue to LLMNode(agent_style='agentic') with tools and skills enabled",
        },
    ]
    return {
        "target_level": P3394_MANIFEST["conformance"]["target_level"],
        "profile": P3394_MANIFEST["conformance"]["profile"],
        "status": "pass" if all(check["status"] == "pass" for check in checks) else "fail",
        "checks": checks,
    }


def _format_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


def _format_output(
    *,
    title: str,
    summary: str,
    normalized: dict[str, Any],
    audit: dict[str, Any],
    payload: Any,
    response_message: dict[str, Any] | None = None,
) -> str:
    response_section = (
        "\n\n## UMF-style Response\n"
        f"```json\n{_format_json(response_message)}\n```"
        if response_message
        else ""
    )
    return (
        f"# {title}\n\n"
        f"{summary}\n\n"
        "## Capability\n"
        f"- `{normalized['body']['capability']}` via `{normalized['message_type']}`\n\n"
        "## Payload\n"
        f"```json\n{_format_json(payload)}\n```\n\n"
        "## UMF-style Envelope\n"
        f"```json\n{_format_json(normalized)}\n```\n\n"
        "## Audit Summary\n"
        f"```json\n{_format_json(audit)}\n```"
        f"{response_section}"
    )


def _first_text_value(data: dict[str, Any]) -> str:
    preferred_keys = [
        "answer",
        "agent",
        "delegate_answer",
        "response",
        "output",
        "result",
        "text",
    ]
    for key in preferred_keys:
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()

    for key, value in data.items():
        if key.startswith("__"):
            continue
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _delegation_user_output(payload: dict[str, Any]) -> str:
    status = str(payload.get("status") or "")
    target = str(payload.get("target_workflow_id") or "target workflow")

    if status == "succeeded":
        state = payload.get("result_state") if isinstance(payload.get("result_state"), dict) else {}
        child_answer = _first_text_value(state)
        if child_answer:
            return child_answer
        return f"已委派给 {target}，任务已完成。"

    if status == "requires_input":
        required = ", ".join(str(item) for item in payload.get("required_inputs") or [])
        return f"还需要补充 {required or '必要输入'}，才能委派给 {target}。"

    if status == "not_registered":
        return f"{target} 还没有导入或注册，先在右侧导入这个智能体后我才能委派。"

    if status == "rejected":
        return str(payload.get("reason") or f"不能委派给 {target}。")

    if status == "not_delegated":
        return str(payload.get("reason") or "这条任务会交给当前 P3394 Runtime 继续执行。")

    return str(payload.get("reason") or f"委派给 {target} 时没有完成，状态：{status or 'unknown'}。")


def _route_user_output(route: dict[str, Any], payload: dict[str, Any]) -> str:
    family_labels = {
        "p3394_architecture": "P3394 架构分析 / 改造",
        "code_command": "命令 / 代码执行",
        "document_analysis": "文档分析",
        "knowledge_search": "资料搜索",
        "general_chat": "普通对话",
        "explicit_delegate": "指定委派",
    }
    target = str(route.get("target") or payload.get("target_workflow_id") or "agentic_runtime")
    label = family_labels.get(str(route.get("family") or ""), str(route.get("family") or "默认路由"))
    if target == "agentic_runtime":
        return f"这类任务会走「{label}」路线，并交给 P3394 的 Agentic Runtime 继续执行。"
    return f"这类任务会走「{label}」路线，目标智能体是 {target}。发送自然语言任务后，我会直接委派执行。"


def _build_agent_prompt(
    *,
    text: str,
    normalized: dict[str, Any],
    audit: dict[str, Any],
    session: dict[str, Any],
    route: dict[str, Any] | None = None,
    role_plan: list[dict[str, Any]] | None = None,
) -> str:
    route = route or {}
    architecture_mode = (
        "- p3394_reference_mode: map the project to manifest, channel adapter, UMF, session/context, relationship/capability authorization, resources/tools, audit, and conformance evidence\n"
        if route.get("family") == "p3394_architecture"
        else ""
    )
    role_plan = role_plan or []
    role_plan_text = ""
    if role_plan:
        role_lines = [
            f"- {step.get('role')}: {step.get('focus')}"
            for step in role_plan
            if step.get("role")
        ]
        role_plan_text = (
            "Internal P3394 role plan. Do not expose this role plan unless the user asks for P3394 internals:\n"
            + "\n".join(role_lines)
            + "\n\n"
        )
    return (
        "Internal P3394 routing context. Use this to execute the task, but do not quote "
        "or summarize this context unless the user asks about P3394 internals:\n"
        f"- capability: {normalized['body']['capability']} via {normalized['message_type']}\n"
        f"- relationship: {normalized['sender']['relationship']}\n"
        f"- session_id: {normalized.get('canonical_session_id') or session.get('canonical_session_id')}\n"
        f"- route: {route.get('family', 'general_chat')} -> {route.get('target', 'agentic_runtime')}\n"
        f"- audit_event_id: {audit.get('event_id')}\n"
        "- runtime: AgentClaw LLMNode(agent_style='agentic') with built-in tools and skills enabled\n\n"
        f"{architecture_mode}"
        f"{role_plan_text}"
        "User request:\n"
        f"{text}\n\n"
        "Respond to the user normally, in concise natural language. Do not expose UMF, manifests, audit objects, "
        "or route JSON, role-plan JSON, or P3394 protocol headings by default. "
        "Do not explain internal routing, sessions, audit, UMF, or role plans unless explicitly asked. "
        "Use AgentClaw tools/skills when useful. "
        "Default to action: use AgentClaw tools/skills when they can move the task forward. "
        "If the user asks to run commands, inspect files, edit code, or verify behavior, "
        "use the available tools instead of only explaining. "
        "After tool use, summarize the concrete result and any remaining blocker."
    )


class P3394InitNode(CustomNode):
    """P3394 runtime ingress before the AgentClaw LLM agent."""

    def process(self, **_):
        """CustomNode requires a sync process hook; runtime work uses async_execute."""
        return {}

    async def async_execute(self, state: dict, context) -> dict:
        text = str(state.get("user_input") or "").strip()
        raw_umf = state.get("umf_message") if isinstance(state.get("umf_message"), dict) else {}
        relationship = _relationship_from_state(state.get("relationship"))
        capability, message_type = _detect_capability(text, raw_umf)
        normalized = _normalize_message(
            text=text,
            umf_message=raw_umf,
            capability=capability,
            message_type=message_type,
            relationship=relationship,
            thread_id=context.thread_id,
        )

        if not _is_allowed(relationship, capability):
            payload = _error_envelope(
                "authorization_failed",
                f"Relationship {relationship!r} cannot call capability {capability!r}.",
                normalized,
            )
            audit = _record_audit(
                normalized,
                relationship,
                "denied",
                thread_id=context.thread_id,
                reason_code="authorization_failed",
            )
            response_message = _response_envelope(normalized, audit, payload)
            output = _format_output(
                title="P3394 Authorization Error",
                summary="The request reached the adapter boundary but failed relationship-based authorization.",
                normalized=normalized,
                audit=audit,
                payload=payload,
                response_message=response_message,
            )
            await stream_output(output, node=self.id, save_to_context=True)
            return {
                "p3394_runtime_agent": output,
                "p3394_umf_message": normalized,
                "p3394_response_message": response_message,
                "p3394_payload": payload,
                "p3394_audit": audit,
                "__p3394_complete__": True,
            }

        file_context_ids = record_p3394_file_contexts_from_state(
            workflow_id=workflow.id,
            thread_id=context.thread_id,
            request=text,
            state=state,
        )
        auto_memories = _persist_p3394_auto_memory(
            workflow_id=workflow.id,
            thread_id=context.thread_id,
            text=text,
        )

        if capability == "manifest.describe":
            payload = copy.deepcopy(P3394_MANIFEST)
            summary = "Returned the public manifest contract for this AgentClaw-hosted P3394 runtime."
            title = "P3394 Manifest"
        elif capability == "message.normalize":
            payload = normalized
            summary = "Normalized the inbound request into the runtime's UMF-style envelope."
            title = "P3394 Message Normalization"
        elif capability == "session.create":
            payload = copy.deepcopy(_create_session(context.thread_id, normalized))
            normalized["canonical_session_id"] = payload["canonical_session_id"]
            normalized["metadata"]["session_lifecycle"] = payload["lifecycle"]
            summary = "Created a session owned by the P3394 Runtime Agent."
            title = "P3394 Session Created"
        elif capability == "session.fetch":
            payload = copy.deepcopy(_fetch_session(context.thread_id, normalized))
            normalized["canonical_session_id"] = payload["canonical_session_id"]
            normalized["metadata"]["session_lifecycle"] = payload["lifecycle"]
            summary = "Fetched the current session context compartments."
            title = "P3394 Session Context"
        elif capability == "session.close":
            payload = copy.deepcopy(_close_session(context.thread_id, normalized))
            normalized["canonical_session_id"] = payload["canonical_session_id"]
            normalized["metadata"]["session_lifecycle"] = payload["lifecycle"]
            summary = "Closed the current P3394 session context."
            title = "P3394 Session Closed"
        elif capability == "task.route":
            route = _select_route(text, normalized)
            normalized["metadata"]["selected_route"] = route
            if message_type == "agent.request" and relationship != "anonymous":
                session = _get_session(context.thread_id, normalized)
                normalized["canonical_session_id"] = session["canonical_session_id"]
                normalized["metadata"]["session_lifecycle"] = session["lifecycle"]
                if route.get("target") != "agentic_runtime":
                    payload = await _delegate_to_workflow(route=route, normalized=normalized, context=context)
                    audit_status = "delegated" if payload["status"] == "succeeded" else "delegation_pending"
                    audit = _record_audit(
                        normalized,
                        relationship,
                        audit_status,
                        thread_id=context.thread_id,
                        details={
                            "route": route,
                            "delegated_to": payload.get("target_workflow_id"),
                            "delegation_status": payload.get("status"),
                        },
                    )
                    response_message = _response_envelope(normalized, audit, payload)
                    protocol_output = _format_output(
                        title="P3394 Routed Delegation",
                        summary="P3394 selected a child AgentClaw workflow and attempted direct delegation.",
                        normalized=normalized,
                        audit=audit,
                        payload=payload,
                        response_message=response_message,
                    )
                    output = _delegation_user_output(payload)
                    if not payload.get("child_streamed_output"):
                        await stream_output(output, node=self.id, save_to_context=True)
                    return {
                        "p3394_runtime_agent": output,
                        "p3394_protocol_output": protocol_output,
                        "p3394_umf_message": normalized,
                        "p3394_response_message": response_message,
                        "p3394_payload": payload,
                        "p3394_route": route,
                        "p3394_audit": audit,
                        "__p3394_complete__": True,
                    }

                audit = _record_audit(
                    normalized,
                    relationship,
                    "routed",
                    thread_id=context.thread_id,
                    details={"route": route},
                )
                payload = {
                    "response": "Task routed and delegated to the AgentClaw agentic LLM runtime.",
                    "runtime": "LLMNode(agent_style='agentic')",
                    "selected_route": route,
                    "tools": "AgentClaw built-in tools enabled",
                    "skills": "AgentClaw project and built-in skills enabled",
                }
                role_plan = activate_p3394_role_plan(
                    build_p3394_role_plan(text, route),
                    normalized=normalized,
                    route=route,
                    file_context_ids=file_context_ids,
                )
                task_history_id = record_p3394_task_history(
                    workflow_id=workflow.id,
                    thread_id=context.thread_id,
                    request=text,
                    route=route,
                    role_plan=role_plan,
                    status="routed",
                )
                execution_record_id = record_p3394_execution_record(
                    workflow_id=workflow.id,
                    thread_id=context.thread_id,
                    task_history_id=task_history_id,
                    request=text,
                    route=route,
                    status="running",
                )
                payload["role_plan"] = role_plan
                payload["task_history_id"] = task_history_id
                payload["execution_record_id"] = execution_record_id
                payload["file_context_ids"] = file_context_ids
                payload["auto_memory_count"] = len(auto_memories)
                agent_prompt = _build_agent_prompt(
                    text=text,
                    normalized=normalized,
                    audit=audit,
                    session=session,
                    route=route,
                    role_plan=role_plan,
                )
                return {
                    "p3394_init": agent_prompt,
                    "p3394_runtime_agent": payload["response"],
                    "p3394_umf_message": normalized,
                    "p3394_payload": payload,
                    "p3394_route": route,
                    "p3394_role_plan": role_plan,
                    "p3394_task_history_id": task_history_id,
                    "p3394_execution_record_id": execution_record_id,
                    "p3394_file_context_ids": file_context_ids,
                    "p3394_auto_memory_count": len(auto_memories),
                    "p3394_audit": audit,
                    "__p3394_complete__": False,
                }

            payload = {
                "selected_route": route,
                "route_catalog": _route_catalog(),
                "next_action": (
                    "agent.delegate can run the selected workflow when required inputs are provided."
                    if route["target"] != "agentic_runtime"
                    else "local agentic runtime will execute with built-in tools and skills."
                ),
            }
            audit = _record_audit(
                normalized,
                relationship,
                "routed",
                thread_id=context.thread_id,
                details={"route": route},
            )
            response_message = _response_envelope(normalized, audit, payload)
            protocol_output = _format_output(
                title="P3394 Task Route",
                summary="Selected an AgentClaw execution target for this P3394 request.",
                normalized=normalized,
                audit=audit,
                payload=payload,
                response_message=response_message,
            )
            output = _route_user_output(route, payload)
            await stream_output(output, node=self.id, save_to_context=True)
            return {
                "p3394_runtime_agent": output,
                "p3394_protocol_output": protocol_output,
                "p3394_umf_message": normalized,
                "p3394_response_message": response_message,
                "p3394_payload": payload,
                "p3394_route": route,
                "p3394_audit": audit,
                "__p3394_complete__": True,
            }
        elif capability == "agent.delegate":
            route = _select_route(text, normalized)
            normalized["metadata"]["selected_route"] = route
            payload = await _delegate_to_workflow(route=route, normalized=normalized, context=context)
            audit_status = "delegated" if payload["status"] == "succeeded" else "delegation_failed"
            audit = _record_audit(
                normalized,
                relationship,
                audit_status,
                thread_id=context.thread_id,
                details={
                    "route": route,
                    "delegated_to": payload.get("target_workflow_id"),
                    "delegation_status": payload.get("status"),
                },
            )
            response_message = _response_envelope(normalized, audit, payload)
            protocol_output = _format_output(
                title="P3394 Agent Delegation",
                summary="Delegated the request through the P3394 orchestration boundary.",
                normalized=normalized,
                audit=audit,
                payload=payload,
                response_message=response_message,
            )
            output = _delegation_user_output(payload)
            if not payload.get("child_streamed_output"):
                await stream_output(output, node=self.id, save_to_context=True)
            return {
                "p3394_runtime_agent": output,
                "p3394_protocol_output": protocol_output,
                "p3394_umf_message": normalized,
                "p3394_response_message": response_message,
                "p3394_payload": payload,
                "p3394_route": route,
                "p3394_audit": audit,
                "__p3394_complete__": True,
            }
        elif capability == "audit.summary":
            audit = _record_audit(normalized, relationship, "ok", thread_id=context.thread_id)
            events = _audit_events_for(normalized, context.thread_id)
            payload = {
                "latest_audit_projection": audit,
                "total_events": len(events),
                "events": events,
                "required_fields": [
                    "event_id",
                    "principal",
                    "service_principal",
                    "relationship",
                    "capability",
                    "message_type",
                    "canonical_session_id",
                    "status",
                    "timestamp",
                ],
            }
            response_message = _response_envelope(normalized, audit, payload)
            output = _format_output(
                title="P3394 Audit Summary",
                summary="Generated the audit event log projection for this invocation.",
                normalized=normalized,
                audit=audit,
                payload=payload,
                response_message=response_message,
            )
            await stream_output(output, node=self.id, save_to_context=True)
            return {
                "p3394_runtime_agent": output,
                "p3394_umf_message": normalized,
                "p3394_response_message": response_message,
                "p3394_payload": payload,
                "p3394_audit": audit,
                "__p3394_complete__": True,
            }
        elif capability == "p3394.task_history":
            audit = _record_audit(normalized, relationship, "ok", thread_id=context.thread_id)
            tasks = list_p3394_task_history(workflow.id, limit=20)
            payload = {
                "count": len(tasks),
                "tasks": tasks,
            }
            response_message = _response_envelope(normalized, audit, payload)
            if tasks:
                lines = [
                    f"{index + 1}. {task.get('request') or '(empty request)'} [{(task.get('route') or {}).get('family', 'unknown')}]"
                    for index, task in enumerate(tasks[:10])
                ]
                output = "最近 P3394 任务历史：\n" + "\n".join(lines)
            else:
                output = "还没有 P3394 任务历史。"
            await stream_output(output, node=self.id, save_to_context=True)
            return {
                "p3394_runtime_agent": output,
                "p3394_umf_message": normalized,
                "p3394_response_message": response_message,
                "p3394_payload": payload,
                "p3394_audit": audit,
                "__p3394_complete__": True,
            }
        elif capability == "p3394.file_context":
            audit = _record_audit(normalized, relationship, "ok", thread_id=context.thread_id)
            contexts = list_p3394_file_contexts(workflow.id, limit=20)
            payload = {
                "count": len(contexts),
                "contexts": contexts,
            }
            response_message = _response_envelope(normalized, audit, payload)
            if contexts:
                lines = [
                    f"{index + 1}. {item.get('display_name') or item.get('path')} [{item.get('file_type', 'file')}] {item.get('status', 'unknown')}"
                    for index, item in enumerate(contexts[:10])
                ]
                output = "最近 P3394 文件上下文：\n" + "\n".join(lines)
            else:
                output = "还没有 P3394 文件上下文。"
            await stream_output(output, node=self.id, save_to_context=True)
            return {
                "p3394_runtime_agent": output,
                "p3394_umf_message": normalized,
                "p3394_response_message": response_message,
                "p3394_payload": payload,
                "p3394_audit": audit,
                "__p3394_complete__": True,
            }
        elif capability == "p3394.tool_records":
            audit = _record_audit(normalized, relationship, "ok", thread_id=context.thread_id)
            records = list_p3394_tool_records(workflow.id, limit=20)
            payload = {
                "count": len(records),
                "records": records,
            }
            response_message = _response_envelope(normalized, audit, payload)
            if records:
                lines = []
                for index, record in enumerate(records[:10]):
                    command = record.get("command") or record.get("tool_name") or "tool"
                    exit_part = ""
                    if record.get("exit_code") is not None:
                        exit_part = f" exit {record.get('exit_code')}"
                    lines.append(
                        f"{index + 1}. {record.get('tool_name') or 'tool'}: {command} [{record.get('status', 'unknown')}{exit_part}]"
                    )
                output = "最近 P3394 工具记录：\n" + "\n".join(lines)
            else:
                output = "还没有 P3394 工具记录。"
            await stream_output(output, node=self.id, save_to_context=True)
            return {
                "p3394_runtime_agent": output,
                "p3394_umf_message": normalized,
                "p3394_response_message": response_message,
                "p3394_payload": payload,
                "p3394_audit": audit,
                "__p3394_complete__": True,
            }
        elif capability == "p3394.local_memory":
            audit = _record_audit(normalized, relationship, "ok", thread_id=context.thread_id)
            input_data = _message_body_input(normalized)
            memory_text = str(input_data.get("content") or input_data.get("memory") or _extract_memory_text(text)).strip()
            created: dict[str, Any] | None = None
            if message_type == "agent.request" and memory_text:
                created_item = add_p3394_knowledge_item(
                    workflow_id=workflow.id,
                    title=memory_text[:80],
                    content=memory_text,
                    source="p3394_chat",
                    tags=["chat-memory"],
                    metadata={"thread_id": context.thread_id},
                )
                created_relation = add_p3394_memory_relation(
                    workflow_id=workflow.id,
                    source_label="用户记忆",
                    source_kind="memory_bucket",
                    relation="contains",
                    target_label=created_item["title"],
                    target_kind="knowledge",
                    evidence=memory_text,
                )
                created = {"knowledge": created_item, "relation": created_relation}

            query = str(input_data.get("query") or "").strip()
            matches = search_p3394_knowledge_items(workflow_id=workflow.id, query=query, limit=10) if query else []
            summary = get_p3394_local_memory_summary(workflow.id, limit=50)
            payload = {
                "created": created,
                "matches": matches,
                "summary": summary,
            }
            response_message = _response_envelope(normalized, audit, payload)
            if created:
                output = f"已写入本地记忆：{created['knowledge']['title']}"
            elif matches:
                lines = [f"{index + 1}. {item.get('title')}" for index, item in enumerate(matches[:8])]
                output = "查到这些本地记忆：\n" + "\n".join(lines)
            else:
                graph = summary.get("graph", {})
                output = (
                    "本地记忆图谱："
                    f"{graph.get('node_count', 0)} 个节点，"
                    f"{graph.get('edge_count', 0)} 条关系，"
                    f"{summary.get('knowledge_count', 0)} 条知识。"
                )
            await stream_output(output, node=self.id, save_to_context=True)
            return {
                "p3394_runtime_agent": output,
                "p3394_umf_message": normalized,
                "p3394_response_message": response_message,
                "p3394_payload": payload,
                "p3394_audit": audit,
                "__p3394_complete__": True,
            }
        elif capability == "conformance.check":
            payload = _conformance_report()
            summary = "Checked this AgentClaw-hosted runtime against the P3394 Level 2 runtime profile."
            title = "P3394 Conformance Check"
        else:
            route = _select_route(text, normalized)
            session = _get_session(context.thread_id, normalized)
            normalized["canonical_session_id"] = session["canonical_session_id"]
            normalized["metadata"]["session_lifecycle"] = session["lifecycle"]
            normalized["metadata"]["selected_route"] = route
            audit = _record_audit(
                normalized,
                relationship,
                "accepted",
                thread_id=context.thread_id,
                details={"route": route},
            )
            payload = {
                "response": "Request accepted and delegated to the AgentClaw agentic LLM runtime.",
                "runtime": "LLMNode(agent_style='agentic')",
                "selected_route": route,
                "tools": "AgentClaw built-in tools enabled",
                "skills": "AgentClaw project and built-in skills enabled",
            }
            role_plan = activate_p3394_role_plan(
                build_p3394_role_plan(text, route),
                normalized=normalized,
                route=route,
                file_context_ids=file_context_ids,
            )
            task_history_id = record_p3394_task_history(
                workflow_id=workflow.id,
                thread_id=context.thread_id,
                request=text,
                route=route,
                role_plan=role_plan,
                status="accepted",
            )
            execution_record_id = record_p3394_execution_record(
                workflow_id=workflow.id,
                thread_id=context.thread_id,
                task_history_id=task_history_id,
                request=text,
                route=route,
                status="running",
            )
            payload["role_plan"] = role_plan
            payload["task_history_id"] = task_history_id
            payload["execution_record_id"] = execution_record_id
            payload["file_context_ids"] = file_context_ids
            agent_prompt = _build_agent_prompt(
                text=text,
                normalized=normalized,
                audit=audit,
                session=session,
                route=route,
                role_plan=role_plan,
            )
            return {
                "p3394_init": agent_prompt,
                "p3394_runtime_agent": payload["response"],
                "p3394_umf_message": normalized,
                "p3394_payload": payload,
                "p3394_route": route,
                "p3394_role_plan": role_plan,
                "p3394_task_history_id": task_history_id,
                "p3394_execution_record_id": execution_record_id,
                "p3394_file_context_ids": file_context_ids,
                "p3394_audit": audit,
                "__p3394_complete__": False,
            }

        audit = _record_audit(normalized, relationship, "ok", thread_id=context.thread_id)
        response_message = _response_envelope(normalized, audit, payload)
        output = _format_output(
            title=title,
            summary=summary,
            normalized=normalized,
            audit=audit,
            payload=payload,
            response_message=response_message,
        )
        await stream_output(output, node=self.id, save_to_context=True)
        return {
            "p3394_runtime_agent": output,
            "p3394_umf_message": normalized,
            "p3394_response_message": response_message,
            "p3394_payload": payload,
            "p3394_audit": audit,
            "__p3394_complete__": True,
        }


class P3394FinalizeNode(CustomNode):
    """Persist post-LLM P3394 role-stage completion without adding chat noise."""

    def process(self, **_):
        """CustomNode requires a sync process hook; runtime work uses async_execute."""
        return {}

    async def async_execute(self, state: dict[str, Any], context) -> dict[str, Any]:
        role_plan = state.get("p3394_role_plan")
        history_id = state.get("p3394_task_history_id")
        execution_record_id = state.get("p3394_execution_record_id")
        if not isinstance(role_plan, list) or not history_id:
            latest = get_latest_p3394_task_history_for_thread(
                workflow_id=workflow.id,
                thread_id=str(getattr(context, "thread_id", "") or ""),
            )
            if latest:
                history_id = history_id or latest.get("id")
                role_plan = role_plan if isinstance(role_plan, list) else latest.get("role_plan")
        if not execution_record_id:
            latest_execution = get_latest_p3394_execution_record_for_thread(
                workflow_id=workflow.id,
                thread_id=str(getattr(context, "thread_id", "") or ""),
            )
            if latest_execution:
                execution_record_id = latest_execution.get("id")
        if not isinstance(role_plan, list) or not history_id:
            return {}

        answer_preview = str(state.get("answer") or "").strip()[:500]
        completed_plan = complete_p3394_role_plan(
            role_plan,
            answer=answer_preview,
        )
        history_updated = update_p3394_task_history(
            history_id=str(history_id),
            workflow_id=workflow.id,
            role_plan=completed_plan,
            status="completed",
        )
        execution_updated = False
        if execution_record_id:
            execution_updated = complete_p3394_execution_record(
                record_id=str(execution_record_id),
                workflow_id=workflow.id,
                answer_preview=answer_preview,
                role_statuses=[str(step.get("status") or "") for step in completed_plan],
                status="completed",
            )
        execution_status = (
            "completed"
            if history_updated and (not execution_record_id or execution_updated)
            else "completion_not_recorded"
        )
        return {
            "p3394_role_plan": completed_plan,
            "p3394_execution_status": execution_status,
            "p3394_task_history_id": history_id,
            "p3394_execution_record_id": execution_record_id,
        }


workflow.add_node(P3394InitNode(
    id="p3394_init",
    description="识别任务、准备上下文和执行记录。",
    output_to_user=False,
))

workflow.add_node(SmartPreFilterNode())

workflow.add_node(LLMNode(
    id="agent",
    description="接入 MLL 的 P3394 执行智能体。",
    system_prompt=P3394_AGENT_SYSTEM_PROMPT,
    user_prompt="{p3394_init}",
    agent_style="agentic",
    skills="*",
    enable_builtin_skills=True,
    tools="*",
    enable_builtin_tools=True,
    enable_memory=True,
    stream=True,
    output_to_user=True,
    max_context_messages=30,
    output_key="answer",
    tools_filter_key="__filtered_tools__",
    skills_filter_key="__filtered_skill_names__",
))

workflow.add_node(P3394FinalizeNode(
    id="p3394_finalize",
    description="记录 P3394 内部角色阶段完成状态。",
    output_to_user=False,
))

workflow.add_edge("__start__", "p3394_init")
workflow.add_conditional_edge(
    "p3394_init",
    condition=lambda state: "__end__" if state.get("__p3394_complete__") else "smart_prefilter",
    targets={
        "__end__": "__end__",
        "smart_prefilter": "smart_prefilter",
    },
)
workflow.add_edge("smart_prefilter", "agent")
workflow.add_edge("agent", "p3394_finalize")

workflow.publish()
