"""Readable P3394 execution summaries for the admin workbench."""

from __future__ import annotations

import re
from typing import Any

from agentclaw.agent_square.p3394_runtime_agent.agents.p3394_artifacts import (
    list_p3394_artifacts,
)
from agentclaw.agent_square.p3394_runtime_agent.agents.p3394_execution_records import (
    list_p3394_execution_records,
)
from agentclaw.agent_square.p3394_runtime_agent.agents.p3394_file_context import (
    list_p3394_file_contexts,
)
from agentclaw.agent_square.p3394_runtime_agent.agents.p3394_tool_records import (
    list_p3394_tool_records,
)


def _route_label(route: Any) -> str:
    if not isinstance(route, dict):
        return ""
    family = str(route.get("family") or "").strip()
    target = str(route.get("target") or "").strip()
    if family and target:
        return f"{family} -> {target}"
    return family or target


def _role_step(record: dict[str, Any]) -> dict[str, Any] | None:
    statuses = record.get("role_statuses") or []
    if not statuses:
        return None
    completed = sum(1 for status in statuses if str(status).lower() == "completed")
    return {
        "kind": "role",
        "title": "角色阶段",
        "status": "completed" if completed == len(statuses) else "running",
        "summary": f"{completed}/{len(statuses)} 个阶段完成",
        "updated_at": record.get("updated_at"),
    }


def _is_verify_command(command: str, output: str) -> bool:
    command_text = command.lower()
    output_text = output.lower()
    command_patterns = (
        r"(^|[;&|]\s*|\s)(pytest|vitest|ruff|mypy)(\s|$)",
        r"\bnpm\s+(test|run\s+build)\b",
        r"\bpnpm\s+(test|build)\b",
    )
    if any(re.search(pattern, command_text) for pattern in command_patterns):
        return True
    return bool(re.search(r"\b\d+\s+(passed|failed)\b", output_text))


def _tool_step_kind(tool: dict[str, Any]) -> str:
    command = str(tool.get("command") or "")
    output = f"{tool.get('stdout') or ''}\n{tool.get('stderr') or ''}\n{tool.get('result_preview') or ''}"
    if _is_verify_command(command, output):
        return "verify"
    return "run"


def _tool_step_title(kind: str) -> str:
    return {
        "run": "运行命令",
        "verify": "验证结果",
    }.get(kind, "工具调用")


def _artifact_step_kind(artifact: dict[str, Any]) -> str:
    return "log" if artifact.get("file_type") == "run_log" else "write"


def list_p3394_execution_summary(workflow_id: str, limit: int = 20) -> list[dict[str, Any]]:
    executions = list_p3394_execution_records(workflow_id=workflow_id, limit=limit)
    tools = list_p3394_tool_records(workflow_id=workflow_id, limit=max(limit * 20, 200))
    files = list_p3394_file_contexts(workflow_id=workflow_id, limit=max(limit * 20, 200))
    artifacts = list_p3394_artifacts(workflow_id=workflow_id, limit=max(limit * 20, 200))

    tools_by_thread: dict[str, list[dict[str, Any]]] = {}
    files_by_thread: dict[str, list[dict[str, Any]]] = {}
    artifacts_by_thread: dict[str, list[dict[str, Any]]] = {}
    for item in tools:
        tools_by_thread.setdefault(str(item.get("thread_id") or ""), []).append(item)
    for item in files:
        files_by_thread.setdefault(str(item.get("thread_id") or ""), []).append(item)
    for item in artifacts:
        artifacts_by_thread.setdefault(str(item.get("thread_id") or ""), []).append(item)

    summaries: list[dict[str, Any]] = []
    for record in executions:
        thread_id = str(record.get("thread_id") or "")
        route_label = _route_label(record.get("route"))
        record_tools = tools_by_thread.get(thread_id, [])
        record_files = files_by_thread.get(thread_id, [])
        record_artifacts = artifacts_by_thread.get(thread_id, [])
        steps = [
            {
                "kind": "route",
                "title": "能力路由",
                "status": record.get("status") or "unknown",
                "summary": route_label,
                "updated_at": record.get("created_at"),
            }
        ]
        role = _role_step(record)
        if role:
            steps.append(role)
        for file_item in record_files[:8]:
            steps.append(
                {
                    "kind": "read",
                    "title": "读取文件",
                    "status": file_item.get("status") or "available",
                    "summary": file_item.get("display_name") or file_item.get("path") or "",
                    "path": file_item.get("path") or "",
                    "updated_at": file_item.get("updated_at"),
                }
            )
        for tool in record_tools[:8]:
            kind = _tool_step_kind(tool)
            steps.append(
                {
                    "kind": kind,
                    "title": _tool_step_title(kind),
                    "status": tool.get("status") or "unknown",
                    "summary": tool.get("command") or tool.get("result_preview") or "",
                    "updated_at": tool.get("updated_at"),
                    "exit_code": tool.get("exit_code"),
                }
            )
        for artifact in record_artifacts[:6]:
            kind = _artifact_step_kind(artifact)
            steps.append(
                {
                    "kind": kind,
                    "title": "运行日志" if kind == "log" else "写入文件",
                    "status": artifact.get("status") or "available",
                    "summary": artifact.get("path") or artifact.get("preview") or "",
                    "path": artifact.get("path") or "",
                    "artifact_type": artifact.get("file_type") or "file",
                    "updated_at": artifact.get("updated_at"),
                }
            )
        summaries.append(
            {
                **record,
                "route_label": route_label,
                "tool_count": len(record_tools),
                "file_count": len(record_files),
                "artifact_count": len(record_artifacts),
                "tools": record_tools[:10],
                "files": record_files[:10],
                "artifacts": record_artifacts[:10],
                "steps": steps,
            }
        )
    return summaries
