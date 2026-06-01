from __future__ import annotations

from pathlib import Path

import pytest

from agentclaw.agent_square.p3394_runtime_agent.agents.p3394_roles import (
    build_p3394_role_plan,
)
from agentclaw.agent_square.p3394_runtime_agent.agents.p3394_execution_records import (
    complete_p3394_execution_record,
    list_p3394_execution_records,
    record_p3394_execution_record,
)
from agentclaw.agent_square.p3394_runtime_agent.agents.p3394_tool_records import (
    record_p3394_tool_record,
)
from agentclaw.agent_square.p3394_runtime_agent.agents.p3394_file_context import (
    record_p3394_file_contexts_from_state,
)
from agentclaw.agent_square.p3394_runtime_agent.agents.p3394_task_history import (
    list_p3394_task_history,
    record_p3394_task_history,
)
from agentclaw.api.routers.public.execution import _mark_p3394_execution_failed
from agentclaw.test.conftest import auth_header


pytestmark = pytest.mark.api


def test_admin_p3394_task_history_lists_persisted_role_plan(
    admin_api_client,
    auth_tokens,
    tmp_path,
    monkeypatch,
):
    sqlite_path = tmp_path / "agentclaw-local.db"
    monkeypatch.setenv("AGENTCLAW_SQLITE_PATH", str(sqlite_path))
    role_plan = build_p3394_role_plan(
        "按 P3394 架构分析这个项目",
        {"family": "p3394_architecture", "target": "agentic_runtime"},
    )
    history_id = record_p3394_task_history(
        workflow_id="p3394_runtime_agent",
        thread_id="thread-1",
        request="按 P3394 架构分析这个项目",
        route={"family": "p3394_architecture", "target": "agentic_runtime"},
        role_plan=role_plan,
        status="routed",
    )

    response = admin_api_client.get(
        "/admin/p3394/task-history?workflow_id=p3394_runtime_agent&limit=5",
        headers=auth_header(auth_tokens.admin),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["workflow_id"] == "p3394_runtime_agent"
    assert payload["count"] == 1
    assert payload["tasks"][0]["id"] == history_id
    assert payload["tasks"][0]["thread_id"] == "thread-1"
    assert payload["tasks"][0]["request"] == "按 P3394 架构分析这个项目"
    assert payload["tasks"][0]["route"]["family"] == "p3394_architecture"
    assert payload["tasks"][0]["role_plan"][0]["role"] == "P3394 Planner"


def test_admin_p3394_execution_records_lists_persisted_runs(
    admin_api_client,
    auth_tokens,
    tmp_path,
    monkeypatch,
):
    sqlite_path = tmp_path / "agentclaw-local.db"
    monkeypatch.setenv("AGENTCLAW_SQLITE_PATH", str(sqlite_path))
    record_id = record_p3394_execution_record(
        workflow_id="p3394_runtime_agent",
        thread_id="thread-1",
        task_history_id="p3394_task_1",
        request="按 P3394 架构分析这个项目",
        route={"family": "p3394_architecture", "target": "agentic_runtime"},
        status="running",
    )
    complete_p3394_execution_record(
        record_id=record_id,
        workflow_id="p3394_runtime_agent",
        answer_preview="项目可以按 manifest、adapter、session、audit 层拆解。",
        role_statuses=["completed", "completed", "completed", "completed"],
        status="completed",
    )

    response = admin_api_client.get(
        "/admin/p3394/execution-records?workflow_id=p3394_runtime_agent&limit=5",
        headers=auth_header(auth_tokens.admin),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["workflow_id"] == "p3394_runtime_agent"
    assert payload["count"] == 1
    assert payload["records"][0]["id"] == record_id
    assert payload["records"][0]["thread_id"] == "thread-1"
    assert payload["records"][0]["status"] == "completed"
    assert payload["records"][0]["route"]["family"] == "p3394_architecture"
    assert payload["records"][0]["answer_preview"] == "项目可以按 manifest、adapter、session、audit 层拆解。"


def test_p3394_execution_failure_marks_running_records(
    tmp_path,
    monkeypatch,
):
    sqlite_path = tmp_path / "agentclaw-local.db"
    monkeypatch.setenv("AGENTCLAW_SQLITE_PATH", str(sqlite_path))
    role_plan = build_p3394_role_plan(
        "explain the runtime",
        {"family": "general_chat", "target": "agentic_runtime"},
    )
    history_id = record_p3394_task_history(
        workflow_id="p3394_runtime_agent",
        thread_id="thread-failed",
        request="explain the runtime",
        route={"family": "general_chat", "target": "agentic_runtime"},
        role_plan=role_plan,
        status="routed",
    )
    record_id = record_p3394_execution_record(
        workflow_id="p3394_runtime_agent",
        thread_id="thread-failed",
        task_history_id=history_id,
        request="explain the runtime",
        route={"family": "general_chat", "target": "agentic_runtime"},
        status="running",
    )

    _mark_p3394_execution_failed("p3394_runtime_agent", "thread-failed", RuntimeError("model 503"))

    records = list_p3394_execution_records("p3394_runtime_agent")
    tasks = list_p3394_task_history("p3394_runtime_agent")
    assert records[0]["id"] == record_id
    assert records[0]["status"] == "failed"
    assert records[0]["answer_preview"] == "执行失败：model 503"
    assert tasks[0]["id"] == history_id
    assert tasks[0]["status"] == "failed"


def test_admin_p3394_file_context_lists_persisted_context(
    admin_api_client,
    auth_tokens,
    tmp_path,
    monkeypatch,
):
    sqlite_path = tmp_path / "agentclaw-local.db"
    monkeypatch.setenv("AGENTCLAW_SQLITE_PATH", str(sqlite_path))
    notes = tmp_path / "notes.md"
    notes.write_text("P3394 file context notes", encoding="utf-8")
    record_p3394_file_contexts_from_state(
        workflow_id="p3394_runtime_agent",
        thread_id="thread-files",
        request=f"读取 {notes}",
        state={},
    )

    response = admin_api_client.get(
        "/admin/p3394/file-context?workflow_id=p3394_runtime_agent&limit=5",
        headers=auth_header(auth_tokens.admin),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["workflow_id"] == "p3394_runtime_agent"
    assert payload["count"] == 1
    assert payload["contexts"][0]["thread_id"] == "thread-files"
    assert payload["contexts"][0]["path"] == str(notes)
    assert payload["contexts"][0]["file_type"] == "markdown"


def test_admin_p3394_artifacts_lists_files_created_by_tool_records(
    admin_api_client,
    auth_tokens,
    tmp_path,
    monkeypatch,
):
    sqlite_path = tmp_path / "agentclaw-local.db"
    monkeypatch.setenv("AGENTCLAW_SQLITE_PATH", str(sqlite_path))
    artifact = tmp_path / "P3394-output.md"
    artifact.write_text("# P3394 Output\n\nCreated by the runtime.", encoding="utf-8")
    record_p3394_tool_record(
        workflow_id="p3394_runtime_agent",
        thread_id="thread-artifact",
        task_id="task-artifact",
        tool_name="execute_command",
        tool_arguments={"command": f"Set-Content -Path '{artifact}' -Value demo"},
        tool_result=f"[stdout]\ncreated: {artifact}\nexit code 0",
        status="succeeded",
    )

    response = admin_api_client.get(
        "/admin/p3394/artifacts?workflow_id=p3394_runtime_agent&limit=5",
        headers=auth_header(auth_tokens.admin),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["workflow_id"] == "p3394_runtime_agent"
    assert payload["count"] == 1
    assert payload["artifacts"][0]["thread_id"] == "thread-artifact"
    assert payload["artifacts"][0]["path"] == str(artifact)
    assert payload["artifacts"][0]["display_name"] == "P3394-output.md"
    assert payload["artifacts"][0]["file_type"] == "markdown"
    assert payload["artifacts"][0]["status"] == "available"
    assert "Created by the runtime" in payload["artifacts"][0]["preview"]


def test_admin_p3394_artifacts_include_folders_logs_and_can_open_paths(
    admin_api_client,
    auth_tokens,
    tmp_path,
    monkeypatch,
):
    sqlite_path = tmp_path / "agentclaw-local.db"
    monkeypatch.setenv("AGENTCLAW_SQLITE_PATH", str(sqlite_path))
    folder = tmp_path / "generated-project"
    folder.mkdir()
    (folder / "main.py").write_text("print('hello')", encoding="utf-8")
    record_p3394_tool_record(
        workflow_id="p3394_runtime_agent",
        thread_id="thread-folder",
        task_id="task-folder",
        tool_name="execute_command",
        tool_arguments={"command": f"New-Item -ItemType Directory -Path '{folder}'"},
        tool_result=f"[stdout]\ncreated folder: {folder}\nran pytest -q\nexit code 0",
        status="succeeded",
    )

    response = admin_api_client.get(
        "/admin/p3394/artifacts?workflow_id=p3394_runtime_agent&limit=10",
        headers=auth_header(auth_tokens.admin),
    )

    assert response.status_code == 200
    payload = response.json()
    folder_artifact = next(item for item in payload["artifacts"] if item["path"] == str(folder))
    assert folder_artifact["file_type"] == "folder"
    assert folder_artifact["display_name"] == "generated-project"
    assert "main.py" in folder_artifact["preview"]
    assert any(item["file_type"] == "run_log" and "ran pytest -q" in item["preview"] for item in payload["artifacts"])

    opened: list[str] = []
    from agentclaw.agent_square.p3394_runtime_agent.agents import p3394_artifacts

    monkeypatch.setattr(p3394_artifacts, "_open_path_for_os", lambda path: opened.append(str(path)))
    open_response = admin_api_client.post(
        "/admin/p3394/open-path",
        headers=auth_header(auth_tokens.admin),
        json={"path": str(folder)},
    )

    assert open_response.status_code == 200
    assert open_response.json()["success"] is True
    assert opened == [str(folder)]


def test_admin_p3394_knowledge_import_adds_local_files_to_memory_graph(
    admin_api_client,
    auth_tokens,
    tmp_path,
    monkeypatch,
):
    sqlite_path = tmp_path / "agentclaw-local.db"
    memory_dir = tmp_path / "p3394-memory"
    monkeypatch.setenv("AGENTCLAW_SQLITE_PATH", str(sqlite_path))
    monkeypatch.setenv("AGENTCLAW_P3394_MEMORY_DIR", str(memory_dir))
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    notes = docs_dir / "runtime-notes.md"
    notes.write_text("# Runtime Notes\n\nP3394 can execute commands and keep memory.", encoding="utf-8")
    ignored = docs_dir / "image.png"
    ignored.write_bytes(b"png")

    response = admin_api_client.post(
        "/admin/p3394/knowledge/import",
        headers=auth_header(auth_tokens.admin),
        json={
            "workflow_id": "p3394_runtime_agent",
            "paths": [str(docs_dir)],
            "recursive": True,
            "max_files": 10,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["imported_count"] == 1
    assert payload["skipped_count"] == 1
    assert payload["items"][0]["title"] == "runtime-notes.md"
    assert payload["items"][0]["source"] == "local_knowledge_import"
    assert payload["items"][0]["metadata"]["path"] == str(notes)
    assert payload["items"][0]["metadata"]["summary"]
    assert payload["items"][0]["content"].startswith("Summary:")

    knowledge_response = admin_api_client.get(
        "/admin/p3394/knowledge?workflow_id=p3394_runtime_agent&q=execute commands&limit=10",
        headers=auth_header(auth_tokens.admin),
    )
    assert knowledge_response.status_code == 200
    knowledge = knowledge_response.json()
    assert knowledge["count"] == 1
    assert knowledge["items"][0]["title"] == "runtime-notes.md"

    graph_response = admin_api_client.get(
        "/admin/p3394/memory-graph?workflow_id=p3394_runtime_agent&limit=20",
        headers=auth_header(auth_tokens.admin),
    )
    graph = graph_response.json()
    assert "本地知识库" in {node["label"] for node in graph["nodes"]}
    assert "runtime-notes.md" in {node["label"] for node in graph["nodes"]}
    assert any(
        edge["source_label"] == "本地知识库"
        and edge["target_label"] == "runtime-notes.md"
        and edge["relation"] == "contains"
        for edge in graph["edges"]
    )


def test_admin_p3394_knowledge_upload_imports_files_with_summary(
    admin_api_client,
    auth_tokens,
    tmp_path,
    monkeypatch,
):
    sqlite_path = tmp_path / "agentclaw-local.db"
    memory_dir = tmp_path / "p3394-memory"
    upload_dir = tmp_path / "uploads"
    monkeypatch.setenv("AGENTCLAW_SQLITE_PATH", str(sqlite_path))
    monkeypatch.setenv("AGENTCLAW_P3394_MEMORY_DIR", str(memory_dir))
    monkeypatch.setenv("AGENTCLAW_P3394_IMPORT_UPLOAD_DIR", str(upload_dir))

    response = admin_api_client.post(
        "/admin/p3394/knowledge/import-files",
        headers=auth_header(auth_tokens.admin),
        data={"workflow_id": "p3394_runtime_agent", "recursive": "true"},
        files={
            "files": (
                "dragged-notes.md",
                b"# Dragged Notes\n\nP3394 uploads files into SQLite and graph memory.",
                "text/markdown",
            )
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["imported_count"] == 1
    assert payload["items"][0]["title"] == "dragged-notes.md"
    assert payload["items"][0]["metadata"]["source_mode"] == "uploaded_file"
    assert payload["items"][0]["metadata"]["summary"]
    assert Path(payload["items"][0]["metadata"]["path"]).exists()


def test_admin_p3394_tool_records_lists_command_details(
    admin_api_client,
    auth_tokens,
    tmp_path,
    monkeypatch,
):
    sqlite_path = tmp_path / "agentclaw-local.db"
    monkeypatch.setenv("AGENTCLAW_SQLITE_PATH", str(sqlite_path))
    record_id = record_p3394_tool_record(
        workflow_id="p3394_runtime_agent",
        thread_id="thread-tools",
        task_id="task-1",
        message_id="message-1",
        tool_call_id="call-1",
        tool_name="execute_command",
        tool_arguments='{"command":"git status --short","cwd":"D:\\\\codex\\\\ui\\\\agentclaw"}',
        tool_result="[stdout]\n M agentclaw/test/api/test_admin_p3394_api.py\n[stderr]\nwarning\nexit code 0",
        status="succeeded",
        duration_ms=42.5,
        batch_id="round-1",
        node_id="agent",
    )

    response = admin_api_client.get(
        "/admin/p3394/tool-records?workflow_id=p3394_runtime_agent&limit=5",
        headers=auth_header(auth_tokens.admin),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["workflow_id"] == "p3394_runtime_agent"
    assert payload["count"] == 1
    assert payload["records"][0]["id"] == record_id
    assert payload["records"][0]["thread_id"] == "thread-tools"
    assert payload["records"][0]["tool_call_id"] == "call-1"
    assert payload["records"][0]["tool_name"] == "execute_command"
    assert payload["records"][0]["command"] == "git status --short"
    assert payload["records"][0]["cwd"] == "D:\\codex\\ui\\agentclaw"
    assert payload["records"][0]["stdout"] == " M agentclaw/test/api/test_admin_p3394_api.py"
    assert payload["records"][0]["stderr"] == "warning"
    assert payload["records"][0]["exit_code"] == 0
    assert payload["records"][0]["duration_ms"] == 42.5


def test_admin_p3394_execution_summary_groups_route_tools_files_and_artifacts(
    admin_api_client,
    auth_tokens,
    tmp_path,
    monkeypatch,
):
    sqlite_path = tmp_path / "agentclaw-local.db"
    monkeypatch.setenv("AGENTCLAW_SQLITE_PATH", str(sqlite_path))
    artifact = tmp_path / "summary-output.txt"
    artifact.write_text("summary artifact", encoding="utf-8")
    exec_id = record_p3394_execution_record(
        workflow_id="p3394_runtime_agent",
        thread_id="thread-summary",
        task_history_id="task-summary",
        request="create a summary file",
        route={"family": "code_command", "target": "agentic_runtime"},
        status="running",
    )
    complete_p3394_execution_record(
        record_id=exec_id,
        workflow_id="p3394_runtime_agent",
        answer_preview="Created summary-output.txt",
        role_statuses=["completed", "completed"],
        status="completed",
    )
    record_p3394_file_contexts_from_state(
        workflow_id="p3394_runtime_agent",
        thread_id="thread-summary",
        request=f"read {artifact}",
        state={},
    )
    record_p3394_tool_record(
        workflow_id="p3394_runtime_agent",
        thread_id="thread-summary",
        task_id="task-summary",
        tool_name="execute_command",
        tool_arguments={"command": f"Set-Content -Path '{artifact}' -Value demo"},
        tool_result=f"[stdout]\n{artifact}\nexit code 0",
        status="succeeded",
    )

    response = admin_api_client.get(
        "/admin/p3394/execution-summary?workflow_id=p3394_runtime_agent&limit=5",
        headers=auth_header(auth_tokens.admin),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["workflow_id"] == "p3394_runtime_agent"
    assert payload["count"] == 1
    item = payload["records"][0]
    assert item["id"] == exec_id
    assert item["route_label"] == "code_command -> agentic_runtime"
    assert item["tool_count"] == 1
    assert item["file_count"] == 1
    assert item["artifact_count"] == 1
    assert [step["kind"] for step in item["steps"]] == ["route", "role", "read", "run", "write"]
    assert item["tools"][0]["command"].startswith("Set-Content")
    assert item["artifacts"][0]["path"] == str(artifact)


def test_admin_p3394_execution_summary_names_read_run_write_and_verify_steps(
    admin_api_client,
    auth_tokens,
    tmp_path,
    monkeypatch,
):
    sqlite_path = tmp_path / "agentclaw-local.db"
    monkeypatch.setenv("AGENTCLAW_SQLITE_PATH", str(sqlite_path))
    source = tmp_path / "source.md"
    output = tmp_path / "output.md"
    source.write_text("read me", encoding="utf-8")
    output.write_text("written", encoding="utf-8")
    exec_id = record_p3394_execution_record(
        workflow_id="p3394_runtime_agent",
        thread_id="thread-codex",
        task_history_id="task-codex",
        request="read source, write output, run tests",
        route={"family": "code_command", "target": "agentic_runtime"},
        status="running",
    )
    complete_p3394_execution_record(
        record_id=exec_id,
        workflow_id="p3394_runtime_agent",
        answer_preview="Wrote output and verified with pytest.",
        role_statuses=["completed"],
        status="completed",
    )
    record_p3394_file_contexts_from_state(
        workflow_id="p3394_runtime_agent",
        thread_id="thread-codex",
        request=f"read {source}",
        state={},
    )
    record_p3394_tool_record(
        workflow_id="p3394_runtime_agent",
        thread_id="thread-codex",
        task_id="task-codex",
        tool_name="execute_command",
        tool_arguments={"command": f"Set-Content -Path '{output}' -Value written"},
        tool_result=f"[stdout]\n{output}\nexit code 0",
        status="succeeded",
    )
    record_p3394_tool_record(
        workflow_id="p3394_runtime_agent",
        thread_id="thread-codex",
        task_id="task-codex",
        tool_name="execute_command",
        tool_arguments={"command": "pytest -q"},
        tool_result="[stdout]\n1 passed\nexit code 0",
        status="succeeded",
    )

    response = admin_api_client.get(
        "/admin/p3394/execution-summary?workflow_id=p3394_runtime_agent&limit=5",
        headers=auth_header(auth_tokens.admin),
    )

    assert response.status_code == 200
    item = response.json()["records"][0]
    assert item["id"] == exec_id
    step_kinds = [step["kind"] for step in item["steps"]]
    assert "read" in step_kinds
    assert "run" in step_kinds
    assert "write" in step_kinds
    assert "verify" in step_kinds
    assert any(step["path"] == str(source) for step in item["steps"] if step["kind"] == "read")
    assert any(step["path"] == str(output) for step in item["steps"] if step["kind"] == "write")
    assert any("pytest -q" in step["summary"] for step in item["steps"] if step["kind"] == "verify")


def test_admin_p3394_memory_graph_creates_relation_and_lists_graph(
    admin_api_client,
    auth_tokens,
    tmp_path,
    monkeypatch,
):
    sqlite_path = tmp_path / "agentclaw-local.db"
    monkeypatch.setenv("AGENTCLAW_SQLITE_PATH", str(sqlite_path))

    response = admin_api_client.post(
        "/admin/p3394/memory-graph/relations",
        headers=auth_header(auth_tokens.admin),
        json={
            "workflow_id": "p3394_runtime_agent",
            "source_label": "用户",
            "source_kind": "person",
            "relation": "owns",
            "target_label": "P3394 Agent Platform",
            "target_kind": "project",
            "evidence": "用户把 P3394 包装成自己的本地智能体平台。",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["relation"]["source"]["label"] == "用户"
    assert payload["relation"]["target"]["label"] == "P3394 Agent Platform"
    assert payload["relation"]["edge"]["relation"] == "owns"

    graph_response = admin_api_client.get(
        "/admin/p3394/memory-graph?workflow_id=p3394_runtime_agent&limit=20",
        headers=auth_header(auth_tokens.admin),
    )

    assert graph_response.status_code == 200
    graph = graph_response.json()
    assert graph["workflow_id"] == "p3394_runtime_agent"
    assert graph["node_count"] == 2
    assert graph["edge_count"] == 1
    assert {node["label"] for node in graph["nodes"]} == {"用户", "P3394 Agent Platform"}
    assert graph["edges"][0]["source_label"] == "用户"
    assert graph["edges"][0]["target_label"] == "P3394 Agent Platform"


def test_admin_p3394_knowledge_create_list_and_search(
    admin_api_client,
    auth_tokens,
    tmp_path,
    monkeypatch,
):
    sqlite_path = tmp_path / "agentclaw-local.db"
    monkeypatch.setenv("AGENTCLAW_SQLITE_PATH", str(sqlite_path))

    response = admin_api_client.post(
        "/admin/p3394/knowledge",
        headers=auth_header(auth_tokens.admin),
        json={
            "workflow_id": "p3394_runtime_agent",
            "title": "命令执行偏好",
            "content": "P3394 需要接入模型并允许执行本地命令。",
            "source": "test",
            "tags": ["p3394", "memory"],
            "metadata": {"scope": "local"},
        },
    )

    assert response.status_code == 200
    created = response.json()
    assert created["success"] is True
    assert created["item"]["title"] == "命令执行偏好"

    list_response = admin_api_client.get(
        "/admin/p3394/knowledge?workflow_id=p3394_runtime_agent&limit=10",
        headers=auth_header(auth_tokens.admin),
    )
    assert list_response.status_code == 200
    listed = list_response.json()
    assert listed["count"] == 1
    assert listed["items"][0]["content"] == "P3394 需要接入模型并允许执行本地命令。"

    search_response = admin_api_client.get(
        "/admin/p3394/knowledge?workflow_id=p3394_runtime_agent&q=本地命令&limit=10",
        headers=auth_header(auth_tokens.admin),
    )
    assert search_response.status_code == 200
    searched = search_response.json()
    assert searched["query"] == "本地命令"
    assert searched["count"] == 1
    assert searched["items"][0]["title"] == "命令执行偏好"


def test_admin_p3394_memory_graph_seed_demo_creates_readable_starter_graph(
    admin_api_client,
    auth_tokens,
    tmp_path,
    monkeypatch,
):
    sqlite_path = tmp_path / "agentclaw-local.db"
    monkeypatch.setenv("AGENTCLAW_SQLITE_PATH", str(sqlite_path))

    response = admin_api_client.post(
        "/admin/p3394/memory-graph/seed-demo?workflow_id=p3394_runtime_agent",
        headers=auth_header(auth_tokens.admin),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["seeded_relations"] >= 40
    assert payload["node_count"] >= 25
    assert payload["edge_count"] >= 40
    labels = {node["label"] for node in payload["nodes"]}
    assert "P3394 Agent Platform" in labels
    assert "Sigma.js" in labels
    assert "Graphology" in labels
    assert "p3394_memory_graph_nodes" in labels

    knowledge_response = admin_api_client.get(
        "/admin/p3394/knowledge?workflow_id=p3394_runtime_agent&q=平台定位&limit=10",
        headers=auth_header(auth_tokens.admin),
    )
    assert knowledge_response.status_code == 200
    knowledge = knowledge_response.json()
    assert knowledge["count"] == 1
    assert knowledge["items"][0]["source"] == "seed-demo"

    memory_response = admin_api_client.get(
        "/admin/p3394/knowledge?workflow_id=p3394_runtime_agent&q=记忆图谱&limit=10",
        headers=auth_header(auth_tokens.admin),
    )
    assert memory_response.status_code == 200
    memory = memory_response.json()
    assert memory["count"] >= 1
    assert any(item["title"] == "记忆图谱定位" for item in memory["items"])


def test_admin_p3394_daily_memory_lists_and_generates_markdown(
    admin_api_client,
    auth_tokens,
    tmp_path,
    monkeypatch,
):
    sqlite_path = tmp_path / "agentclaw-local.db"
    memory_dir = tmp_path / "p3394-memory"
    monkeypatch.setenv("AGENTCLAW_SQLITE_PATH", str(sqlite_path))
    monkeypatch.setenv("AGENTCLAW_P3394_MEMORY_DIR", str(memory_dir))

    response = admin_api_client.post(
        "/admin/p3394/daily-memory/generate?workflow_id=p3394_runtime_agent",
        headers=auth_header(auth_tokens.admin),
        json={
            "title": "Daily planning memory",
            "content": "User wants a Logseq-style local memory journal.",
            "tags": ["daily-memory", "graph"],
        },
    )

    assert response.status_code == 200
    generated = response.json()
    assert generated["success"] is True
    assert generated["note"]["entry_count"] == 1
    assert generated["note"]["path"].endswith(".md")
    assert "Daily planning memory" in generated["note"]["preview"]

    list_response = admin_api_client.get(
        "/admin/p3394/daily-memory?workflow_id=p3394_runtime_agent&limit=5",
        headers=auth_header(auth_tokens.admin),
    )

    assert list_response.status_code == 200
    payload = list_response.json()
    assert payload["workflow_id"] == "p3394_runtime_agent"
    assert payload["count"] == 1
    assert payload["notes"][0]["entry_count"] == 1
    assert "Daily planning memory" in payload["notes"][0]["preview"]


def test_admin_p3394_daily_memory_timeline_backfills_recent_days(
    admin_api_client,
    auth_tokens,
    tmp_path,
    monkeypatch,
):
    sqlite_path = tmp_path / "agentclaw-local.db"
    memory_dir = tmp_path / "p3394-memory"
    monkeypatch.setenv("AGENTCLAW_SQLITE_PATH", str(sqlite_path))
    monkeypatch.setenv("AGENTCLAW_P3394_MEMORY_DIR", str(memory_dir))

    response = admin_api_client.get(
        "/admin/p3394/daily-memory/timeline?workflow_id=p3394_runtime_agent&days=3&end_date=2026-06-01",
        headers=auth_header(auth_tokens.admin),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["workflow_id"] == "p3394_runtime_agent"
    assert payload["count"] == 3
    assert [note["date_key"] for note in payload["notes"]] == ["2026-06-01", "2026-05-31", "2026-05-30"]
    assert all(note["path"].endswith(".md") for note in payload["notes"])
    assert all("Daily Memory" in note["preview"] for note in payload["notes"])
