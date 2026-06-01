import pytest

from agentclaw.agent_square.p3394_runtime_agent.agents.p3394_runtime_agent import (
    P3394_AGENT_SYSTEM_PROMPT,
    P3394_MANIFEST,
)


pytestmark = pytest.mark.unit


def test_p3394_prompt_names_local_engineering_tools():
    prompt = P3394_AGENT_SYSTEM_PROMPT

    for tool_name in [
        "project_overview",
        "read_file",
        "write_file",
        "shell",
        "powershell",
        "git_status",
        "git_diff",
        "git_commit_suggestions",
        "search_web",
    ]:
        assert tool_name in prompt

    assert "PowerShell" in prompt
    assert "PDF" in prompt
    assert "Markdown" in prompt


def test_p3394_prompt_defaults_to_execution_not_protocol_output():
    prompt = P3394_AGENT_SYSTEM_PROMPT

    assert "Default to doing the work" in prompt
    assert "Default to action" in prompt
    assert "normal model-language output" in prompt
    assert "not a P3394 spec dump" in prompt
    assert "Do not expose UMF" in prompt


def test_p3394_manifest_declares_local_project_tooling():
    capability_names = {capability["name"] for capability in P3394_MANIFEST["capabilities"]}

    assert "local_project_tooling" in capability_names
