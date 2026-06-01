from pathlib import Path
import shutil
import subprocess

import pytest
from mcp.types import ListToolsRequest

from agentclaw.mcp.builtin_servers.skill_tools import SkillToolsServer


pytestmark = pytest.mark.unit


def _require_git() -> str:
    git = shutil.which("git")
    if not git:
        pytest.skip("git executable is not available")
    return git


async def _tool_names(server: SkillToolsServer) -> set[str]:
    result = await server._server.request_handlers[ListToolsRequest](ListToolsRequest())
    return {tool.name for tool in result.root.tools}


def _git(git: str, cwd: Path, *args: str) -> None:
    subprocess.run([git, *args], cwd=cwd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)


@pytest.mark.asyncio
async def test_git_and_project_tools_are_registered(tmp_path: Path):
    server = SkillToolsServer(working_dir=str(tmp_path), project_dir=str(tmp_path))

    names = await _tool_names(server)

    assert {"powershell", "git_status", "git_diff", "git_commit_suggestions", "project_overview", "search_web"} <= names


@pytest.mark.asyncio
async def test_git_status_reports_short_branch_status(tmp_path: Path):
    git = _require_git()
    _git(git, tmp_path, "init")
    (tmp_path / "README.md").write_text("hello", encoding="utf-8")
    server = SkillToolsServer(working_dir=str(tmp_path), project_dir=str(tmp_path))

    output = await server._git_status({})

    assert "git status --short --branch" in output
    assert "README.md" in output
    assert "Untracked" in output


@pytest.mark.asyncio
async def test_git_diff_reports_stat_and_patch(tmp_path: Path):
    git = _require_git()
    _git(git, tmp_path, "init")
    _git(git, tmp_path, "config", "user.email", "test@example.com")
    _git(git, tmp_path, "config", "user.name", "Test User")
    tracked = tmp_path / "app.py"
    tracked.write_text("print('old')\n", encoding="utf-8")
    _git(git, tmp_path, "add", "app.py")
    _git(git, tmp_path, "commit", "-m", "initial")
    tracked.write_text("print('new')\n", encoding="utf-8")
    server = SkillToolsServer(working_dir=str(tmp_path), project_dir=str(tmp_path))

    output = await server._git_diff({"path": "app.py", "max_chars": 4000})

    assert "git diff --stat -- app.py" in output
    assert "git diff -- app.py" in output
    assert "+print('new')" in output
    assert "-print('old')" in output


@pytest.mark.asyncio
async def test_git_commit_suggestions_summarize_changed_files(tmp_path: Path):
    git = _require_git()
    _git(git, tmp_path, "init")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "agent.py").write_text("print('p3394')\n", encoding="utf-8")
    server = SkillToolsServer(working_dir=str(tmp_path), project_dir=str(tmp_path))

    output = await server._git_commit_suggestions({})

    assert "Changed files" in output
    assert "src/agent.py" in output
    assert "Suggested commit messages" in output


@pytest.mark.asyncio
async def test_project_overview_detects_project_markers(tmp_path: Path):
    (tmp_path / "package.json").write_text('{"scripts":{"test":"vitest"}}', encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("print('hi')\n", encoding="utf-8")
    server = SkillToolsServer(working_dir=str(tmp_path), project_dir=str(tmp_path))

    output = await server._project_overview({})

    assert "Project overview" in output
    assert "package.json" in output
    assert "pyproject.toml" in output
    assert "src/" in output


@pytest.mark.asyncio
async def test_search_web_formats_results_without_external_service(monkeypatch, tmp_path: Path):
    server = SkillToolsServer(working_dir=str(tmp_path), project_dir=str(tmp_path))

    def fake_search(query: str, max_results: int):
        assert query == "P3394 agent protocol"
        assert max_results == 2
        return [
            {
                "title": "P3394 Agent Protocol",
                "url": "https://example.com/p3394",
                "snippet": "A software agent interoperability draft.",
            }
        ]

    monkeypatch.setattr(server, "_search_web_sync", fake_search)

    output = await server._search_web({"query": "P3394 agent protocol", "max_results": 2})

    assert "Web search results for: P3394 agent protocol" in output
    assert "P3394 Agent Protocol" in output
    assert "https://example.com/p3394" in output
    assert "interoperability draft" in output
