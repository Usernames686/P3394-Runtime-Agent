import pytest

from agentclaw.agent_square.p3394_runtime_agent.agents.p3394_runtime_agent import (
    P3394_AGENT_SYSTEM_PROMPT,
    P3394_MANIFEST,
    _select_route,
)
from agentclaw.agent_square.p3394_runtime_agent.agents.p3394_reference import (
    build_p3394_reference_prompt,
    find_p3394_reference_path,
)


pytestmark = pytest.mark.unit


def test_p3394_reference_loader_finds_local_draft_document():
    path = find_p3394_reference_path()

    assert path is not None
    assert path.name == "P3394-v0.9.0-combined(2).md"
    assert path.exists()


def test_p3394_system_prompt_injects_local_architecture_reference_and_roles():
    reference = build_p3394_reference_prompt()

    assert "P3394 local architecture reference" in reference
    assert "IEEE P3394" in reference
    for concept in [
        "agent manifest",
        "channel adapter",
        "Universal Message Format",
        "session model",
        "non-escalation",
        "conformance",
    ]:
        assert concept.lower() in reference.lower()

    for role in [
        "P3394 Planner",
        "P3394 Researcher",
        "P3394 Executor",
        "P3394 Reviewer",
    ]:
        assert role in P3394_AGENT_SYSTEM_PROMPT


def test_p3394_manifest_and_router_support_architecture_mode():
    capability_names = {capability["name"] for capability in P3394_MANIFEST["capabilities"]}
    route_families = {route["family"] for route in P3394_MANIFEST["orchestration"]["routes"]}

    assert "p3394.architecture_reference" in capability_names
    assert "p3394_architecture" in route_families

    route = _select_route(
        "按 P3394 架构分析并改造这个项目",
        {"body": {"input": {}}, "message_type": "agent.request"},
    )

    assert route["family"] == "p3394_architecture"
    assert route["target"] == "agentic_runtime"


def test_p3394_router_keeps_markdown_creation_on_local_runtime():
    route = _select_route(
        "给我在桌面写一个关于 P3394 的 md 文档",
        {"body": {"input": {}}, "message_type": "agent.request"},
    )

    assert route["family"] == "code_command"
    assert route["target"] == "agentic_runtime"


def test_p3394_router_delegates_existing_document_analysis():
    route = _select_route(
        "分析这个合同文档的风险",
        {"body": {"input": {"documents": ["contract.pdf"]}}, "message_type": "agent.request"},
    )

    assert route["family"] == "document_analysis"
    assert route["target"] == "doc_analyzer"
