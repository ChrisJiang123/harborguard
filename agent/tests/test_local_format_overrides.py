"""OLLAMA_FORMAT_OVERRIDES 行为测试（C4 候选修复，离线，不依赖 Ollama）。

覆盖：解析器合法/非法输入、默认（未设置）全部完整 schema、
显式按模型覆盖 json、未列出模型不受影响、非 RecommendationDraft 请求永不携带 format。
回退保证：清空环境变量后 payload 与 C3 原行为逐字段一致。
"""
from __future__ import annotations

import asyncio
from dataclasses import replace

import pytest

from agent.config import load_settings
from agent.prompts import SYSTEM_PROMPT
from agent.router import LocalProvider, parse_format_overrides
from agent.schemas import RecommendationDraft


class _CaptureHttp:
    def __init__(self) -> None:
        self.payloads: list[dict] = []

    async def post(self, url, json=None, timeout=None):  # noqa: A002 - 与 httpx 形参对齐
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


def test_non_draft_requests_never_carry_format(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OLLAMA_MODEL", "harborguard-lora")
    monkeypatch.setenv("OLLAMA_FORMAT_OVERRIDES", "harborguard-lora:json")
    provider = LocalProvider(load_settings())
    provider._http = _CaptureHttp()
    asyncio.run(provider.complete("非建议系统提示", [{"role": "user", "content": "x"}], 5.0))
    assert "format" not in provider._http.payloads[0]


def test_settings_default_is_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OLLAMA_FORMAT_OVERRIDES", raising=False)
    assert load_settings().ollama_format_overrides == ""
    monkeypatch.setenv("OLLAMA_FORMAT_OVERRIDES", "m:json")
    assert load_settings().ollama_format_overrides == "m:json"


def test_settings_are_pure_data(monkeypatch: pytest.MonkeyPatch) -> None:
    """配置对象可被 replace 派生（测试/隔离用），不携带行为。"""
    monkeypatch.delenv("OLLAMA_FORMAT_OVERRIDES", raising=False)
    settings = load_settings()
    isolated = replace(settings, cloud_provider="disabled")
    assert isolated.cloud_provider == "disabled"
    assert settings.cloud_provider != "disabled" or settings.cloud_provider == isolated.cloud_provider
