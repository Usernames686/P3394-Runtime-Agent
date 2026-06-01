"""Internal P3394 role planning helpers."""

from __future__ import annotations

from time import time
from typing import Any

from .p3394_reference import P3394_INTERNAL_ROLES


def build_p3394_role_plan(text: str, route: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Create a compact internal role plan for one P3394 request."""
    route = route or {}
    family = str(route.get("family") or "general_chat")

    focus_by_role = {
        "P3394 Planner": (
            "Map the request to P3394 manifest, session, relationship, capability, and route constraints."
            if family == "p3394_architecture"
            else "Clarify the task boundary, route, required tools, and success checks."
        ),
        "P3394 Researcher": (
            "Inspect the local P3394 reference, project structure, files, documents, and web evidence when needed."
            if family == "p3394_architecture"
            else "Gather local file, project, document, or web evidence before acting when needed."
        ),
        "P3394 Executor": (
            "Execute the smallest useful command, file edit, or tool action through AgentClaw runtime tools."
        ),
        "P3394 Reviewer": (
            "Verify command results, changed files, tests, risks, and P3394 conformance gaps before final output."
        ),
    }

    return [
        {
            "step": index + 1,
            "role": role_name,
            "status": "planned",
            "focus": focus_by_role[role_name],
            "route_family": family,
            "request_preview": text[:160],
        }
        for index, (role_name, _description) in enumerate(P3394_INTERNAL_ROLES)
    ]


def activate_p3394_role_plan(
    role_plan: list[dict[str, Any]],
    *,
    normalized: dict[str, Any] | None = None,
    route: dict[str, Any] | None = None,
    file_context_ids: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Materialize deterministic internal role handoffs before the LLM runtime runs."""
    normalized = normalized or {}
    route = route or {}
    file_context_ids = file_context_ids or []
    started_at = int(time() * 1000)
    capability = str(normalized.get("body", {}).get("capability") or normalized.get("capability") or "")
    message_type = str(normalized.get("message_type") or "")
    route_family = str(route.get("family") or "general_chat")
    target = str(route.get("target") or "agentic_runtime")
    mode = str(route.get("execution_mode") or "local_agentic_runtime")

    result_by_role = {
        "P3394 Planner": "Route, capability, and success boundary selected before execution.",
        "P3394 Researcher": "Reference, file context, document, project, or web evidence requirements were gathered.",
        "P3394 Executor": "AgentClaw runtime handoff prepared for command, file, search, or document tools.",
        "P3394 Reviewer": "Waiting to review the final answer, tool results, and persistence records.",
    }
    artifact_by_role = {
        "P3394 Planner": {
            "capability": capability,
            "message_type": message_type,
            "route_family": route_family,
            "target": target,
            "success_checks": [
                "normal_language_answer",
                "tool_results_recorded",
                "role_history_persisted",
            ],
        },
        "P3394 Researcher": {
            "reference": "P3394-v0.9.0 local architecture draft",
            "file_context_count": len(file_context_ids),
            "file_context_ids": file_context_ids,
            "needs_web_context": route_family == "knowledge_search",
            "needs_project_context": route_family in {"p3394_architecture", "code_command"},
        },
        "P3394 Executor": {
            "runtime": "AgentClaw LLMNode(agent_style='agentic')",
            "target": target,
            "execution_mode": mode,
            "tool_contract": "built-in local tools, MCP tools, and skills are available",
        },
        "P3394 Reviewer": {
            "checks": [
                "answer_preview",
                "execution_record_status",
                "task_history_status",
                "tool_record_status",
            ],
        },
    }
    status_by_role = {
        "P3394 Planner": "completed",
        "P3394 Researcher": "completed",
        "P3394 Executor": "running",
        "P3394 Reviewer": "planned",
    }

    activated: list[dict[str, Any]] = []
    for step in role_plan:
        role = str(step.get("role") or "")
        item = {
            **step,
            "status": status_by_role.get(role, "planned"),
            "started_at": step.get("started_at") or started_at,
            "result": result_by_role.get(role, "Role stage prepared."),
            "artifact": artifact_by_role.get(role, {}),
        }
        if item["status"] == "completed":
            item["completed_at"] = started_at
        activated.append(item)
    return activated


def complete_p3394_role_plan(
    role_plan: list[dict[str, Any]],
    *,
    answer: str | None = None,
) -> list[dict[str, Any]]:
    """Mark the internal role plan as completed after the AgentClaw runtime answers."""
    completed_at = int(time() * 1000)
    result_by_role = {
        "P3394 Planner": "Task was routed and bounded before execution.",
        "P3394 Researcher": "Context and evidence gathering were delegated to the agentic runtime when needed.",
        "P3394 Executor": "Execution was delegated to AgentClaw's agentic LLM runtime and tools.",
        "P3394 Reviewer": "Final answer was produced and recorded for review.",
    }
    answer_preview = (answer or "").strip()[:160]
    completed: list[dict[str, Any]] = []
    for step in role_plan:
        role = str(step.get("role") or "")
        item = {
            **step,
            "status": "completed",
            "started_at": step.get("started_at") or completed_at,
            "completed_at": completed_at,
            "result": result_by_role.get(role, "Role stage completed."),
        }
        if role == "P3394 Reviewer" and answer_preview:
            item["answer_preview"] = answer_preview
        completed.append(item)
    return completed
