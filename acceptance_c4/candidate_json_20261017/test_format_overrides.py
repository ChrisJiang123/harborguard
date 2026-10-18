"""OLLAMA_FORMAT_OVERRIDES 单元验证：默认行为不变、显式覆盖生效、非法配置报错。

隔离运行（不改仓库测试目录）；直接构造 LocalProvider 并捕获 /api/chat payload。
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agent.config import load_settings
from agent.prompts import SYSTEM_PROMPT
from agent.router import LocalProvider, parse_format_overrides
from agent.schemas import RecommendationDraft


class CaptureHttp:
    def __init__(self):
        self.payloads = []

    async def post(self, url, json=None, timeout=None):
        self.payloads.append(json)

        class R:
            def raise_for_status(self):
                pass

            def json(self):
                return {"message": {"content": "{}"}, "model": "x"}

        return R()

    async def aclose(self):
        pass


def payload_format(env: str, model: str) -> str:
    os.environ["OLLAMA_FORMAT_OVERRIDES"] = env
    os.environ["OLLAMA_MODEL"] = model
    try:
        settings = load_settings()
        provider = LocalProvider(settings)
        provider._http = CaptureHttp()
        asyncio.run(provider.complete(SYSTEM_PROMPT, [{"role": "user", "content": "{}"}], 5.0))
        assert provider._http.payloads, "未发出请求"
        fmt = provider._http.payloads[0].get("format", "<absent>")
        assert provider._http.payloads[0]["model"] == model
        return "schema" if isinstance(fmt, dict) else fmt
    finally:
        os.environ.pop("OLLAMA_FORMAT_OVERRIDES", None)
        os.environ.pop("OLLAMA_MODEL", None)


def main() -> int:
    checks = []

    # 1) 未设环境变量：所有模型 schema（现状不变）
    os.environ.pop("OLLAMA_FORMAT_OVERRIDES", None)
    settings = load_settings()
    assert settings.ollama_format_overrides == ""
    assert parse_format_overrides(None) == {}
    assert parse_format_overrides("") == {}
    checks.append(("默认(未设) qwen3 → schema", payload_format("", "qwen3:1.7b") == "schema"))

    # 2) 显式覆盖：lora/base → json；未列出的模型不受影响
    env = "harborguard-lora:json,harborguard-base:json"
    checks.append(("覆盖后 harborguard-lora → json", payload_format(env, "harborguard-lora") == "json"))
    checks.append(("覆盖后 harborguard-base → json", payload_format(env, "harborguard-base") == "json"))
    checks.append(("覆盖后 qwen3:1.7b 仍 → schema", payload_format(env, "qwen3:1.7b") == "schema"))

    # 3) 显式 schema 覆盖与非法配置
    assert parse_format_overrides("m:schema") == {"m": "schema"}
    for bad in ("harborguard-lora", "m:text", ":json", "m:json:extra"):
        try:
            parse_format_overrides(bad)
        except ValueError:
            pass
        else:
            checks.append((f"非法配置应报错: {bad!r}", False))
    checks.append(("非法配置全部抛 ValueError", all(v for k, v in checks if k.startswith("非法"))))

    # 4) 空 system（非 SYSTEM_PROMPT 请求）永不带 format
    os.environ["OLLAMA_FORMAT_OVERRIDES"] = "harborguard-lora:json"
    try:
        provider = LocalProvider(load_settings())
        provider._http = CaptureHttp()
        asyncio.run(provider.complete("其它系统提示", [{"role": "user", "content": "x"}], 5.0))
        checks.append(("非 RecommendationDraft 请求不带 format", "format" not in provider._http.payloads[0]))
    finally:
        os.environ.pop("OLLAMA_FORMAT_OVERRIDES", None)

    ok = True
    for name, passed in checks:
        print(("PASS " if passed else "FAIL ") + name)
        ok = ok and passed
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
