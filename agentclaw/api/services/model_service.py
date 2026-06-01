"""
模型服务 - 封装模型管理业务逻辑
"""

import time
from typing import Any, Optional

from agentclaw.logger.config import get_logger

logger = get_logger(__name__)

NON_CONVERSATION_MODEL_TYPES = {"embedding", "rerank", "speech2text", "tts"}

MODEL_TEST_MESSAGES = [
    {"role": "system", "content": "Reply with exactly: ok"},
    {"role": "user", "content": "health check"},
]


class ModelService:
    """模型服务"""
    
    def __init__(self, llm_manager=None):
        self._llm_manager = llm_manager
    
    def list_models(self) -> dict:
        """获取所有模型列表和降级状态"""
        if not self._llm_manager:
            return {"models": [], "fallback_state": {}}
        
        models = []
        for config in self._llm_manager.get_all_models():
            info = self._llm_manager.get_model_info(config.id)
            if info:
                models.append(info)
        
        fallback_state = self._llm_manager.get_fallback_state()
        
        return {
            "models": models,
            "fallback_state": fallback_state,
        }
    
    def list_available_models(self) -> dict:
        """获取可用模型列表（用于节点模型切换）"""
        if not self._llm_manager:
            return {"models": [], "default_model_id": None}

        models = []
        for config in self._llm_manager.get_all_models():
            model_type = str(config.model_type or "chat").strip().lower()
            if model_type in NON_CONVERSATION_MODEL_TYPES:
                continue
            models.append({
                "id": config.id,
                "provider": config.provider,
                "model": config.model,
                "model_type": config.model_type,
                "supports_vision": getattr(config, "supports_vision", False),
            })

        return {
            "models": models,
            "default_model_id": self._llm_manager.default_id,
        }
    
    def get_model(self, model_id: str) -> Optional[dict]:
        """获取单个模型信息"""
        if not self._llm_manager:
            return None
        
        return self._llm_manager.get_model_info(model_id)
    
    def update_model(self, model_id: str, **params) -> Optional[dict]:
        """更新模型配置"""
        if not self._llm_manager:
            return None
        
        success = self._llm_manager.update_model_config(model_id, **params)
        if not success:
            return None
        
        return self._llm_manager.get_model_info(model_id)
    
    def force_fallback(self, model_id: str, reason: str = "手动触发") -> dict:
        """手动触发降级"""
        if not self._llm_manager:
            return {}
        
        self._llm_manager.force_fallback(reason)
        return self._llm_manager.get_fallback_state()
    
    def force_primary(self, model_id: str) -> dict:
        """恢复主模型"""
        if not self._llm_manager:
            return {}
        
        self._llm_manager.force_primary()
        return self._llm_manager.get_fallback_state()
    
    def get_model_diagnostics(self) -> dict:
        """Return non-secret readiness diagnostics for configured models."""
        if not self._llm_manager:
            return {
                "current_model_id": None,
                "default_model_id": None,
                "fallback_model_id": None,
                "models": [],
            }

        fallback_state = self._safe_fallback_state()
        return {
            "current_model_id": fallback_state.get("current_model_id"),
            "default_model_id": fallback_state.get("default_model_id"),
            "fallback_model_id": fallback_state.get("fallback_model_id"),
            "models": [
                self._diagnostic_for_config(config)
                for config in self._llm_manager.get_all_models()
            ],
        }

    async def test_model(self, model_id: str) -> dict:
        """Run a tiny completion request and return an actionable diagnostic."""
        if not self._llm_manager:
            return self._missing_model_diagnostic(model_id, "Model manager is not available.")

        config = self._find_config(model_id)
        if not config:
            return self._missing_model_diagnostic(
                model_id,
                f"Model '{model_id}' is not configured.",
            )

        diagnostic = self._diagnostic_for_config(config)
        if diagnostic["reason_code"] != "ok":
            return diagnostic

        start = time.perf_counter()
        try:
            result = await self._llm_manager.invoke(
                MODEL_TEST_MESSAGES,
                model_id=model_id,
                max_tokens=8,
                temperature=0,
                _max_attempts=1,
                _call_type="diagnostic",
            )
            latency_ms = int((time.perf_counter() - start) * 1000)
            sample = self._sample_from_response(result)
            return {
                **diagnostic,
                "ready": True,
                "reason_code": "ok",
                "message": "Model responded successfully.",
                "suggested_fix": None,
                "latency_ms": latency_ms,
                "sample": sample,
            }
        except Exception as exc:
            latency_ms = int((time.perf_counter() - start) * 1000)
            reason_code, message, suggested_fix = self._failure_reason(exc)
            return {
                **diagnostic,
                "ready": False,
                "reason_code": reason_code,
                "message": message,
                "suggested_fix": suggested_fix,
                "latency_ms": latency_ms,
                "sample": None,
            }

    def _safe_fallback_state(self) -> dict:
        try:
            return self._llm_manager.get_fallback_state() or {}
        except Exception:
            return {}

    def _find_config(self, model_id: str) -> Optional[Any]:
        for config in self._llm_manager.get_all_models():
            if getattr(config, "id", None) == model_id:
                return config
        return None

    def _diagnostic_for_config(self, config: Any) -> dict:
        model_id = getattr(config, "id", "")
        info = self._llm_manager.get_model_info(model_id) or {}
        provider = str(getattr(config, "provider", info.get("provider", "openai")) or "openai")
        model_type = str(getattr(config, "model_type", info.get("model_type", "chat")) or "chat")
        api_key_set = bool(str(getattr(config, "api_key", "") or "").strip())
        base_url_set = bool(str(getattr(config, "base_url", "") or "").strip())

        ready, reason_code, message, suggested_fix = self._static_readiness(
            provider=provider,
            model_type=model_type,
            api_key_set=api_key_set,
            base_url_set=base_url_set,
        )

        return {
            "id": model_id,
            "provider": provider,
            "model": str(getattr(config, "model", info.get("model", "")) or ""),
            "model_type": model_type,
            "status": info.get("status", "standby"),
            "is_current": bool(info.get("is_current", False)),
            "api_key_set": api_key_set,
            "base_url_set": base_url_set,
            "ready": ready,
            "reason_code": reason_code,
            "message": message,
            "suggested_fix": suggested_fix,
            "latency_ms": None,
            "sample": None,
        }

    def _static_readiness(
        self,
        *,
        provider: str,
        model_type: str,
        api_key_set: bool,
        base_url_set: bool,
    ) -> tuple[bool, str, str, Optional[str]]:
        if model_type.lower() in NON_CONVERSATION_MODEL_TYPES:
            return (
                False,
                "non_chat_model",
                "This model is not a chat model.",
                "Choose a chat-capable model for P3394 conversations.",
            )

        normalized_provider = provider.lower()
        if normalized_provider == "openai" and (api_key_set or base_url_set):
            return True, "ok", "Model configuration looks ready.", None
        if normalized_provider in {"azure", "anthropic"} and api_key_set:
            return True, "ok", "Model configuration looks ready.", None
        if normalized_provider == "custom":
            return True, "ok", "Custom model configuration is present.", None

        return (
            False,
            "missing_api_key",
            "Model API key is missing.",
            "Set api_key in models.json or configure an environment variable reference.",
        )

    def _missing_model_diagnostic(self, model_id: str, message: str) -> dict:
        return {
            "id": model_id,
            "provider": "",
            "model": "",
            "model_type": "chat",
            "status": "missing",
            "is_current": False,
            "api_key_set": False,
            "base_url_set": False,
            "ready": False,
            "reason_code": "missing_model",
            "message": message,
            "suggested_fix": "Add this model to models.json or select another configured model.",
            "latency_ms": None,
            "sample": None,
        }

    def _failure_reason(self, exc: Exception) -> tuple[str, str, str]:
        status_code = getattr(exc, "status_code", None)
        text = str(exc)
        lowered = text.lower()

        if "missing" in lowered and "api_key" in lowered:
            return (
                "missing_api_key",
                "Model API key is missing.",
                "Set api_key in models.json or configure an environment variable reference.",
            )
        if status_code in {401, 403} or any(token in lowered for token in ("unauthorized", "authentication", "permission denied")):
            return (
                "authentication_failed",
                "Model provider rejected the credentials.",
                "Check api_key, base_url, provider, and organization/project settings.",
            )
        if status_code == 404 or ("model" in lowered and "not found" in lowered):
            return (
                "model_not_found",
                "The provider could not find the configured model.",
                "Check the model name in models.json and make sure the key can access it.",
            )
        if isinstance(exc, TimeoutError) or any(token in lowered for token in ("timeout", "timed out")):
            return (
                "timeout",
                "Model request timed out.",
                "Increase timeout or check the provider/base_url network path.",
            )
        if any(token in lowered for token in ("base_url", "connection", "connect", "dns", "name resolution", "proxy")):
            return (
                "base_url_error",
                "Could not reach the configured model endpoint.",
                "Check base_url, proxy settings, and local network connectivity.",
            )
        return (
            "request_failed",
            text or "Model request failed.",
            "Open the server log for details, then check provider, model, key, and network settings.",
        )

    def _sample_from_response(self, result: Any) -> str:
        content = getattr(result, "content", result)
        if content is None:
            content = ""
        sample = str(content).strip()
        if len(sample) > 120:
            return sample[:117] + "..."
        return sample

    def get_usage_stats(self) -> dict:
        """获取模型使用统计"""
        if not self._llm_manager:
            return {}
        
        return self._llm_manager.get_usage_stats()


def get_model_service() -> ModelService:
    """获取模型服务实例"""
    llm_manager = None
    
    try:
        from agentclaw.api.registry import WorkflowRegistry
        workflows = WorkflowRegistry.list_all()
        if workflows:
            llm_manager = getattr(workflows[0], "_llm_manager", None)
    except Exception:
        pass
    
    return ModelService(llm_manager=llm_manager)
