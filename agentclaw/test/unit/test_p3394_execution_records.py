import pytest

from agentclaw.agent_square.p3394_runtime_agent.agents.p3394_execution_records import (
    complete_p3394_execution_record,
    list_p3394_execution_records,
    record_p3394_execution_record,
)


pytestmark = pytest.mark.unit


def test_p3394_execution_records_persist_and_complete_to_sqlite(monkeypatch, tmp_path):
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
    updated = complete_p3394_execution_record(
        record_id=record_id,
        workflow_id="p3394_runtime_agent",
        answer_preview="项目可以按 manifest、adapter、session、audit 层拆解。",
        role_statuses=["completed", "completed", "completed", "completed"],
        status="completed",
    )

    rows = list_p3394_execution_records(workflow_id="p3394_runtime_agent")
    assert updated is True
    assert rows[0]["id"] == record_id
    assert rows[0]["thread_id"] == "thread-1"
    assert rows[0]["task_history_id"] == "p3394_task_1"
    assert rows[0]["route"]["family"] == "p3394_architecture"
    assert rows[0]["status"] == "completed"
    assert rows[0]["answer_preview"] == "项目可以按 manifest、adapter、session、audit 层拆解。"
    assert rows[0]["role_statuses"] == ["completed", "completed", "completed", "completed"]
    assert rows[0]["completed_at"] >= rows[0]["created_at"]
