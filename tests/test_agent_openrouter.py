"""OpenRouter adapter: explicit selection, strict schema, diagnostics and deadlines."""

from __future__ import annotations

import asyncio
from dataclasses import replace
from types import SimpleNamespace

import pytest

from agent.config import get_settings
from agent.prompts import ASK_SYSTEM_PROMPT, SYSTEM_PROMPT
from agent.router import (
    AnthropicCloudProvider,
    DisabledCloudProvider,
    OpenRouterProvider,
    build_cloud_provider,
)


class FakeResponse:
    model = "google/gemini-2.5-flash"
    choices = [SimpleNamespace(message=SimpleNamespace(content='{"summary":"ok"}'))]
    model_extra = {"provider": "Google AI Studio"}

    def model_dump(self):
        return {
            "model": self.model,
            "provider": "Google AI Studio",
            "usage": {
                "prompt_tokens": 101,
                "completion_tokens": 23,
                "total_tokens": 124,
                "completion_tokens_details": {"reasoning_tokens": 7},
                "cost": 0.0000875,
            },
        }


class FakeCompletions:
    def __init__(self):
        self.calls = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        return FakeResponse()


class FakeClient:
    def __init__(self):
        self.completions = FakeCompletions()
        self.chat = SimpleNamespace(completions=self.completions)

    async def close(self):
        return None


def openrouter_settings(**updates):
    values = {
        "cloud_provider": "openrouter",
        "openrouter_api_key": "test-only-key",
        "openrouter_base_url": "https://openrouter.ai/api/v1",
        "openrouter_model": "google/gemini-2.5-flash",
    }
    values.update(updates)
    return replace(get_settings(), **values)


def test_explicit_provider_selection_ignores_legacy_credentials():
    settings = openrouter_settings(anthropic_auth_token="legacy-token")
    provider = build_cloud_provider(settings)
    assert isinstance(provider, OpenRouterProvider)
    assert provider.provider == "openrouter"
    assert provider.request_model == "google/gemini-2.5-flash"

    legacy = build_cloud_provider(replace(settings, cloud_provider="anthropic"))
    assert isinstance(legacy, AnthropicCloudProvider)
    disabled = build_cloud_provider(replace(settings, cloud_provider="disabled"))
    assert isinstance(disabled, DisabledCloudProvider)
    with pytest.raises(ValueError, match="CLOUD_PROVIDER"):
        build_cloud_provider(replace(settings, cloud_provider="auto"))


def test_missing_openrouter_key_disables_only_selected_adapter():
    provider = OpenRouterProvider(openrouter_settings(openrouter_api_key=None))
    assert provider.enabled is False
    assert provider._client is None


def test_recommendation_request_requires_schema_and_no_provider_fallback():
    async def run():
        provider = OpenRouterProvider(openrouter_settings())
        fake = FakeClient()
        provider._client = fake
        response = await provider.complete(
            SYSTEM_PROMPT,
            [{"role": "user", "content": "{}"}],
            1.25,
        )
        call = fake.completions.calls[0]
        assert call["model"] == "google/gemini-2.5-flash"
        assert call["timeout"] == 1.25
        assert call["extra_body"]["provider"] == {
            "require_parameters": True,
            "allow_fallbacks": False,
        }
        assert call["extra_body"]["usage"] == {"include": True}
        response_format = call["response_format"]
        assert response_format["type"] == "json_schema"
        assert response_format["json_schema"]["strict"] is True
        schema = response_format["json_schema"]["schema"]
        assert schema["additionalProperties"] is False
        assert set(schema["required"]) == {
            "summary", "explanation", "recommended_option_id",
            "evidence_ids", "uncertainties", "confidence",
        }
        assert response.response_model == "google/gemini-2.5-flash"
        assert response.upstream_provider == "Google AI Studio"
        assert response.usage == {
            "prompt_tokens": 101,
            "completion_tokens": 23,
            "total_tokens": 124,
            "reasoning_tokens": 7,
        }
        assert response.cost == 0.0000875
        await provider.aclose()

    asyncio.run(run())


def test_ask_keeps_provider_constraints_without_recommendation_schema():
    async def run():
        provider = OpenRouterProvider(openrouter_settings())
        fake = FakeClient()
        provider._client = fake
        await provider.complete(ASK_SYSTEM_PROMPT, [{"role": "user", "content": "hi"}], 1.0)
        call = fake.completions.calls[0]
        assert "response_format" not in call
        assert call["extra_body"]["provider"]["allow_fallbacks"] is False
        assert call["extra_body"]["provider"]["require_parameters"] is True

    asyncio.run(run())
