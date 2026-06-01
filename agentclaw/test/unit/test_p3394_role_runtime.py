import pytest

from agentclaw.agent_square.p3394_runtime_agent.agents.p3394_runtime_agent import (
    P3394_MANIFEST,
    P3394FinalizeNode,
    _build_agent_prompt,
    _detect_capability,
    extract_p3394_auto_memory_candidates,
)
from agentclaw.agent_square.p3394_runtime_agent.agents.p3394_roles import (
    activate_p3394_role_plan,
    build_p3394_role_plan,
)
from agentclaw.agent_square.p3394_runtime_agent.agents.p3394_execution_records import (
    list_p3394_execution_records,
    record_p3394_execution_record,
)
from agentclaw.agent_square.p3394_runtime_agent.agents.p3394_file_context import (
    list_p3394_file_contexts,
    record_p3394_file_contexts_from_state,
)
from agentclaw.agent_square.p3394_runtime_agent.agents.p3394_task_history import (
    list_p3394_task_history,
    record_p3394_task_history,
    update_p3394_task_history,
)
from agentclaw.agent_square.p3394_runtime_agent.agents.p3394_tool_records import (
    list_p3394_tool_records,
)
from agentclaw.agent_square.p3394_runtime_agent.agents.p3394_local_memory import (
    add_p3394_knowledge_item,
    get_p3394_daily_memory_timeline,
    get_p3394_memory_graph_summary,
    list_p3394_daily_memory_notes,
    list_p3394_knowledge_items,
)


pytestmark = pytest.mark.unit


def _normalized_request() -> dict:
    return {
        "message_type": "agent.request",
        "body": {"capability": "task.route", "input": {}},
        "sender": {"relationship": "owner"},
        "canonical_session_id": "session-1",
    }


def test_p3394_role_plan_has_four_internal_roles_in_execution_order():
    route = {"family": "p3394_architecture", "target": "agentic_runtime"}

    plan = build_p3394_role_plan("按 P3394 架构分析并改造这个项目", route)

    assert [step["role"] for step in plan] == [
        "P3394 Planner",
        "P3394 Researcher",
        "P3394 Executor",
        "P3394 Reviewer",
    ]
    assert plan[0]["status"] == "planned"
    assert "manifest" in plan[0]["focus"].lower()
    assert "verify" in plan[-1]["focus"].lower()


def test_p3394_agent_prompt_receives_internal_role_plan():
    route = {"family": "p3394_architecture", "target": "agentic_runtime"}
    role_plan = build_p3394_role_plan("按 P3394 架构分析并改造这个项目", route)

    prompt = _build_agent_prompt(
        text="按 P3394 架构分析并改造这个项目",
        normalized=_normalized_request(),
        audit={"event_id": "audit-1"},
        session={"canonical_session_id": "session-1"},
        route=route,
        role_plan=role_plan,
    )

    assert "Internal P3394 role plan" in prompt
    for role in ["P3394 Planner", "P3394 Researcher", "P3394 Executor", "P3394 Reviewer"]:
        assert role in prompt
    assert "Do not expose this role plan" in prompt


def test_p3394_role_plan_materializes_internal_role_trace():
    route = {
        "family": "p3394_architecture",
        "target": "agentic_runtime",
        "execution_mode": "local_agentic_runtime",
    }
    normalized = {
        "message_type": "agent.request",
        "body": {"capability": "task.route"},
    }

    plan = activate_p3394_role_plan(
        build_p3394_role_plan("按 P3394 架构分析并改造这个项目", route),
        normalized=normalized,
        route=route,
        file_context_ids=["file-1", "file-2"],
    )

    by_role = {step["role"]: step for step in plan}
    assert by_role["P3394 Planner"]["status"] == "completed"
    assert by_role["P3394 Planner"]["artifact"]["capability"] == "task.route"
    assert by_role["P3394 Researcher"]["artifact"]["file_context_count"] == 2
    assert by_role["P3394 Executor"]["status"] == "running"
    assert by_role["P3394 Executor"]["artifact"]["runtime"] == "AgentClaw LLMNode(agent_style='agentic')"
    assert by_role["P3394 Reviewer"]["status"] == "planned"


def test_p3394_task_history_persists_role_plan_to_sqlite(monkeypatch, tmp_path):
    sqlite_path = tmp_path / "agentclaw-local.db"
    monkeypatch.setenv("AGENTCLAW_SQLITE_PATH", str(sqlite_path))
    role_plan = build_p3394_role_plan(
        "按 P3394 架构分析并改造这个项目",
        {"family": "p3394_architecture", "target": "agentic_runtime"},
    )

    history_id = record_p3394_task_history(
        workflow_id="p3394_runtime_agent",
        thread_id="thread-1",
        request="按 P3394 架构分析并改造这个项目",
        route={"family": "p3394_architecture", "target": "agentic_runtime"},
        role_plan=role_plan,
        status="routed",
    )
    rows = list_p3394_task_history(workflow_id="p3394_runtime_agent")

    assert sqlite_path.exists()
    assert rows[0]["id"] == history_id
    assert rows[0]["thread_id"] == "thread-1"
    assert rows[0]["route"]["family"] == "p3394_architecture"
    assert rows[0]["role_plan"][0]["role"] == "P3394 Planner"


def test_p3394_task_history_can_update_role_plan_status(monkeypatch, tmp_path):
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
    completed_plan = [{**step, "status": "completed"} for step in role_plan]

    updated = update_p3394_task_history(
        history_id=history_id,
        workflow_id="p3394_runtime_agent",
        role_plan=completed_plan,
        status="completed",
    )

    rows = list_p3394_task_history(workflow_id="p3394_runtime_agent")
    assert updated is True
    assert rows[0]["id"] == history_id
    assert rows[0]["status"] == "completed"
    assert {step["status"] for step in rows[0]["role_plan"]} == {"completed"}
    assert rows[0]["updated_at"] >= rows[0]["created_at"]


@pytest.mark.asyncio
async def test_p3394_finalize_node_completes_visible_role_plan(monkeypatch, tmp_path):
    from agentclaw.graph.context import WorkflowContext

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
    execution_id = record_p3394_execution_record(
        workflow_id="p3394_runtime_agent",
        thread_id="thread-1",
        task_history_id=history_id,
        request="按 P3394 架构分析这个项目",
        route={"family": "p3394_architecture", "target": "agentic_runtime"},
        status="running",
    )
    node = P3394FinalizeNode(id="p3394_finalize", output_to_user=False)

    result = await node.async_execute(
        {
            "p3394_task_history_id": history_id,
            "p3394_execution_record_id": execution_id,
            "p3394_role_plan": role_plan,
            "answer": "项目可以按 P3394 的 manifest、adapter、session、audit 层拆解。",
        },
        WorkflowContext(thread_id="thread-1"),
    )

    rows = list_p3394_task_history(workflow_id="p3394_runtime_agent")
    execution_rows = list_p3394_execution_records(workflow_id="p3394_runtime_agent")
    assert result["p3394_execution_status"] == "completed"
    assert {step["status"] for step in result["p3394_role_plan"]} == {"completed"}
    assert rows[0]["status"] == "completed"
    assert {step["status"] for step in rows[0]["role_plan"]} == {"completed"}
    assert result["p3394_execution_record_id"] == execution_id
    assert execution_rows[0]["status"] == "completed"
    assert execution_rows[0]["answer_preview"] == "项目可以按 P3394 的 manifest、adapter、session、audit 层拆解。"


@pytest.mark.asyncio
async def test_p3394_finalize_node_recovers_history_from_thread_id(monkeypatch, tmp_path):
    from agentclaw.graph.context import WorkflowContext

    sqlite_path = tmp_path / "agentclaw-local.db"
    monkeypatch.setenv("AGENTCLAW_SQLITE_PATH", str(sqlite_path))
    role_plan = build_p3394_role_plan(
        "按 P3394 架构分析这个项目",
        {"family": "p3394_architecture", "target": "agentic_runtime"},
    )
    history_id = record_p3394_task_history(
        workflow_id="p3394_runtime_agent",
        thread_id="thread-fallback",
        request="按 P3394 架构分析这个项目",
        route={"family": "p3394_architecture", "target": "agentic_runtime"},
        role_plan=role_plan,
        status="routed",
    )
    execution_id = record_p3394_execution_record(
        workflow_id="p3394_runtime_agent",
        thread_id="thread-fallback",
        task_history_id=history_id,
        request="按 P3394 架构分析这个项目",
        route={"family": "p3394_architecture", "target": "agentic_runtime"},
        status="running",
    )
    node = P3394FinalizeNode(id="p3394_finalize", output_to_user=False)

    result = await node.async_execute(
        {"answer": "按 P3394 看，这个项目已经具备 runtime shell。"},
        WorkflowContext(thread_id="thread-fallback"),
    )

    rows = list_p3394_task_history(workflow_id="p3394_runtime_agent")
    execution_rows = list_p3394_execution_records(workflow_id="p3394_runtime_agent")
    assert result["p3394_task_history_id"] == history_id
    assert result["p3394_execution_record_id"] == execution_id
    assert result["p3394_execution_status"] == "completed"
    assert rows[0]["status"] == "completed"
    assert {step["status"] for step in rows[0]["role_plan"]} == {"completed"}
    assert execution_rows[0]["status"] == "completed"


@pytest.mark.asyncio
async def test_p3394_init_node_creates_running_execution_record(monkeypatch, tmp_path):
    from agentclaw.agent_square.p3394_runtime_agent.agents.p3394_runtime_agent import P3394InitNode
    from agentclaw.graph.context import WorkflowContext

    sqlite_path = tmp_path / "agentclaw-local.db"
    monkeypatch.setenv("AGENTCLAW_SQLITE_PATH", str(sqlite_path))
    node = P3394InitNode(id="p3394_init", output_to_user=False)

    result = await node.async_execute(
        {
            "user_input": "按 P3394 架构分析这个项目",
            "relationship": "owner",
        },
        WorkflowContext(thread_id="thread-init-execution"),
    )

    rows = list_p3394_execution_records(workflow_id="p3394_runtime_agent")
    assert result["__p3394_complete__"] is False
    assert result["p3394_execution_record_id"] == rows[0]["id"]
    assert rows[0]["status"] == "running"
    assert rows[0]["thread_id"] == "thread-init-execution"
    assert rows[0]["task_history_id"] == result["p3394_task_history_id"]
    assert rows[0]["route"]["family"] == "p3394_architecture"


@pytest.mark.asyncio
async def test_p3394_init_node_records_file_context(monkeypatch, tmp_path):
    from agentclaw.agent_square.p3394_runtime_agent.agents.p3394_runtime_agent import P3394InitNode
    from agentclaw.graph.context import WorkflowContext

    sqlite_path = tmp_path / "agentclaw-local.db"
    monkeypatch.setenv("AGENTCLAW_SQLITE_PATH", str(sqlite_path))
    readme = tmp_path / "README.md"
    readme.write_text("# P3394\n\nRuntime notes.\n", encoding="utf-8")
    node = P3394InitNode(id="p3394_init", output_to_user=False)

    result = await node.async_execute(
        {
            "user_input": f"按 P3394 架构分析 {readme}",
            "relationship": "owner",
        },
        WorkflowContext(thread_id="thread-file-context"),
    )

    rows = list_p3394_file_contexts(workflow_id="p3394_runtime_agent")
    assert result["__p3394_complete__"] is False
    assert result["p3394_file_context_ids"] == [rows[0]["id"]]
    assert rows[0]["thread_id"] == "thread-file-context"
    assert rows[0]["path"] == str(readme)
    assert rows[0]["file_type"] == "markdown"


def test_p3394_manifest_declares_multi_agent_role_runtime():
    capability_names = {capability["name"] for capability in P3394_MANIFEST["capabilities"]}

    assert "p3394.multi_agent_roles" in capability_names
    assert "p3394.task_history" in capability_names
    assert "p3394.file_context" in capability_names
    assert "internal_role_runtime" in P3394_MANIFEST["conformance"]["implemented"]
    assert "internal_role_trace" in P3394_MANIFEST["conformance"]["implemented"]
    assert "sqlite_file_context" in P3394_MANIFEST["conformance"]["implemented"]


def test_p3394_detects_task_history_queries():
    capability, message_type = _detect_capability("查看 P3394 任务历史", {})

    assert capability == "p3394.task_history"
    assert message_type == "agent.query"


def test_p3394_detects_file_context_queries():
    capability, message_type = _detect_capability("查看 P3394 文件上下文", {})

    assert capability == "p3394.file_context"
    assert message_type == "agent.query"


def test_p3394_auto_memory_extracts_preferences_and_project_facts():
    candidates = extract_p3394_auto_memory_candidates(
        "我喜欢 AgentClaw 原版那种简洁界面。这个项目叫 P3394 Agent Platform，必须能执行命令。"
    )

    titles = {item["title"] for item in candidates}
    assert "用户偏好：AgentClaw 原版那种简洁界面" in titles
    assert "项目事实：P3394 Agent Platform" in titles
    assert "能力需求：能执行命令" in titles
    assert all(item["source"] == "auto_memory" for item in candidates)


def test_p3394_auto_memory_extracts_natural_user_phrasing():
    candidates = extract_p3394_auto_memory_candidates(
        "我喜欢极简但功能强的界面。这个项目叫 P3394 Memory Platform，必须支持本地知识库和执行命令。"
    )

    titles = {item["title"] for item in candidates}
    assert "用户偏好：极简但功能强的界面" in titles
    assert "项目事实：P3394 Memory Platform" in titles
    assert "能力需求：支持本地知识库和执行命令" in titles


def test_p3394_knowledge_write_creates_daily_markdown_and_graph(monkeypatch, tmp_path):
    sqlite_path = tmp_path / "agentclaw-local.db"
    memory_dir = tmp_path / "p3394-memory"
    monkeypatch.setenv("AGENTCLAW_SQLITE_PATH", str(sqlite_path))
    monkeypatch.setenv("AGENTCLAW_P3394_MEMORY_DIR", str(memory_dir))

    add_p3394_knowledge_item(
        workflow_id="p3394_runtime_agent",
        title="User prefers compact UI",
        content="The user wants a clean AgentClaw-like interface.",
        source="auto_memory",
        tags=["auto-memory", "preference"],
        metadata={"memory_category": "user_preference"},
    )

    notes = list_p3394_daily_memory_notes("p3394_runtime_agent", limit=5)
    graph = get_p3394_memory_graph_summary("p3394_runtime_agent", limit=50)
    content = notes[0]["path"] and __import__("pathlib").Path(notes[0]["path"]).read_text(encoding="utf-8")
    labels = {node["label"] for node in graph["nodes"]}
    relations = {edge["relation"] for edge in graph["edges"]}

    assert len(notes) == 1
    assert notes[0]["entry_count"] == 1
    assert notes[0]["title"] == "Daily Memory"
    assert "[[User prefers compact UI]]" in content
    assert "The user wants a clean AgentClaw-like interface." in content
    assert "\u6bcf\u65e5\u8bb0\u5fc6" in labels
    assert "User prefers compact UI" in labels
    assert "records" in relations


def test_p3394_daily_memory_timeline_backfills_days_and_extracts_links(monkeypatch, tmp_path):
    sqlite_path = tmp_path / "agentclaw-local.db"
    memory_dir = tmp_path / "p3394-memory"
    monkeypatch.setenv("AGENTCLAW_SQLITE_PATH", str(sqlite_path))
    monkeypatch.setenv("AGENTCLAW_P3394_MEMORY_DIR", str(memory_dir))

    add_p3394_knowledge_item(
        workflow_id="p3394_runtime_agent",
        title="P3394 Graph",
        content="Daily graph memory should expose wikilinks and tags.",
        source="auto_memory",
        tags=["auto-memory", "graph"],
        metadata={"memory_category": "memory_graph", "date_key": "2026-05-30"},
    )

    timeline = get_p3394_daily_memory_timeline(
        "p3394_runtime_agent",
        days=3,
        end_date="2026-06-01",
    )
    graph = get_p3394_memory_graph_summary("p3394_runtime_agent", limit=100)
    labels = {node["label"] for node in graph["nodes"]}

    assert [note["date_key"] for note in timeline] == ["2026-06-01", "2026-05-31", "2026-05-30"]
    assert timeline[0]["entry_count"] == 0
    assert timeline[1]["entry_count"] == 0
    assert timeline[2]["entry_count"] == 1
    assert "P3394 Graph" in timeline[2]["wikilinks"]
    assert "auto-memory" in timeline[2]["markdown_tags"]
    assert "\u6bcf\u65e5\u8bb0\u5fc6" in labels
    assert {"2026-06-01", "2026-05-31", "2026-05-30"}.issubset(labels)
    assert "auto-memory" in labels
    assert any(
        edge["source_label"] == "2026-05-30"
        and edge["relation"] == "mentions"
        and edge["target_label"] == "P3394 Graph"
        for edge in graph["edges"]
    )
    assert any(
        edge["source_label"] == "2026-05-30"
        and edge["relation"] == "tagged"
        and edge["target_label"] == "auto-memory"
        for edge in graph["edges"]
    )


@pytest.mark.asyncio
async def test_p3394_init_node_auto_persists_memory_candidates(monkeypatch, tmp_path):
    from agentclaw.agent_square.p3394_runtime_agent.agents.p3394_runtime_agent import P3394InitNode
    from agentclaw.graph.context import WorkflowContext

    sqlite_path = tmp_path / "agentclaw-local.db"
    monkeypatch.setenv("AGENTCLAW_SQLITE_PATH", str(sqlite_path))
    node = P3394InitNode(id="p3394_init", output_to_user=False)

    result = await node.async_execute(
        {
            "user_input": "我喜欢简洁的 AgentClaw 原版界面。这个项目叫 P3394 Agent Platform，必须能执行命令。",
            "relationship": "owner",
        },
        WorkflowContext(thread_id="thread-auto-memory"),
    )

    items = list_p3394_knowledge_items("p3394_runtime_agent", limit=20)
    graph = get_p3394_memory_graph_summary("p3394_runtime_agent", limit=50)
    titles = {item["title"] for item in items}
    labels = {node["label"] for node in graph["nodes"]}
    assert result["p3394_auto_memory_count"] >= 3
    assert "用户偏好：简洁的 AgentClaw 原版界面" in titles
    assert "项目事实：P3394 Agent Platform" in titles
    assert "能力需求：能执行命令" in titles
    assert "自动记忆" in labels
    assert "用户偏好" in labels
    assert graph["edge_count"] >= 3


@pytest.mark.asyncio
async def test_p3394_init_node_returns_file_context_summary(monkeypatch, tmp_path):
    from agentclaw.agent_square.p3394_runtime_agent.agents.p3394_runtime_agent import P3394InitNode
    from agentclaw.graph.context import WorkflowContext

    sqlite_path = tmp_path / "agentclaw-local.db"
    monkeypatch.setenv("AGENTCLAW_SQLITE_PATH", str(sqlite_path))
    notes = tmp_path / "README.md"
    notes.write_text("P3394 context summary", encoding="utf-8")
    record_p3394_file_contexts_from_state(
        workflow_id="p3394_runtime_agent",
        thread_id="thread-file-query",
        request=f"读取 {notes}",
        state={},
    )
    node = P3394InitNode(id="p3394_init", output_to_user=False)

    result = await node.async_execute(
        {
            "user_input": "查看 P3394 文件上下文",
            "relationship": "owner",
        },
        WorkflowContext(thread_id="thread-file-query"),
    )

    assert result["__p3394_complete__"] is True
    assert result["p3394_payload"]["count"] == 1
    assert result["p3394_payload"]["contexts"][0]["display_name"] == "README.md"
    assert "README.md" in result["p3394_runtime_agent"]


@pytest.mark.asyncio
async def test_p3394_output_channel_persists_tool_records(monkeypatch, tmp_path):
    from agentclaw.runtime.streaming.context import OutputChannel

    sqlite_path = tmp_path / "agentclaw-local.db"
    monkeypatch.setenv("AGENTCLAW_SQLITE_PATH", str(sqlite_path))
    channel = OutputChannel(workflow_id="p3394_runtime_agent", thread_id="thread-tools")

    await channel.push_tool(
        tool_call_id="call-1",
        tool_name="execute_command",
        tool_arguments='{"command":"pwd","cwd":"D:\\\\codex\\\\ui"}',
        tool_result="[stdout]\nD:\\codex\\ui\nexit code 0",
        tool_status="succeeded",
        batch_id="round-1",
        node="agent",
    )

    rows = list_p3394_tool_records("p3394_runtime_agent")
    assert len(rows) == 1
    assert rows[0]["thread_id"] == "thread-tools"
    assert rows[0]["tool_call_id"] == "call-1"
    assert rows[0]["tool_name"] == "execute_command"
    assert rows[0]["command"] == "pwd"
    assert rows[0]["cwd"] == "D:\\codex\\ui"
    assert rows[0]["stdout"] == "D:\\codex\\ui"
    assert rows[0]["exit_code"] == 0
