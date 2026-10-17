"""C3 模型路由：云端兼容接口 → 本地 Ollama → 确定性模板。

每次调用只运行一个受截止时间约束的 await 链，不创建迟到后仍可能提交的生成任务。
SDK 隐式重试关闭；只有模型已经返回、但草案结构或 ID 不合法时才附错误重试一次。
"""

from __future__ import annotations

import asyncio
import copy
import hashlib
import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, Protocol
from urllib.parse import urlsplit, urlunsplit

import httpx
from anthropic import AsyncAnthropic
from openai import AsyncOpenAI

from .config import Settings, get_settings
from .context import context_ids
from .factcheck import FACT_CHECK_SCOPE, check_draft_facts, fact_snapshot
from .prompts import ASK_SYSTEM_PROMPT, SYSTEM_PROMPT
from .schemas import DraftOutputError, RecommendationDraft, normalize_draft, parse_model_draft, validate_draft
from .template import generate_recommendation

Route = Literal["cloud", "local", "template"]


@dataclass(frozen=True)
class RawResponse:
    text: str
    response_model: str | None
    upstream_provider: str | None = None
    usage: dict | None = None
    cost: float | None = None


@dataclass(frozen=True)
class GenerationResult:
    draft: RecommendationDraft
    model: Route
    latency_ms: float
    provider: str
    request_model: str | None
    response_model: str | None
    attempts: int
    upstream_provider: str | None = None
    usage: dict | None = None
    cost: float | None = None


@dataclass(frozen=True)
class AnswerResult:
    answer: str
    model: Route
    latency_ms: float
    provider: str
    request_model: str | None
    response_model: str | None
    upstream_provider: str | None = None
    usage: dict | None = None
    cost: float | None = None


class CompletionProvider(Protocol):
    provider: str
    request_model: str
    enabled: bool

    async def complete(self, system: str, messages: list[dict], timeout_s: float) -> RawResponse: ...

    async def aclose(self) -> None: ...


def _provider_label(base_url: str | None) -> str:
    if not base_url:
        return "anthropic-api"
    host = (urlsplit(base_url).hostname or "unknown").lower()
    if host == "api.z.ai" or host.endswith(".z.ai"):
        return "z.ai-anthropic-compatible"
    return f"anthropic-compatible:{host}"


class AnthropicCloudProvider:
    def __init__(self, settings: Settings):
        self.provider = _provider_label(settings.anthropic_base_url)
        self.request_model = settings.anthropic_model
        self.enabled = bool(settings.anthropic_api_key or settings.anthropic_auth_token)
        self._client = (
            AsyncAnthropic(
                api_key=settings.anthropic_api_key,
                auth_token=settings.anthropic_auth_token,
                base_url=settings.anthropic_base_url,
                timeout=settings.anthropic_timeout_s,
                max_retries=0,
            )
            if self.enabled
            else None
        )

    async def complete(self, system: str, messages: list[dict], timeout_s: float) -> RawResponse:
        if self._client is None:
            raise RuntimeError("cloud credentials are not configured")
        response = await self._client.messages.create(
            model=self.request_model,
            max_tokens=1200,
            system=system,
            messages=messages,
            timeout=timeout_s,
        )
        text = "".join(
            block.text for block in response.content
            if getattr(block, "type", None) == "text" and getattr(block, "text", None)
        )
        return RawResponse(text=text, response_model=str(getattr(response, "model", "")) or None)

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.close()


def _number(value) -> int | float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return value


class OpenRouterProvider:
    """OpenRouter Chat Completions adapter using the async OpenAI SDK.

    Structured recommendation calls always send the exact RecommendationDraft schema.
    OpenRouter must reject endpoints that do not support it; schema constraints are never
    silently removed. SDK retries and OpenRouter provider fallbacks are both disabled so the
    caller's asyncio deadline remains the only retry/time budget authority.
    """

    def __init__(self, settings: Settings):
        self.provider = "openrouter"
        self.request_model = settings.openrouter_model
        self.enabled = bool(settings.openrouter_api_key)
        self._client = (
            AsyncOpenAI(
                api_key=settings.openrouter_api_key,
                base_url=settings.openrouter_base_url,
                timeout=settings.openrouter_timeout_s,
                max_retries=0,
            )
            if self.enabled
            else None
        )

    @staticmethod
    def _response_diagnostics(response) -> tuple[str | None, dict | None, float | None]:
        dumped = response.model_dump() if hasattr(response, "model_dump") else {}
        extra = getattr(response, "model_extra", None) or {}
        upstream = dumped.get("provider") or extra.get("provider")
        raw_usage = dumped.get("usage") or {}
        if hasattr(raw_usage, "model_dump"):
            raw_usage = raw_usage.model_dump()
        usage = {
            key: value
            for key in ("prompt_tokens", "completion_tokens", "total_tokens", "reasoning_tokens")
            if (value := _number(raw_usage.get(key))) is not None
        }
        details = raw_usage.get("completion_tokens_details") or {}
        if "reasoning_tokens" not in usage:
            reasoning = _number(details.get("reasoning_tokens"))
            if reasoning is not None:
                usage["reasoning_tokens"] = reasoning
        cost = _number(raw_usage.get("cost"))
        return (str(upstream) if upstream else None, usage or None, float(cost) if cost is not None else None)

    async def complete(self, system: str, messages: list[dict], timeout_s: float) -> RawResponse:
        if self._client is None:
            raise RuntimeError("OpenRouter credentials are not configured")
        extra_body = {
            "provider": {
                "require_parameters": True,
                "allow_fallbacks": False,
            },
            "usage": {"include": True},
        }
        kwargs = {
            "model": self.request_model,
            "messages": [{"role": "system", "content": system}, *messages],
            "max_tokens": 1200 if system == SYSTEM_PROMPT else 300,
            "temperature": 0.0,
            "timeout": timeout_s,
            "extra_body": extra_body,
        }
        if system == SYSTEM_PROMPT:
            kwargs["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "recommendation_draft",
                    "strict": True,
                    "schema": RecommendationDraft.model_json_schema(),
                },
            }
        response = await self._client.chat.completions.create(**kwargs)
        message = response.choices[0].message if response.choices else None
        text = getattr(message, "content", None) or ""
        upstream, usage, cost = self._response_diagnostics(response)
        return RawResponse(
            text=text,
            response_model=str(getattr(response, "model", "")) or None,
            upstream_provider=upstream,
            usage=usage,
            cost=cost,
        )

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.close()


class DisabledCloudProvider:
    provider = "disabled"
    request_model = "none"
    enabled = False

    async def complete(self, system: str, messages: list[dict], timeout_s: float) -> RawResponse:
        raise RuntimeError("cloud provider is disabled")

    async def aclose(self) -> None:
        return None


def build_cloud_provider(settings: Settings) -> CompletionProvider:
    """Build only the explicitly selected cloud adapter; credentials never select a provider."""
    if settings.cloud_provider == "openrouter":
        return OpenRouterProvider(settings)
    if settings.cloud_provider == "anthropic":
        return AnthropicCloudProvider(settings)
    if settings.cloud_provider == "disabled":
        return DisabledCloudProvider()
    raise ValueError(
        "CLOUD_PROVIDER must be one of: openrouter, anthropic, disabled "
        f"(got {settings.cloud_provider!r})"
    )


# Backwards-compatible name for tests/importers of the preserved legacy adapter.
CloudProvider = AnthropicCloudProvider


class LocalProvider:
    def __init__(self, settings: Settings):
        self.provider = "ollama"
        self.request_model = settings.ollama_model
        self.enabled = True
        self.base_url = settings.ollama_base_url
        self.keep_alive = settings.ollama_keep_alive
        self.timeout_s = settings.ollama_timeout_s
        self._http = httpx.AsyncClient(timeout=settings.ollama_timeout_s)

    async def complete(self, system: str, messages: list[dict], timeout_s: float) -> RawResponse:
        payload = {
            "model": self.request_model,
            "messages": [{"role": "system", "content": system}, *messages],
            "stream": False,
            "think": False,
            "keep_alive": self.keep_alive,
            "options": {
                "temperature": 0.0,
                "seed": 0,
                "num_predict": 450 if system == SYSTEM_PROMPT else 250,
            },
        }
        if system == SYSTEM_PROMPT:
            payload["format"] = RecommendationDraft.model_json_schema()
        response = await self._http.post(
            self._native_url("/api/chat"),
            json=payload,
            timeout=timeout_s,
        )
        response.raise_for_status()
        body = response.json()
        text = (body.get("message") or {}).get("content") or ""
        return RawResponse(text=text, response_model=body.get("model"))

    def _native_url(self, path: str) -> str:
        parsed = urlsplit(self.base_url)
        return urlunsplit((parsed.scheme, parsed.netloc, path, "", ""))

    async def warm(self) -> dict:
        """先卸载再测一次冷加载，随后测热请求，并保持模型驻留。"""
        url = self._native_url("/api/generate")
        timeout = min(max(self.timeout_s, 1.0), 20.0)
        result: dict = {"ok": False, "model": self.request_model, "cold_ms": None, "hot_ms": None}
        async with httpx.AsyncClient(timeout=timeout) as http:
            try:
                await http.post(
                    url,
                    json={"model": self.request_model, "prompt": "", "stream": False, "keep_alive": 0},
                )
            except Exception:  # 卸载失败不妨碍后续探测
                pass
            for label in ("cold_ms", "hot_ms"):
                started = time.perf_counter()
                response = await http.post(
                    url,
                    json={
                        "model": self.request_model,
                        "prompt": "",
                        "stream": False,
                        "keep_alive": self.keep_alive,
                    },
                )
                response.raise_for_status()
                body = response.json()
                result[label] = round((time.perf_counter() - started) * 1000.0, 1)
                result["response_model"] = body.get("model")
        result["ok"] = True
        return result

    async def aclose(self) -> None:
        await self._http.aclose()


def _provider_stats() -> dict:
    return {
        "draft_attempts": 0,
        "draft_raw_outputs": 0,
        "draft_raw_valid": 0,
        "draft_first_structure_valid": 0,
        "draft_first_fact_valid": 0,
        "draft_invalid": 0,
        "draft_fact_valid": 0,
        "draft_fact_invalid": 0,
        "draft_retries": 0,
        "draft_retry_success": 0,
        "success": 0,
        "errors": 0,
        "timeouts": 0,
        "ask_attempts": 0,
        "ask_success": 0,
        "request_model": None,
        "response_model": None,
        "upstream_provider": None,
        "usage_requests": 0,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "reasoning_tokens": 0,
        "total_tokens": 0,
        "reported_cost_usd": None,
        "cost_reports": 0,
        "last_error": None,
    }


def _safe_error(exc: BaseException) -> str:
    text = " ".join(str(exc).split())
    return f"{type(exc).__name__}: {text[:240]}" if text else type(exc).__name__


class Router:
    def __init__(
        self,
        settings: Settings | None = None,
        *,
        cloud: CompletionProvider | None = None,
        local: CompletionProvider | None = None,
    ):
        self.settings = settings or get_settings()
        self.cloud = cloud or build_cloud_provider(self.settings)
        self.local = local or LocalProvider(self.settings)
        self.stats = {
            "providers": {"cloud": _provider_stats(), "local": _provider_stats()},
            "generated_routes": {"cloud": 0, "local": 0, "template": 0},
            "ask_routes": {"cloud": 0, "local": 0, "template": 0},
            "template_fallbacks": 0,
            "cloud_skipped_offline": 0,
            "cloud_skipped_unhealthy": 0,
        }
        self.stats["providers"]["cloud"]["request_model"] = self.cloud.request_model
        self.stats["providers"]["local"]["request_model"] = self.local.request_model
        self.last_route: dict | None = None
        self.warmup: dict = {"ok": False, "status": "not_started"}
        self.cloud_retry_after = 0.0
        self.cloud_circuit_reason: str | None = None

    @property
    def cloud_timeout_s(self) -> float:
        if self.settings.cloud_provider == "openrouter":
            return self.settings.openrouter_timeout_s
        return self.settings.anthropic_timeout_s

    @staticmethod
    def _record_response_diagnostics(stat: dict, response: RawResponse) -> None:
        stat["response_model"] = response.response_model
        stat["upstream_provider"] = response.upstream_provider
        if response.usage:
            stat["usage_requests"] += 1
            for key in ("prompt_tokens", "completion_tokens", "reasoning_tokens", "total_tokens"):
                value = _number(response.usage.get(key))
                if value is not None:
                    stat[key] += value
        if response.cost is not None:
            current_cost = stat["reported_cost_usd"] or 0.0
            stat["reported_cost_usd"] = round(current_cost + response.cost, 10)
            stat["cost_reports"] += 1

    async def startup(self) -> None:
        warm = getattr(self.local, "warm", None)
        if warm is None:
            self.warmup = {"ok": False, "status": "not_supported"}
            return
        try:
            self.warmup = {"status": "complete", **await warm()}
        except Exception as exc:  # noqa: BLE001 - 本地失败不能阻止 Agent 启动
            self.warmup = {"ok": False, "status": "failed", "error": _safe_error(exc)}

    async def aclose(self) -> None:
        await asyncio.gather(self.cloud.aclose(), self.local.aclose(), return_exceptions=True)

    def health(self) -> dict:
        result = copy.deepcopy(self.stats)
        result["providers"]["cloud"]["provider"] = self.cloud.provider
        result["providers"]["cloud"]["configured"] = bool(self.cloud.enabled)
        result["providers"]["local"]["provider"] = self.local.provider
        result["providers"]["local"]["configured"] = bool(self.local.enabled)
        result["warmup"] = copy.deepcopy(self.warmup)
        result["last_route"] = copy.deepcopy(self.last_route)
        result["cloud_circuit"] = {
            "open": time.perf_counter() < self.cloud_retry_after,
            "retry_in_s": round(max(0.0, self.cloud_retry_after - time.perf_counter()), 1),
            "reason": self.cloud_circuit_reason,
        }
        result["fact_check_scope"] = FACT_CHECK_SCOPE
        return result

    @staticmethod
    def _redact_text(value: str, ids: set[str]) -> str:
        for identifier in sorted(ids, key=len, reverse=True):
            alias = hashlib.sha256(identifier.encode("utf-8")).hexdigest()[:8]
            value = value.replace(identifier, f"<id:{alias}>")
        return value

    @classmethod
    def _redact_value(cls, value, ids: set[str]):
        if isinstance(value, str):
            return cls._redact_text(value, ids)
        if isinstance(value, list):
            return [cls._redact_value(item, ids) for item in value]
        if isinstance(value, dict):
            return {
                cls._redact_text(key, ids) if isinstance(key, str) else key: cls._redact_value(item, ids)
                for key, item in value.items()
            }
        return value

    def _record_fact_failure(
        self,
        route: str,
        provider: CompletionProvider,
        response: RawResponse,
        draft: RecommendationDraft,
        context: dict,
        errors: list[str],
    ) -> None:
        """追加脱敏 JSONL；只含校验事实，不含日志、坐标、凭证或完整原始响应。"""
        configured = self.settings.agent_failure_log.strip()
        if not configured:
            return
        try:
            path = Path(configured)
            ids = context_ids(context)
            sanitized = {
                key: self._redact_text(value, ids) if isinstance(value, str) else value
                for key, value in draft.model_dump().items()
            }
            sanitized["evidence_ids"] = [
                self._redact_text(value, ids) for value in draft.evidence_ids
            ]
            sanitized["uncertainties"] = [
                self._redact_text(value, ids) for value in draft.uncertainties
            ]
            record = {
                "recorded_at": datetime.now(timezone.utc).isoformat(),
                "route": route,
                "provider": provider.provider,
                "request_model": provider.request_model,
                "response_model": response.response_model,
                "errors": [self._redact_text(error, ids) for error in errors],
                "facts": self._redact_value(fact_snapshot(context), ids),
                "draft": sanitized,
            }
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
        except OSError:
            pass  # 评估样例写入失败不得拖垮在线建议链路

    def reset_cloud_circuit(self) -> None:
        self.cloud_retry_after = 0.0
        self.cloud_circuit_reason = None

    def _trip_cloud_circuit(self, seconds: float = 60.0) -> None:
        self.cloud_retry_after = time.perf_counter() + seconds
        self.cloud_circuit_reason = self.stats["providers"]["cloud"].get("last_error")

    @staticmethod
    def _retry_messages(context_json: str, raw: str | None, error: str | None) -> list[dict]:
        messages = [{"role": "user", "content": context_json}]
        if error is not None:
            messages.extend([
                {"role": "assistant", "content": (raw or "")[:2000]},
                {
                    "role": "user",
                    "content": (
                        "上一次输出不合格，请只输出修正后的完整 JSON 对象。"
                        f"校验错误：{error[:800]}"
                    ),
                },
            ])
        return messages

    async def _draft_from_provider(
        self,
        route: Literal["cloud", "local"],
        provider: CompletionProvider,
        context_json: str,
        context: dict,
        known_ids: set[str],
        option_ids: set[str],
        deadline: float,
        timeout_cap: float,
    ) -> tuple[RecommendationDraft, RawResponse, int] | None:
        stat = self.stats["providers"][route]
        error: str | None = None
        raw: str | None = None
        for attempt in range(2):
            remaining = min(timeout_cap, deadline - time.perf_counter())
            if remaining <= 0.05:
                break
            stat["draft_attempts"] += 1
            if attempt:
                stat["draft_retries"] += 1
            try:
                async with asyncio.timeout(remaining):
                    response = await provider.complete(
                        SYSTEM_PROMPT,
                        self._retry_messages(context_json, raw, error),
                        remaining,
                    )
            except asyncio.TimeoutError:
                stat["timeouts"] += 1
                stat["last_error"] = "TimeoutError: provider deadline exceeded"
                return None
            except Exception as exc:  # SDK 重试已关闭；认证等明确错误立即降级
                stat["errors"] += 1
                stat["last_error"] = _safe_error(exc)
                return None

            stat["draft_raw_outputs"] += 1
            self._record_response_diagnostics(stat, response)
            raw = response.text
            try:
                draft = parse_model_draft(raw, known_ids, option_ids)
            except DraftOutputError as exc:
                stat["draft_invalid"] += 1
                error = str(exc)
                stat["last_error"] = error[:240]
                continue
            stat["draft_raw_valid"] += 1
            if attempt == 0:
                stat["draft_first_structure_valid"] += 1
            fact_result = check_draft_facts(draft, context)
            if not fact_result.ok:
                stat["draft_fact_invalid"] += 1
                error = "事实校验失败: " + "; ".join(fact_result.errors)
                stat["last_error"] = error[:240]
                self._record_fact_failure(route, provider, response, draft, context, fact_result.errors)
                continue
            stat["draft_fact_valid"] += 1
            if attempt == 0:
                stat["draft_first_fact_valid"] += 1
            stat["success"] += 1
            if attempt:
                stat["draft_retry_success"] += 1
            stat["last_error"] = None
            return draft, response, attempt + 1
        return None

    def _record_route(
        self,
        model: Route,
        provider: str,
        request_model: str | None,
        response_model: str | None,
        upstream_provider: str | None = None,
        usage: dict | None = None,
        cost: float | None = None,
    ) -> None:
        self.stats["generated_routes"][model] += 1
        self.last_route = {
            "operation": "recommendation",
            "model": model,
            "provider": provider,
            "request_model": request_model,
            "response_model": response_model,
            "upstream_provider": upstream_provider,
            "usage": copy.deepcopy(usage),
            "cost_usd": cost,
        }

    async def generate(self, context: dict, *, deadline: float) -> GenerationResult:
        started = time.perf_counter()
        generation_end = deadline - self.settings.agent_post_reserve_s
        context_json = json.dumps(context, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
        known_ids = context_ids(context)
        option_ids = {o["id"] for o in context.get("options", [])}

        if context.get("network") == "offline":
            self.stats["cloud_skipped_offline"] += 1
        elif time.perf_counter() < self.cloud_retry_after:
            self.stats["cloud_skipped_unhealthy"] += 1
        elif (
            self.cloud.enabled
            and time.perf_counter() >= self.cloud_retry_after
            and time.perf_counter() < generation_end
        ):
            cloud_transport_failures = (
                self.stats["providers"]["cloud"]["errors"]
                + self.stats["providers"]["cloud"]["timeouts"]
            )
            cloud_deadline = min(
                generation_end,
                time.perf_counter() + self.settings.agent_cloud_budget_s,
            )
            value = await self._draft_from_provider(
                "cloud",
                self.cloud,
                context_json,
                context,
                known_ids,
                option_ids,
                cloud_deadline,
                self.cloud_timeout_s,
            )
            if value is not None:
                draft, response, attempts = value
                self._record_route(
                    "cloud", self.cloud.provider, self.cloud.request_model, response.response_model,
                    response.upstream_provider, response.usage, response.cost,
                )
                return GenerationResult(
                    draft=draft,
                    model="cloud",
                    latency_ms=round((time.perf_counter() - started) * 1000.0, 1),
                    provider=self.cloud.provider,
                    request_model=self.cloud.request_model,
                    response_model=response.response_model,
                    attempts=attempts,
                    upstream_provider=response.upstream_provider,
                    usage=response.usage,
                    cost=response.cost,
                )
            current_transport_failures = (
                self.stats["providers"]["cloud"]["errors"]
                + self.stats["providers"]["cloud"]["timeouts"]
            )
            # 结构/事实不合格只降级当前事件；云服务本身仍健康，不能因此阻断后续事件。
            if current_transport_failures > cloud_transport_failures:
                self._trip_cloud_circuit()

        if self.local.enabled and time.perf_counter() < generation_end:
            value = await self._draft_from_provider(
                "local",
                self.local,
                context_json,
                context,
                known_ids,
                option_ids,
                generation_end,
                self.settings.ollama_timeout_s,
            )
            if value is not None:
                draft, response, attempts = value
                self._record_route(
                    "local", self.local.provider, self.local.request_model, response.response_model,
                    response.upstream_provider, response.usage, response.cost,
                )
                return GenerationResult(
                    draft=draft,
                    model="local",
                    latency_ms=round((time.perf_counter() - started) * 1000.0, 1),
                    provider=self.local.provider,
                    request_model=self.local.request_model,
                    response_model=response.response_model,
                    attempts=attempts,
                    upstream_provider=response.upstream_provider,
                    usage=response.usage,
                    cost=response.cost,
                )

        draft = normalize_draft(generate_recommendation(context))
        errors = validate_draft(draft, known_ids, option_ids)
        if errors:
            raise ValueError("模板建议未通过双重校验: " + "; ".join(errors))
        fact_result = check_draft_facts(draft, context)
        if not fact_result.ok:
            raise ValueError("模板建议未通过事实校验: " + "; ".join(fact_result.errors))
        self.stats["template_fallbacks"] += 1
        self._record_route("template", "deterministic-template", None, None)
        return GenerationResult(
            draft=draft,
            model="template",
            latency_ms=round((time.perf_counter() - started) * 1000.0, 1),
            provider="deterministic-template",
            request_model=None,
            response_model=None,
            attempts=0,
        )

    async def _answer_from_provider(
        self,
        route: Literal["cloud", "local"],
        provider: CompletionProvider,
        prompt: str,
        deadline: float,
        timeout_cap: float,
    ) -> tuple[str, RawResponse] | None:
        stat = self.stats["providers"][route]
        remaining = min(timeout_cap, deadline - time.perf_counter())
        if remaining <= 0.05:
            return None
        stat["ask_attempts"] += 1
        try:
            async with asyncio.timeout(remaining):
                response = await provider.complete(
                    ASK_SYSTEM_PROMPT,
                    [{"role": "user", "content": prompt}],
                    remaining,
                )
        except asyncio.TimeoutError:
            stat["timeouts"] += 1
            stat["last_error"] = "TimeoutError: ask provider deadline exceeded"
            return None
        except Exception as exc:
            stat["errors"] += 1
            stat["last_error"] = _safe_error(exc)
            return None
        answer = " ".join(response.text.strip().split())
        if not answer:
            stat["last_error"] = "ask output was blank"
            return None
        stat["ask_success"] += 1
        self._record_response_diagnostics(stat, response)
        return answer[:150], response

    async def answer(
        self,
        question: str,
        facts: dict,
        *,
        deadline: float,
        template_answer: str,
    ) -> AnswerResult:
        started = time.perf_counter()
        end = deadline - 0.5
        prompt = json.dumps(
            {"question": question, "context": facts},
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        network = facts.get("network")

        if network == "offline":
            self.stats["cloud_skipped_offline"] += 1
        elif time.perf_counter() < self.cloud_retry_after:
            self.stats["cloud_skipped_unhealthy"] += 1
        elif self.cloud.enabled and time.perf_counter() >= self.cloud_retry_after:
            cloud_deadline = min(end, time.perf_counter() + min(8.0, self.cloud_timeout_s))
            value = await self._answer_from_provider(
                "cloud", self.cloud, prompt, cloud_deadline, self.cloud_timeout_s
            )
            if value is not None:
                answer, response = value
                self.stats["ask_routes"]["cloud"] += 1
                self.last_route = {
                    "operation": "ask",
                    "model": "cloud",
                    "provider": self.cloud.provider,
                    "request_model": self.cloud.request_model,
                    "response_model": response.response_model,
                    "upstream_provider": response.upstream_provider,
                    "usage": copy.deepcopy(response.usage),
                    "cost_usd": response.cost,
                }
                return AnswerResult(
                    answer, "cloud", round((time.perf_counter() - started) * 1000.0, 1),
                    self.cloud.provider, self.cloud.request_model, response.response_model,
                    response.upstream_provider, response.usage, response.cost,
                )
            self._trip_cloud_circuit()

        value = await self._answer_from_provider(
            "local", self.local, prompt, end, self.settings.ollama_timeout_s
        )
        if value is not None:
            answer, response = value
            self.stats["ask_routes"]["local"] += 1
            self.last_route = {
                "operation": "ask",
                "model": "local",
                "provider": self.local.provider,
                "request_model": self.local.request_model,
                "response_model": response.response_model,
                "upstream_provider": response.upstream_provider,
                "usage": copy.deepcopy(response.usage),
                "cost_usd": response.cost,
            }
            return AnswerResult(
                answer, "local", round((time.perf_counter() - started) * 1000.0, 1),
                self.local.provider, self.local.request_model, response.response_model,
                response.upstream_provider, response.usage, response.cost,
            )

        self.stats["ask_routes"]["template"] += 1
        self.last_route = {
            "operation": "ask",
            "model": "template",
            "provider": "deterministic-template",
            "request_model": None,
            "response_model": None,
        }
        return AnswerResult(
            template_answer,
            "template",
            round((time.perf_counter() - started) * 1000.0, 1),
            "deterministic-template",
            None,
            None,
        )
