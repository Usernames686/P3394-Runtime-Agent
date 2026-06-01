import json
from pathlib import Path

import pytest


pytestmark = pytest.mark.unit


PROJECT_ROOT = Path(__file__).resolve().parents[3]
AGENT_SQUARE_DIR = PROJECT_ROOT / "agentclaw" / "agent_square"

EXAMPLE_TEMPLATE_IDS = {
    "hello_world",
    "router",
    "tool_agent",
    "approval",
    "parallel",
    "gif_agent",
    "mcp_agent",
    "custom_demo",
    "weekly_report",
    "doc_analyzer",
    "kb_rag",
}


def test_example_workflows_are_packaged_as_template_library_apps():
    from agentclaw.agent_square import get_claw_app, list_claw_apps

    apps = {app["id"]: app for app in list_claw_apps()}

    assert EXAMPLE_TEMPLATE_IDS.issubset(apps)
    assert "smart_agent" not in apps
    for app_id in EXAMPLE_TEMPLATE_IDS:
        app = get_claw_app(app_id)
        assert app is not None, app_id
        assert app["category"] == "example"
        assert app["copyable"] is True
        assert app["inspectable"] is True
        assert app["recommended_input"]
        assert app["workflow_id"]
        assert Path(app["workflow_path"]).is_file()
        assert Path(app["entry_path"]).is_file()
        assert "示例" in app["tags"] or "Example" in app["tags"]
        assert not (Path(app["app_dir"]) / "server.py").exists()
        assert not (Path(app["app_dir"]) / "models.json").exists()
        assert not (Path(app["app_dir"]) / ".env").exists()


def test_p3394_runtime_agent_is_packaged_as_a_builtin_template():
    from agentclaw.agent_square import get_claw_app

    app = get_claw_app("p3394_runtime_agent")

    assert app is not None
    assert app["name"] == "P3394 Runtime Agent"
    assert app["category"] == "standard"
    assert app["workflow_id"] == "p3394_runtime_agent"
    assert app["recommended_input"]
    assert "P3394" in app["tags"]
    assert Path(app["workflow_path"]).is_file()
    assert Path(app["entry_path"]).is_file()


def test_p3394_runtime_agent_registers_as_a_workflow():
    from agentclaw.agent_square import register_claw_app_workflows
    from agentclaw.api.registry import WorkflowRegistry

    WorkflowRegistry.unregister("p3394_runtime_agent")
    try:
        result = register_claw_app_workflows("p3394_runtime_agent")

        assert result["registered_workflow_ids"] == ["p3394_runtime_agent"]
        workflow = WorkflowRegistry.get("p3394_runtime_agent")
        assert workflow is not None
        structure = workflow.get_structure()
        assert structure["user_input_field"] == "user_input"
        user_input = next(field for field in structure["form_config"] if field["name"] == "user_input")
        assert user_input["label"] == "输入任务，或直接让我运行命令"
    finally:
        WorkflowRegistry.unregister("p3394_runtime_agent")


def test_p3394_runtime_agent_is_agentclaw_like_llm_agent():
    from agentclaw.agent_square import register_claw_app_workflows
    from agentclaw.api.registry import WorkflowRegistry
    from agentclaw.node.llm import LLMNode

    WorkflowRegistry.unregister("p3394_runtime_agent")
    try:
        register_claw_app_workflows("p3394_runtime_agent")
        workflow = WorkflowRegistry.get("p3394_runtime_agent")

        assert list(workflow._nodes) == ["p3394_init", "smart_prefilter", "agent", "p3394_finalize"]
        agent = workflow._nodes["agent"]
        finalize = workflow._nodes["p3394_finalize"]
        assert isinstance(agent, LLMNode)
        assert agent.agent_style == "agentic"
        assert agent.user_prompt == "{p3394_init}"
        assert agent.skills == "*"
        assert agent.enable_builtin_skills is True
        assert agent.tools == "*"
        assert agent.enable_builtin_tools is True
        assert agent.enable_memory is True
        assert agent.stream is True
        assert agent.output_to_user is True
        assert agent.tools_filter_key == "__filtered_tools__"
        assert agent.skills_filter_key == "__filtered_skill_names__"
        assert finalize.output_to_user is False
    finally:
        WorkflowRegistry.unregister("p3394_runtime_agent")


@pytest.mark.asyncio
async def test_p3394_runtime_agent_init_exposes_langgraph_prompt_key():
    from agentclaw.agent_square import register_claw_app_workflows
    from agentclaw.api.registry import WorkflowRegistry
    from agentclaw.graph.context import WorkflowContext

    WorkflowRegistry.unregister("p3394_runtime_agent")
    try:
        register_claw_app_workflows("p3394_runtime_agent")
        workflow = WorkflowRegistry.get("p3394_runtime_agent")
        init_node = workflow._nodes["p3394_init"]

        result = await init_node.async_execute(
            {"user_input": "list project files", "relationship": "owner"},
            WorkflowContext(thread_id="p3394-prompt"),
        )

        assert result["__p3394_complete__"] is False
        assert "Internal P3394 routing context" in result["p3394_init"]
        assert "User request:" in result["p3394_init"]
        assert "Respond to the user normally" in result["p3394_init"]
        assert "```json" not in result["p3394_init"]
        assert "UMF-style Envelope" not in result["p3394_init"]
    finally:
        WorkflowRegistry.unregister("p3394_runtime_agent")


@pytest.mark.asyncio
async def test_p3394_runtime_agent_streams_user_visible_output():
    from agentclaw.agent_square import register_claw_app_workflows
    from agentclaw.api.registry import WorkflowRegistry
    from agentclaw.graph.context import WorkflowContext
    from agentclaw.runtime.streaming.context import OutputChannel

    WorkflowRegistry.unregister("p3394_runtime_agent")
    try:
        register_claw_app_workflows("p3394_runtime_agent")
        workflow = WorkflowRegistry.get("p3394_runtime_agent")

        async with OutputChannel(
            workflow_id=workflow.id,
            thread_id="p3394-output",
            stream_mode=True,
        ) as channel:
            await workflow.run(
                {"user_input": "manifest.describe"},
                WorkflowContext(thread_id="p3394-output"),
                thread_id="p3394-output",
            )

        answer = channel.get_answer()
        assert "# P3394 Manifest" in answer
        assert "UMF-style Envelope" in answer
    finally:
        WorkflowRegistry.unregister("p3394_runtime_agent")


@pytest.mark.asyncio
async def test_p3394_runtime_agent_manifest_exposes_level2_contract():
    from agentclaw.agent_square import register_claw_app_workflows
    from agentclaw.api.registry import WorkflowRegistry
    from agentclaw.graph.context import WorkflowContext

    WorkflowRegistry.unregister("p3394_runtime_agent")
    try:
        register_claw_app_workflows("p3394_runtime_agent")
        workflow = WorkflowRegistry.get("p3394_runtime_agent")
        init_node = workflow._nodes["p3394_init"]

        result = await init_node.async_execute(
            {"user_input": "manifest.describe", "relationship": "owner"},
            WorkflowContext(thread_id="p3394-manifest-v2"),
        )

        manifest = result["p3394_payload"]
        capability_names = {capability["name"] for capability in manifest["capabilities"]}
        responsibilities = manifest["channel_adapter"]["responsibilities"]

        assert manifest["agent"]["conformance_level"] == "level_2_agentclaw_runtime"
        assert manifest["default_input"]["entry_point"] == "handle_message"
        assert responsibilities == [
            "listen",
            "extract_channel_unique_id",
            "validate_security",
            "resolve_service_principal",
            "resolve_relationship",
            "validate_semantic_blocks",
            "normalize_to_umf",
            "deliver_to_handle_message",
        ]
        assert {
            "manifest.describe",
            "message.normalize",
            "session.create",
            "session.fetch",
            "session.close",
            "audit.summary",
            "conformance.check",
            "command_execution",
            "task.route",
            "agent.delegate",
        }.issubset(capability_names)
        assert manifest["orchestration"]["mode"] == "route_then_execute"
        assert {route["family"] for route in manifest["orchestration"]["routes"]} >= {
            "code_command",
            "document_analysis",
            "knowledge_search",
            "general_chat",
        }
        assert {"owner", "administrator", "peer", "client", "anonymous"} <= set(manifest["relationships"])
        assert manifest["security_context_policy"]["levels"] == ["normal", "elevated"]
        assert "semantic_block_constraints" in manifest
        assert manifest["conformance"]["target_level"] == "level_2"
    finally:
        WorkflowRegistry.unregister("p3394_runtime_agent")


@pytest.mark.asyncio
async def test_p3394_runtime_agent_standardizes_umf_input_and_output():
    from agentclaw.agent_square import register_claw_app_workflows
    from agentclaw.api.registry import WorkflowRegistry
    from agentclaw.graph.context import WorkflowContext

    WorkflowRegistry.unregister("p3394_runtime_agent")
    try:
        register_claw_app_workflows("p3394_runtime_agent")
        workflow = WorkflowRegistry.get("p3394_runtime_agent")
        init_node = workflow._nodes["p3394_init"]

        result = await init_node.async_execute(
            {
                "user_input": "message.normalize",
                "relationship": "client",
                "umf_message": {
                    "message_id": "msg-inbound-1",
                    "canonical_session_id": "sess-existing",
                    "parent_session_id": "sess-parent",
                    "sender": {
                        "principal": "alice@example.com",
                        "service_principal": {
                            "person": "alice@example.com",
                            "org": "acme-corp",
                            "role": "analyst",
                        },
                    },
                    "metadata": {
                        "channel": "workflow_api",
                        "session_lifecycle": "open",
                    },
                    "body": {
                        "content": "normalize this request",
                        "input": {"topic": "supplier risk"},
                    },
                },
            },
            WorkflowContext(thread_id="p3394-normalize-v2"),
        )

        normalized = result["p3394_payload"]
        response = result["p3394_response_message"]

        assert normalized["message_id"] == "msg-inbound-1"
        assert normalized["message_type"] == "agent.query"
        assert normalized["canonical_session_id"] == "sess-existing"
        assert normalized["parent_session_id"] == "sess-parent"
        assert normalized["sender"]["principal"] == "alice@example.com"
        assert normalized["sender"]["service_principal"] == {
            "person": "alice@example.com",
            "org": "acme-corp",
            "role": "analyst",
        }
        assert normalized["body"]["content"] == "normalize this request"
        assert normalized["body"]["input"] == {"topic": "supplier risk"}
        assert normalized["metadata"]["channel"] == "workflow_api"
        assert normalized["metadata"]["session_lifecycle"] == "open"
        assert response["message_type"] == "agent.response"
        assert response["in_reply_to"] == "msg-inbound-1"
        assert response["canonical_session_id"] == "sess-existing"
        assert response["body"]["capability"] == "message.normalize"
    finally:
        WorkflowRegistry.unregister("p3394_runtime_agent")


@pytest.mark.asyncio
async def test_p3394_runtime_agent_session_lifecycle_audit_and_conformance_commands():
    from agentclaw.agent_square import register_claw_app_workflows
    from agentclaw.agent_square.p3394_runtime_agent.agents import p3394_runtime_agent as p3394_module
    from agentclaw.api.registry import WorkflowRegistry
    from agentclaw.graph.context import WorkflowContext

    p3394_module.SESSION_STORE.clear()
    if hasattr(p3394_module, "AUDIT_EVENTS"):
        p3394_module.AUDIT_EVENTS.clear()

    WorkflowRegistry.unregister("p3394_runtime_agent")
    try:
        register_claw_app_workflows("p3394_runtime_agent")
        workflow = WorkflowRegistry.get("p3394_runtime_agent")
        init_node = workflow._nodes["p3394_init"]
        context = WorkflowContext(thread_id="p3394-session-v2")

        created = await init_node.async_execute(
            {"user_input": "session.create: contract review", "relationship": "owner"},
            context,
        )
        session_id = created["p3394_payload"]["canonical_session_id"]

        fetched = await init_node.async_execute(
            {
                "user_input": "session.fetch",
                "relationship": "owner",
                "umf_message": {"canonical_session_id": session_id},
            },
            context,
        )
        closed = await init_node.async_execute(
            {
                "user_input": "session.close",
                "relationship": "owner",
                "umf_message": {"canonical_session_id": session_id},
            },
            context,
        )
        audit = await init_node.async_execute(
            {
                "user_input": "audit.summary",
                "relationship": "administrator",
                "umf_message": {"canonical_session_id": session_id},
            },
            context,
        )
        conformance = await init_node.async_execute(
            {"user_input": "conformance.check", "relationship": "owner"},
            context,
        )

        assert created["p3394_payload"]["lifecycle"] == "open"
        assert fetched["p3394_payload"]["canonical_session_id"] == session_id
        assert fetched["p3394_payload"]["lifecycle"] == "open"
        assert closed["p3394_payload"]["canonical_session_id"] == session_id
        assert closed["p3394_payload"]["lifecycle"] == "closed"
        assert closed["p3394_umf_message"]["message_type"] == "session.close"
        assert audit["p3394_payload"]["total_events"] >= 4
        assert {"session.create", "session.fetch", "session.close"} <= {
            event["message_type"] for event in audit["p3394_payload"]["events"]
        }
        assert conformance["p3394_payload"]["target_level"] == "level_2"
        assert conformance["p3394_payload"]["status"] == "pass"
        assert all(check["status"] == "pass" for check in conformance["p3394_payload"]["checks"])
    finally:
        WorkflowRegistry.unregister("p3394_runtime_agent")


@pytest.mark.asyncio
async def test_p3394_runtime_agent_denies_unauthorized_capability_before_llm_execution():
    from agentclaw.agent_square import register_claw_app_workflows
    from agentclaw.api.registry import WorkflowRegistry
    from agentclaw.graph.context import WorkflowContext

    WorkflowRegistry.unregister("p3394_runtime_agent")
    try:
        register_claw_app_workflows("p3394_runtime_agent")
        workflow = WorkflowRegistry.get("p3394_runtime_agent")
        init_node = workflow._nodes["p3394_init"]

        result = await init_node.async_execute(
            {
                "user_input": "run Get-Location",
                "relationship": "anonymous",
                "umf_message": {
                    "capability": "command_execution",
                    "body": {"content": "run Get-Location"},
                },
            },
            WorkflowContext(thread_id="p3394-auth-v2"),
        )

        assert result["__p3394_complete__"] is True
        assert result["p3394_payload"]["message_type"] == "agent.error"
        assert result["p3394_payload"]["reason_code"] == "authorization_failed"
        assert result["p3394_audit"]["status"] == "denied"
    finally:
        WorkflowRegistry.unregister("p3394_runtime_agent")


@pytest.mark.asyncio
async def test_p3394_runtime_agent_authorized_command_execution_reaches_agentic_runtime():
    from agentclaw.agent_square import register_claw_app_workflows
    from agentclaw.api.registry import WorkflowRegistry
    from agentclaw.graph.context import WorkflowContext

    WorkflowRegistry.unregister("p3394_runtime_agent")
    try:
        register_claw_app_workflows("p3394_runtime_agent")
        workflow = WorkflowRegistry.get("p3394_runtime_agent")
        init_node = workflow._nodes["p3394_init"]

        result = await init_node.async_execute(
            {
                "user_input": "run Get-Location",
                "relationship": "owner",
                "umf_message": {
                    "capability": "command_execution",
                    "message_type": "agent.command",
                    "body": {"content": "run Get-Location"},
                },
            },
            WorkflowContext(thread_id="p3394-command-v2"),
        )

        assert result["__p3394_complete__"] is False
        assert result["p3394_umf_message"]["body"]["capability"] == "command_execution"
        assert result["p3394_payload"]["runtime"] == "LLMNode(agent_style='agentic')"
        assert "tools" in result["p3394_payload"]
        assert "skills" in result["p3394_payload"]
        assert "Use AgentClaw tools/skills when useful" in result["p3394_init"]
        assert "Do not expose UMF, manifests, audit objects, or route JSON" in result["p3394_init"]
        assert "Do not explain internal routing, sessions, audit, UMF, or role plans unless explicitly asked" in result["p3394_init"]
    finally:
        WorkflowRegistry.unregister("p3394_runtime_agent")


@pytest.mark.asyncio
async def test_p3394_runtime_agent_routes_tasks_to_agentclaw_targets():
    from agentclaw.agent_square import register_claw_app_workflows
    from agentclaw.api.registry import WorkflowRegistry
    from agentclaw.graph.context import WorkflowContext

    WorkflowRegistry.unregister("p3394_runtime_agent")
    try:
        register_claw_app_workflows("p3394_runtime_agent")
        workflow = WorkflowRegistry.get("p3394_runtime_agent")
        init_node = workflow._nodes["p3394_init"]

        cases = [
            ("task.route: analyze this PDF contract", "document_analysis", "doc_analyzer"),
            ("task.route: search GitHub for agent protocol examples", "knowledge_search", "tool_agent"),
            ("task.route: run pytest and fix code", "code_command", "agentic_runtime"),
            ("task.route: Run this harmless command and report the output: echo p3394-smoke", "code_command", "agentic_runtime"),
            ("task.route: hello, explain what you can do", "general_chat", "agentic_runtime"),
        ]

        for text, family, target in cases:
            result = await init_node.async_execute(
                {"user_input": text, "relationship": "owner"},
                WorkflowContext(thread_id=f"p3394-route-{family}"),
            )

            route = result["p3394_payload"]["selected_route"]
            assert result["__p3394_complete__"] is True
            assert route["family"] == family
            assert route["target"] == target
            assert result["p3394_umf_message"]["body"]["capability"] == "task.route"
            assert result["p3394_audit"]["details"]["route"]["family"] == family
    finally:
        WorkflowRegistry.unregister("p3394_runtime_agent")


@pytest.mark.asyncio
async def test_p3394_runtime_agent_routes_chinese_natural_requests_without_protocol_prefix():
    from agentclaw.agent_square import register_claw_app_workflows
    from agentclaw.api.registry import WorkflowRegistry
    from agentclaw.graph.context import WorkflowContext

    WorkflowRegistry.unregister("p3394_runtime_agent")
    try:
        register_claw_app_workflows("p3394_runtime_agent")
        workflow = WorkflowRegistry.get("p3394_runtime_agent")
        init_node = workflow._nodes["p3394_init"]

        cases = [
            ("帮我跑测试并修复代码", "code_command", "agentic_runtime"),
            ("去网上搜索 P3394 的资料", "knowledge_search", "tool_agent"),
            ("分析这个合同的风险", "document_analysis", "doc_analyzer"),
        ]

        for text, family, target in cases:
            result = await init_node.async_execute(
                {"user_input": text, "relationship": "owner"},
                WorkflowContext(thread_id=f"p3394-natural-{family}"),
            )

            route = result["p3394_route"]
            assert result["p3394_umf_message"]["body"]["capability"] == "task.route"
            assert route["family"] == family
            assert route["target"] == target
    finally:
        WorkflowRegistry.unregister("p3394_runtime_agent")


@pytest.mark.asyncio
async def test_p3394_runtime_agent_auto_delegates_natural_search_to_registered_tool_agent():
    from agentclaw import Workflow
    from agentclaw.agent_square import register_claw_app_workflows
    from agentclaw.api.registry import WorkflowRegistry
    from agentclaw.graph.context import WorkflowContext

    delegate = Workflow(
        id="tool_agent",
        name="Tool Agent",
        inputs={"user_input": {"type": "string", "required": True}},
        user_input="user_input",
    )

    @delegate.node(id="echo", output_to_user=False)
    def echo_node(state):
        return {"delegate_answer": f"tool-agent searched: {state.get('user_input')}"}

    WorkflowRegistry.unregister("p3394_runtime_agent")
    WorkflowRegistry.unregister("tool_agent")
    try:
        register_claw_app_workflows("p3394_runtime_agent")
        WorkflowRegistry.register(delegate)
        workflow = WorkflowRegistry.get("p3394_runtime_agent")
        init_node = workflow._nodes["p3394_init"]

        result = await init_node.async_execute(
            {"user_input": "去网上搜索 P3394 的资料", "relationship": "owner"},
            WorkflowContext(thread_id="p3394-auto-delegate-search"),
        )

        payload = result["p3394_payload"]
        assert result["__p3394_complete__"] is True
        assert result["p3394_route"]["family"] == "knowledge_search"
        assert payload["status"] == "succeeded"
        assert payload["target_workflow_id"] == "tool_agent"
        assert payload["result_state"]["delegate_answer"] == "tool-agent searched: 去网上搜索 P3394 的资料"
        assert result["p3394_audit"]["status"] == "delegated"
    finally:
        WorkflowRegistry.unregister("p3394_runtime_agent")
        WorkflowRegistry.unregister("tool_agent")


@pytest.mark.asyncio
async def test_p3394_runtime_agent_delegation_streams_natural_answer_not_protocol_dump():
    from agentclaw import Workflow
    from agentclaw.agent_square import register_claw_app_workflows
    from agentclaw.api.registry import WorkflowRegistry
    from agentclaw.graph.context import WorkflowContext
    from agentclaw.runtime.streaming.context import OutputChannel

    delegate = Workflow(
        id="tool_agent",
        name="Tool Agent",
        inputs={"user_input": {"type": "string", "required": True}},
        user_input="user_input",
    )

    @delegate.node(id="echo", output_to_user=False)
    def echo_node(state):
        return {"delegate_answer": f"tool-agent searched: {state.get('user_input')}"}

    WorkflowRegistry.unregister("p3394_runtime_agent")
    WorkflowRegistry.unregister("tool_agent")
    try:
        register_claw_app_workflows("p3394_runtime_agent")
        WorkflowRegistry.register(delegate)
        workflow = WorkflowRegistry.get("p3394_runtime_agent")
        user_input = "\u53bb\u7f51\u4e0a\u641c\u7d22 P3394 \u7684\u8d44\u6599"

        async with OutputChannel(
            workflow_id=workflow.id,
            thread_id="p3394-natural-delegation-output",
            stream_mode=True,
        ) as channel:
            await workflow.run(
                {"user_input": user_input, "relationship": "owner"},
                WorkflowContext(thread_id="p3394-natural-delegation-output"),
                thread_id="p3394-natural-delegation-output",
            )

        answer = channel.get_answer()
        assert f"tool-agent searched: {user_input}" in answer
        assert "# P3394 Routed Delegation" not in answer
        assert "## Payload" not in answer
        assert "UMF-style Envelope" not in answer
    finally:
        WorkflowRegistry.unregister("p3394_runtime_agent")
        WorkflowRegistry.unregister("tool_agent")


@pytest.mark.asyncio
async def test_p3394_runtime_agent_regular_task_enters_agentic_runtime_with_route_context():
    from agentclaw.agent_square import register_claw_app_workflows
    from agentclaw.api.registry import WorkflowRegistry
    from agentclaw.graph.context import WorkflowContext

    WorkflowRegistry.unregister("p3394_runtime_agent")
    try:
        register_claw_app_workflows("p3394_runtime_agent")
        workflow = WorkflowRegistry.get("p3394_runtime_agent")
        init_node = workflow._nodes["p3394_init"]

        result = await init_node.async_execute(
            {"user_input": "run pytest and fix code", "relationship": "owner"},
            WorkflowContext(thread_id="p3394-route-runtime"),
        )

        assert result["__p3394_complete__"] is False
        assert result["p3394_umf_message"]["body"]["capability"] == "task.route"
        assert result["p3394_payload"]["selected_route"]["family"] == "code_command"
        assert result["p3394_payload"]["runtime"] == "LLMNode(agent_style='agentic')"
        assert "Internal P3394 routing context" in result["p3394_init"]
        assert "route: code_command -> agentic_runtime" in result["p3394_init"]
        assert "Selected orchestration route" not in result["p3394_init"]
        assert result["p3394_route"]["target"] == "agentic_runtime"
    finally:
        WorkflowRegistry.unregister("p3394_runtime_agent")


@pytest.mark.asyncio
async def test_p3394_runtime_agent_delegates_to_registered_workflow_and_audits_target():
    from agentclaw import Workflow
    from agentclaw.agent_square import register_claw_app_workflows
    from agentclaw.api.registry import WorkflowRegistry
    from agentclaw.graph.context import WorkflowContext

    delegate = Workflow(
        id="p3394_delegate_echo",
        name="P3394 Delegate Echo",
        inputs={"user_input": {"type": "string", "required": True}},
        user_input="user_input",
    )

    @delegate.node(id="echo", output_to_user=False)
    def echo_node(state):
        return {"delegate_answer": f"delegated: {state.get('user_input')}"}

    WorkflowRegistry.unregister("p3394_runtime_agent")
    WorkflowRegistry.unregister("p3394_delegate_echo")
    try:
        register_claw_app_workflows("p3394_runtime_agent")
        WorkflowRegistry.register(delegate)
        workflow = WorkflowRegistry.get("p3394_runtime_agent")
        init_node = workflow._nodes["p3394_init"]

        result = await init_node.async_execute(
            {
                "user_input": "agent.delegate",
                "relationship": "owner",
                "umf_message": {
                    "capability": "agent.delegate",
                    "message_type": "agent.command",
                    "body": {
                        "content": "delegate to echo",
                        "input": {
                            "target_workflow_id": "p3394_delegate_echo",
                            "delegation_inputs": {"user_input": "hello child workflow"},
                        },
                    },
                },
            },
            WorkflowContext(thread_id="p3394-delegate-v1"),
        )

        payload = result["p3394_payload"]
        assert result["__p3394_complete__"] is True
        assert payload["status"] == "succeeded"
        assert payload["target_workflow_id"] == "p3394_delegate_echo"
        assert payload["result_state"]["delegate_answer"] == "delegated: hello child workflow"
        assert result["p3394_audit"]["status"] == "delegated"
        assert result["p3394_audit"]["details"]["delegated_to"] == "p3394_delegate_echo"
    finally:
        WorkflowRegistry.unregister("p3394_runtime_agent")
        WorkflowRegistry.unregister("p3394_delegate_echo")


@pytest.mark.asyncio
async def test_p3394_runtime_agent_denies_anonymous_delegation():
    from agentclaw.agent_square import register_claw_app_workflows
    from agentclaw.api.registry import WorkflowRegistry
    from agentclaw.graph.context import WorkflowContext

    WorkflowRegistry.unregister("p3394_runtime_agent")
    try:
        register_claw_app_workflows("p3394_runtime_agent")
        workflow = WorkflowRegistry.get("p3394_runtime_agent")
        init_node = workflow._nodes["p3394_init"]

        result = await init_node.async_execute(
            {
                "user_input": "agent.delegate",
                "relationship": "anonymous",
                "umf_message": {
                    "capability": "agent.delegate",
                    "body": {"input": {"target_workflow_id": "hello_world"}},
                },
            },
            WorkflowContext(thread_id="p3394-delegate-denied"),
        )

        assert result["__p3394_complete__"] is True
        assert result["p3394_payload"]["reason_code"] == "authorization_failed"
        assert result["p3394_audit"]["status"] == "denied"
    finally:
        WorkflowRegistry.unregister("p3394_runtime_agent")


def test_legacy_examples_project_has_been_removed():
    assert not (PROJECT_ROOT / "agentclaw" / "examples").exists()


def test_example_template_manifests_have_unique_workflow_ids():
    workflow_ids: dict[str, str] = {}
    for manifest_path in AGENT_SQUARE_DIR.glob("*/claw_app.json"):
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        workflow_id = str(manifest.get("workflow_id") or manifest.get("id") or "")
        assert workflow_id not in workflow_ids, f"{workflow_id} duplicated by {manifest_path} and {workflow_ids.get(workflow_id)}"
        workflow_ids[workflow_id] = str(manifest_path)


def test_example_templates_expose_a_chat_launch_path():
    from agentclaw.agent_square import register_claw_app_workflows
    from agentclaw.api.registry import WorkflowRegistry

    registered_ids: list[str] = []
    try:
        for app_id in EXAMPLE_TEMPLATE_IDS:
            result = register_claw_app_workflows(app_id)
            registered_ids.extend(result["registered_workflow_ids"])
            workflow_id = result["registered_workflow_ids"][0]
            workflow = WorkflowRegistry.get(workflow_id)
            structure = workflow.get_structure()
            form_config = structure.get("form_config") or []
            user_input_field = structure.get("user_input_field")

            assert user_input_field or form_config, f"{app_id} has no user input or form start fields"
            if user_input_field:
                assert any(field["name"] == user_input_field for field in form_config), app_id

        weekly = WorkflowRegistry.get("weekly_report").get_structure()
        custom = WorkflowRegistry.get("custom_demo").get_structure()
        doc = WorkflowRegistry.get("doc_analyzer").get_structure()
        assert weekly["user_input_field"] == "user_input"
        assert custom["user_input_field"] == "user_input"
        assert doc["user_input_field"] is None
        assert {field["name"] for field in doc["form_config"]} == {"documents", "question"}
    finally:
        for workflow_id in registered_ids:
            WorkflowRegistry.unregister(workflow_id)


def test_agent_square_workflow_module_name_preserves_package_context():
    from agentclaw.agent_square import _workflow_module_name

    assert (
        _workflow_module_name(
            {"app_dir": str(AGENT_SQUARE_DIR / "werewolf_agent"), "workflow": "agents/werewolf.py"}
        )
        == "agentclaw.agent_square.werewolf_agent.agents.werewolf"
    )


def test_importing_resource_backed_example_templates_copies_support_files(tmp_path):
    from agentclaw.agent_square import import_claw_app_to_project

    gif_import = import_claw_app_to_project("gif_agent", tmp_path)
    gif_target = Path(gif_import["target_dir"])
    assert gif_import["workflow_id"] == "gif_agent"
    assert (gif_target / "agents" / "gif_agent.py").is_file()
    assert (gif_target / "skills" / "slack-gif-creator" / "SKILL.md").is_file()
    assert (gif_target / "skills" / "slack-gif-creator" / "core" / "gif_builder.py").is_file()

    mcp_import = import_claw_app_to_project("mcp_agent", tmp_path)
    mcp_target = Path(mcp_import["target_dir"])
    assert mcp_import["workflow_id"] == "mcp_agent"
    assert (mcp_target / "agents" / "mcp_agent.py").is_file()
    assert (mcp_target / "mcps" / "example_tools.py").is_file()
    assert (mcp_target / "mcp.json").is_file()

    agents_init = tmp_path / "agents" / "__init__.py"
    init_text = agents_init.read_text(encoding="utf-8")
    assert "AgentClaw template import: gif_agent" in init_text
    assert "AgentClaw template import: mcp_agent" in init_text


def test_imported_gif_agent_discovers_its_packaged_skill(tmp_path, monkeypatch):
    from agentclaw.agent_square import import_claw_app_to_project
    from agentclaw.config import get_config

    import_result = import_claw_app_to_project("gif_agent", tmp_path)
    workflow_file = Path(import_result["workflow_file"])
    monkeypatch.setattr(get_config().project, "project_dir", tmp_path)

    namespace: dict[str, object] = {"__file__": str(workflow_file)}
    code = workflow_file.read_text(encoding="utf-8")
    exec(compile(code, str(workflow_file), "exec"), namespace)
    workflow = namespace["workflow"]

    assert workflow._find_skills_dir() == workflow_file.parent.parent / "skills"


def test_example_templates_register_workflows_without_cross_publishing():
    from agentclaw.agent_square import register_claw_app_workflows
    from agentclaw.api.registry import WorkflowRegistry

    for workflow_id in EXAMPLE_TEMPLATE_IDS:
        WorkflowRegistry.unregister(workflow_id)
    for workflow_id in ["turtle_soup", "ai_werewolf"]:
        WorkflowRegistry.unregister(workflow_id)

    gif_result = register_claw_app_workflows("gif_agent")
    assert gif_result["registered_workflow_ids"] == ["gif_agent"]
    assert WorkflowRegistry.get("gif_agent") is not None

    mcp_result = register_claw_app_workflows("mcp_agent")
    assert mcp_result["registered_workflow_ids"] == ["mcp_agent"]
    assert WorkflowRegistry.get("mcp_agent") is not None

    for workflow_id in EXAMPLE_TEMPLATE_IDS:
        WorkflowRegistry.unregister(workflow_id)
