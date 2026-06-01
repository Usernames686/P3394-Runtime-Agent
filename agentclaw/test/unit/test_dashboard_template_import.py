import pytest


pytestmark = pytest.mark.unit


def test_template_import_repairs_marker_without_import_statement(tmp_path):
    from agentclaw.agent_square import import_claw_app_to_project

    agents_dir = tmp_path / "agents"
    agents_dir.mkdir()
    init_path = agents_dir / "__init__.py"
    init_path.write_text(
        '"""Project workflows imported by AgentClaw."""\n'
        "# AgentClaw template import: ai_werewolf\n",
        encoding="utf-8",
    )

    result = import_claw_app_to_project("ai_werewolf", tmp_path)
    init_text = init_path.read_text(encoding="utf-8")

    assert result["import_added"] is True
    assert "from .ai_werewolf.agents.werewolf import workflow as ai_werewolf_workflow" in init_text


def test_project_discovery_prefers_explicit_agentclaw_project_dir(tmp_path, monkeypatch):
    from agentclaw.config import ProjectConfig

    package_like_dir = tmp_path / "package"
    explicit_project_dir = tmp_path / "local-demo"
    package_like_dir.mkdir()
    explicit_project_dir.mkdir()
    (package_like_dir / "agents").mkdir()
    (explicit_project_dir / "models.json").write_text('{"models": []}', encoding="utf-8")

    monkeypatch.chdir(package_like_dir)
    monkeypatch.setenv("AGENTCLAW_PROJECT_DIR", str(explicit_project_dir))

    project = ProjectConfig.discover()

    assert project.project_dir == explicit_project_dir.resolve()


@pytest.mark.asyncio
async def test_dashboard_imports_werewolf_template_as_project_package(tmp_path, monkeypatch):
    from agentclaw.api.registry import WorkflowRegistry
    from agentclaw.api.services.dashboard_service import DashboardService
    from agentclaw.config import AgentClawConfig, ProjectConfig

    models_path = tmp_path / "models.json"
    models_path.write_text('{"models": []}', encoding="utf-8")
    previous_config = AgentClawConfig._instance
    AgentClawConfig._instance = AgentClawConfig(
        project=ProjectConfig(
            project_dir=tmp_path,
            models_config=models_path,
        )
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    WorkflowRegistry.unregister("ai_werewolf")

    try:
        result = await DashboardService().import_template_library_app("ai_werewolf")
        workflow = WorkflowRegistry.get("ai_werewolf")
    finally:
        WorkflowRegistry.unregister("ai_werewolf")
        AgentClawConfig._instance = previous_config

    assert result["success"] is True
    assert result["registered"] is True
    assert result["workflow_id"] == "ai_werewolf"
    assert workflow is not None
    assert workflow.is_builtin is False
    assert workflow._models_config == str(models_path)


@pytest.mark.asyncio
async def test_dashboard_import_registers_existing_copied_werewolf_template(tmp_path, monkeypatch):
    from agentclaw.agent_square import import_claw_app_to_project
    from agentclaw.api.registry import WorkflowRegistry
    from agentclaw.api.services.dashboard_service import DashboardService
    from agentclaw.config import AgentClawConfig, ProjectConfig

    import_claw_app_to_project("ai_werewolf", tmp_path)
    models_path = tmp_path / "models.json"
    models_path.write_text('{"models": []}', encoding="utf-8")
    previous_config = AgentClawConfig._instance
    AgentClawConfig._instance = AgentClawConfig(
        project=ProjectConfig(
            project_dir=tmp_path,
            models_config=models_path,
        )
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    WorkflowRegistry.unregister("ai_werewolf")

    try:
        result = await DashboardService().import_template_library_app("ai_werewolf")
        workflow = WorkflowRegistry.get("ai_werewolf")
    finally:
        WorkflowRegistry.unregister("ai_werewolf")
        AgentClawConfig._instance = previous_config

    assert result["success"] is True
    assert result["registered"] is True
    assert result["imported"] is True
    assert result["import_added"] is False
    assert workflow is not None


@pytest.mark.asyncio
async def test_dashboard_repair_template_registers_existing_import_without_overwrite(tmp_path, monkeypatch):
    from agentclaw.agent_square import import_claw_app_to_project
    from agentclaw.api.registry import WorkflowRegistry
    from agentclaw.api.services.dashboard_service import DashboardService
    from agentclaw.config import AgentClawConfig, ProjectConfig

    import_result = import_claw_app_to_project("ai_werewolf", tmp_path)
    target_file = import_result["workflow_file"]
    models_path = tmp_path / "models.json"
    models_path.write_text('{"models": []}', encoding="utf-8")
    previous_config = AgentClawConfig._instance
    AgentClawConfig._instance = AgentClawConfig(
        project=ProjectConfig(
            project_dir=tmp_path,
            models_config=models_path,
        )
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    WorkflowRegistry.unregister("ai_werewolf")

    try:
        result = await DashboardService().repair_template_library_app("ai_werewolf")
        workflow = WorkflowRegistry.get("ai_werewolf")
    finally:
        WorkflowRegistry.unregister("ai_werewolf")
        AgentClawConfig._instance = previous_config

    assert result["success"] is True
    assert result["repaired"] is True
    assert result["imported"] is True
    assert result["registered"] is True
    assert result["target_dir"] == str(tmp_path / "agents" / "ai_werewolf")
    assert result["workflow_file"] == target_file
    assert workflow is not None
    assert workflow.is_builtin is False


@pytest.mark.asyncio
async def test_dashboard_repair_template_is_noop_when_registered(tmp_path, monkeypatch):
    from agentclaw.api.registry import WorkflowRegistry
    from agentclaw.api.services.dashboard_service import DashboardService
    from agentclaw.config import AgentClawConfig, ProjectConfig

    models_path = tmp_path / "models.json"
    models_path.write_text('{"models": []}', encoding="utf-8")
    previous_config = AgentClawConfig._instance
    AgentClawConfig._instance = AgentClawConfig(
        project=ProjectConfig(
            project_dir=tmp_path,
            models_config=models_path,
        )
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    WorkflowRegistry.unregister("ai_werewolf")

    try:
        imported = await DashboardService().import_template_library_app("ai_werewolf")
        repaired = await DashboardService().repair_template_library_app("ai_werewolf")
    finally:
        WorkflowRegistry.unregister("ai_werewolf")
        AgentClawConfig._instance = previous_config

    assert imported["registered"] is True
    assert repaired["success"] is True
    assert repaired["repaired"] is False
    assert repaired["registered"] is True
    assert repaired["workflow_id"] == "ai_werewolf"
