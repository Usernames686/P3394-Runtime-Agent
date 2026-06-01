from dataclasses import dataclass

import pytest

from agentclaw.api.services.model_service import ModelService


@dataclass
class FakeConfig:
    id: str
    provider: str = "openai"
    model: str = "gpt-test"
    model_type: str = "chat"
    api_key: str | None = None
    base_url: str | None = None
    supports_vision: bool = False
    temperature: float = 0.1
    max_tokens: int = 1024
    timeout: int = 30


class FakeManager:
    default_id = "primary"
    fallback_id = "backup"

    def __init__(self, configs, response="pong", error: Exception | None = None):
        self._configs = {config.id: config for config in configs}
        self._response = response
        self._error = error
        self.invoke_calls = []

    def get_all_models(self):
        return list(self._configs.values())

    def get_model_info(self, model_id):
        config = self._configs.get(model_id)
        if not config:
            return None
        return {
            "id": config.id,
            "provider": config.provider,
            "model": config.model,
            "model_type": config.model_type,
            "supports_vision": config.supports_vision,
            "temperature": config.temperature,
            "max_tokens": config.max_tokens,
            "timeout": config.timeout,
            "status": "primary" if config.id == self.default_id else "standby",
            "is_current": config.id == self.default_id,
        }

    def get_fallback_state(self):
        return {
            "current_model_id": self.default_id,
            "default_model_id": self.default_id,
            "fallback_model_id": self.fallback_id,
        }

    async def invoke(self, messages, *, model_id=None, **kwargs):
        self.invoke_calls.append((messages, model_id, kwargs))
        if self._error:
            raise self._error
        return self._response


def test_model_diagnostics_marks_plain_openai_without_key_as_not_ready():
    manager = FakeManager([FakeConfig(id="primary")])
    service = ModelService(manager)

    payload = service.get_model_diagnostics()

    diagnostic = payload["models"][0]
    assert diagnostic["api_key_set"] is False
    assert diagnostic["base_url_set"] is False
    assert diagnostic["ready"] is False
    assert diagnostic["reason_code"] == "missing_api_key"
    assert "api_key" in diagnostic["suggested_fix"]


def test_model_diagnostics_allows_openai_compatible_base_url_without_key():
    manager = FakeManager([FakeConfig(id="primary", base_url="http://127.0.0.1:11434/v1")])
    service = ModelService(manager)

    diagnostic = service.get_model_diagnostics()["models"][0]

    assert diagnostic["api_key_set"] is False
    assert diagnostic["base_url_set"] is True
    assert diagnostic["ready"] is True
    assert diagnostic["reason_code"] == "ok"


@pytest.mark.asyncio
async def test_model_test_invokes_manager_and_returns_latency_sample():
    manager = FakeManager([FakeConfig(id="primary", api_key="sk-test")], response="pong")
    service = ModelService(manager)

    result = await service.test_model("primary")

    assert result["ready"] is True
    assert result["reason_code"] == "ok"
    assert result["latency_ms"] >= 0
    assert result["sample"] == "pong"
    assert manager.invoke_calls[0][1] == "primary"
    assert manager.invoke_calls[0][2]["_max_attempts"] == 1


@pytest.mark.asyncio
async def test_model_test_maps_timeout_errors_to_actionable_reason():
    manager = FakeManager(
        [FakeConfig(id="primary", api_key="sk-test")],
        error=TimeoutError("request timed out"),
    )
    service = ModelService(manager)

    result = await service.test_model("primary")

    assert result["ready"] is False
    assert result["reason_code"] == "timeout"
    assert "timeout" in result["suggested_fix"].lower()
