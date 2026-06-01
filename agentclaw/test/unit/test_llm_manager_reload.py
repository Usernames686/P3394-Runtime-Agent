import json

from agentclaw.model.manager import LLMManager


def _write_models(path, default="primary", fallback="backup", fast="quick"):
    path.write_text(
        json.dumps(
            {
                "default": default,
                "fallback": fallback,
                "fast": fast,
                "models": [
                    {"id": "primary", "model": "primary-model"},
                    {"id": "backup", "model": "backup-model"},
                    {"id": "quick", "model": "quick-model"},
                    {"id": "override-default", "model": "override-default-model"},
                    {"id": "override-fallback", "model": "override-fallback-model"},
                    {"id": "override-fast", "model": "override-fast-model"},
                ],
            }
        ),
        encoding="utf-8",
    )


def test_llm_manager_reload_preserves_constructor_model_overrides(tmp_path):
    models_path = tmp_path / "models.json"
    _write_models(models_path)
    manager = LLMManager(
        default="override-default",
        fallback="override-fallback",
        fast="override-fast",
        config_path=str(models_path),
    )

    _write_models(models_path, default="changed-default", fallback="changed-fallback", fast="changed-fast")
    manager.reload_models_config(str(models_path))

    assert manager.default_id == "override-default"
    assert manager.fallback_id == "override-fallback"
    assert manager.fast_id == "override-fast"


def test_llm_manager_uses_supports_vision_flag_for_vision_model(tmp_path):
    models_path = tmp_path / "models.json"
    models_path.write_text(
        json.dumps(
            {
                "default": "chat",
                "models": [
                    {"id": "chat", "type": "chat", "model": "chat-model"},
                    {"id": "vision_chat", "type": "chat", "supports_vision": True, "model": "vision-chat-model"},
                ],
            }
        ),
        encoding="utf-8",
    )

    manager = LLMManager(config_path=str(models_path))

    assert manager.get_vision_model_id() == "vision_chat"
    assert manager.get_model("vision_chat").model_type == "chat"
    assert manager.get_model("vision_chat").supports_vision is True


def test_llm_manager_treats_legacy_vision_type_as_chat_with_vision_support(tmp_path):
    models_path = tmp_path / "models.json"
    models_path.write_text(
        json.dumps(
            {
                "default": "chat",
                "models": [
                    {"id": "legacy_vision", "type": "vision", "model": "legacy-vision-model"},
                ],
            }
        ),
        encoding="utf-8",
    )

    manager = LLMManager(config_path=str(models_path))

    assert manager.get_model("legacy_vision").model_type == "chat"
    assert manager.get_model("legacy_vision").supports_vision is True
    assert manager.get_vision_model_id() == "legacy_vision"


def test_llm_manager_falls_back_to_first_model_when_default_aliases_are_empty(tmp_path):
    models_path = tmp_path / "models.json"
    models_path.write_text(
        json.dumps(
            {
                "default": "",
                "fast": "",
                "models": [
                    {"id": "model_1", "model": "gpt-5.5"},
                ],
            }
        ),
        encoding="utf-8",
    )

    manager = LLMManager(config_path=str(models_path))

    assert manager.get_model().id == "model_1"
    client, config = manager._get_current_client("fast")
    assert config.id == "model_1"
    assert client is manager._clients["model_1"]


def test_llm_manager_expands_model_and_base_url_env_references(tmp_path, monkeypatch):
    monkeypatch.setenv("P3394_MODEL_NAME", "env-model")
    monkeypatch.setenv("P3394_MODEL_BASE_URL", "https://example.test/v1")
    monkeypatch.setenv("P3394_MODEL_API_KEY", "env-key")
    models_path = tmp_path / "models.json"
    models_path.write_text(
        json.dumps(
            {
                "default": "model_1",
                "models": [
                    {
                        "id": "model_1",
                        "model": "${P3394_MODEL_NAME}",
                        "base_url": "${P3394_MODEL_BASE_URL}",
                        "api_key": "${P3394_MODEL_API_KEY}",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    manager = LLMManager(config_path=str(models_path))
    config = manager.get_model("model_1")

    assert config.model == "env-model"
    assert config.base_url == "https://example.test/v1"
    assert config.api_key == "env-key"
