from agentclaw.agent_square.p3394_runtime_agent.agents.p3394_file_context import (
    list_p3394_file_contexts,
    record_p3394_file_contexts_from_state,
)


def test_p3394_file_contexts_persist_attachments_and_referenced_markdown(
    monkeypatch,
    tmp_path,
):
    sqlite_path = tmp_path / "agentclaw-local.db"
    monkeypatch.setenv("AGENTCLAW_SQLITE_PATH", str(sqlite_path))
    readme = tmp_path / "README.md"
    readme.write_text("# Demo\n\nP3394 architecture notes.\n", encoding="utf-8")
    pdf = tmp_path / "spec.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")

    record_ids = record_p3394_file_contexts_from_state(
        workflow_id="p3394_runtime_agent",
        thread_id="thread-files",
        request=f"按 P3394 分析 {readme}",
        state={
            "__files__": [
                {
                    "original_name": "spec.pdf",
                    "path": str(pdf),
                    "mime_type": "application/pdf",
                    "size": 9,
                }
            ],
        },
    )

    rows = list_p3394_file_contexts(workflow_id="p3394_runtime_agent")
    by_path = {row["path"]: row for row in rows}
    assert len(record_ids) == 2
    assert sqlite_path.exists()
    assert str(readme) in by_path
    assert by_path[str(readme)]["source"] == "mentioned_path"
    assert by_path[str(readme)]["file_type"] == "markdown"
    assert "P3394 architecture notes" in by_path[str(readme)]["preview"]
    assert str(pdf) in by_path
    assert by_path[str(pdf)]["source"] == "attachment"
    assert by_path[str(pdf)]["file_type"] == "pdf"


def test_p3394_file_contexts_are_deduplicated_per_thread_and_path(
    monkeypatch,
    tmp_path,
):
    sqlite_path = tmp_path / "agentclaw-local.db"
    monkeypatch.setenv("AGENTCLAW_SQLITE_PATH", str(sqlite_path))
    notes = tmp_path / "notes.md"
    notes.write_text("first version", encoding="utf-8")

    first_ids = record_p3394_file_contexts_from_state(
        workflow_id="p3394_runtime_agent",
        thread_id="thread-files",
        request=f"看一下 {notes}",
        state={},
    )
    notes.write_text("second version", encoding="utf-8")
    second_ids = record_p3394_file_contexts_from_state(
        workflow_id="p3394_runtime_agent",
        thread_id="thread-files",
        request=f"重新看一下 {notes}",
        state={},
    )

    rows = list_p3394_file_contexts(workflow_id="p3394_runtime_agent")
    assert first_ids == second_ids
    assert len(rows) == 1
    assert rows[0]["preview"] == "second version"
