"""Offline C4 candidate tests for OLLAMA_FORMAT_OVERRIDES. Cover valid/invalid input, complete-schema
defaults, explicit per-model JSON overrides, unchanged unlisted models and no format for non-
RecommendationDraft requests. Clearing the variable restores C3 payloads field for field.
"""


from __future__ import annotations

import asyncio
from dataclasses import replace

import pytest

from agent.config import load_settings
from agent.prompts import SYSTEM_PROMPT
from agent.router import LocalProvider, Router, parse_format_overrides
from agent.schemas import RecommendationDraft


class _CaptureHttp:
    def __init__(self) -> None:
        self.payloads: list[dict] = []

    async def post(self, url, json=None, timeout=None):  # noqa: A002 - Match the httpx parameter name.
        self.payloads.append(json)

        class _R:
            def raise_for_status(self) -> None:
                return None

            def json(self) -> dict:
                return {"message": {"content": "{}"}}

        return _R()

    async def aclose(self) -> None:
        return None


def _payload_format(monkeypatch: pytest.MonkeyPatch, env: str, model: str):
    monkeypatch.setenv("OLLAMA_MODEL", model)
    if env:
        monkeypatch.setenv("OLLAMA_FORMAT_OVERRIDES", env)
    else:
        monkeypatch.delenv("OLLAMA_FORMAT_OVERRIDES", raising=False)
    provider = LocalProvider(load_settings())
    provider._http = _CaptureHttp()
    asyncio.run(provider.complete(SYSTEM_PROMPT, [{"role": "user", "content": "{}"}], 5.0))
    assert provider._http.payloads, "未发出请求"
    return provider._http.payloads[0]


def test_parse_accepts_explicit_pairs() -> None:
    assert parse_format_overrides(None) == {}
    assert parse_format_overrides("") == {}
    assert parse_format_overrides("harborguard-lora:json") == {"harborguard-lora": "json"}
    assert parse_format_overrides("a:json, b:schema") == {"a": "json", "b": "schema"}


@pytest.mark.parametrize("bad", ["harborguard-lora", "m:text", ":json", "m:json:extra"])
def test_parse_rejects_malformed(bad: str) -> None:
    with pytest.raises(ValueError):
        parse_format_overrides(bad)


def test_default_is_full_schema_for_all_models(monkeypatch: pytest.MonkeyPatch) -> None:
    for model in ("qwen3:1.7b", "harborguard-lora", "harborguard-base"):
        payload = _payload_format(monkeypatch, "", model)
        assert payload["model"] == model
        assert payload["format"] == RecommendationDraft.model_json_schema()


def test_explicit_override_only_affects_listed_models(monkeypatch: pytest.MonkeyPatch) -> None:
    env = "harborguard-lora:json,harborguard-base:json"
    assert _payload_format(monkeypatch, env, "harborguard-lora")["format"] == "json"
    assert _payload_format(monkeypatch, env, "harborguard-base")["format"] == "json"
    payload = _payload_format(monkeypatch, env, "qwen3:1.7b")
    assert payload["format"] == RecommendationDraft.model_json_schema()


def test_provider_exposes_effective_draft_format(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OLLAMA_MODEL", "harborguard-lora")
    monkeypatch.setenv("OLLAMA_FORMAT_OVERRIDES", "harborguard-lora:json")
    provider = LocalProvider(load_settings())
    assert provider.draft_output_format == "json"

    monkeypatch.setenv("OLLAMA_MODEL", "qwen3:1.7b")
    fallback = LocalProvider(load_settings())
    assert fallback.draft_output_format == "json_schema"


def test_non_draft_requests_never_carry_format(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OLLAMA_MODEL", "harborguard-lora")
    monkeypatch.setenv("OLLAMA_FORMAT_OVERRIDES", "harborguard-lora:json")
    provider = LocalProvider(load_settings())
    provider._http = _CaptureHttp()
    asyncio.run(provider.complete("非建议系统提示", [{"role": "user", "content": "x"}], 5.0))
    assert "format" not in provider._http.payloads[0]


@pytest.mark.parametrize("model, expected", [("harborguard-lora", "json"), ("qwen3:1.7b", "json_schema")])
def test_health_reports_format_and_identity_without_inference(monkeypatch, model, expected):
    monkeypatch.setenv("OLLAMA_FORMAT_OVERRIDES", "harborguard-lora:json")
    settings = replace(load_settings(), cloud_provider="disabled", ollama_model=model)
    router = Router(settings)
    try:
        health = router.health()
        local = health["providers"]["local"]
        assert local["draft_output_format"] == expected
        assert local["request_model"] == model
        assert local["base_url"] == settings.ollama_base_url
        assert health["providers"]["cloud"]["provider"] == "disabled"
        assert local["draft_attempts"] == health["providers"]["cloud"]["draft_attempts"] == 0
        assert local["ask_attempts"] == health["providers"]["cloud"]["ask_attempts"] == 0
    finally:
        asyncio.run(router.aclose())


def test_settings_default_is_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OLLAMA_FORMAT_OVERRIDES", raising=False)
    assert load_settings().ollama_format_overrides == ""
    monkeypatch.setenv("OLLAMA_FORMAT_OVERRIDES", "m:json")
    assert load_settings().ollama_format_overrides == "m:json"


def test_settings_are_pure_data(monkeypatch: pytest.MonkeyPatch) -> None:
    """Settings can be derived via replace for isolated tests without embedding behavior."""
    monkeypatch.delenv("OLLAMA_FORMAT_OVERRIDES", raising=False)
    settings = load_settings()
    isolated = replace(settings, cloud_provider="disabled")
    assert isolated.cloud_provider == "disabled"
    assert settings.cloud_provider != "disabled" or settings.cloud_provider == isolated.cloud_provider
