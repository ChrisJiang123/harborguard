"""C3 模型路由：云端兼容接口 → 本地 Ollama → 确定性模板。

每次调用只运行一个受截止时间约束的 await 链，不创建迟到后仍可能提交的生成任务。
SDK 隐式重试关闭；只有模型已经返回、但草案结构或 ID 不合法时才附错误重试一次。
"""

from __future__ import annotations

import asyncio
import copy
import json
import time
from dataclasses import dataclass
from typing import Literal, Protocol
from urllib.parse import urlsplit, urlunsplit

import httpx
from anthropic import AsyncAnthropic

from .config import Settings, get_settings
from .context import context_ids
from .prompts import ASK_SYSTEM_PROMPT, SYSTEM_PROMPT
from .schemas import DraftOutputError, RecommendationDraft, normalize_draft, parse_model_draft, validate_draft
from .template import generate_security

Route = Literal["cloud", "local", "template"]


@dataclass(frozen=True)
class RawResponse:
    text: str
    response_model: str | None


@dataclass(frozen=True)
class GenerationResult:
    draft: RecommendationDraft
    model: Route
    latency_ms: float
    provider: str
    request_model: str | None
    response_model: str | None
    attempts: int


@dataclass(frozen=True)
class AnswerResult:
    answer: str
    model: Route
    latency_ms: float
    provider: str
    request_model: str | None
    response_model: str | None


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


class CloudProvider:
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
        "draft_invalid": 0,
        "draft_retries": 0,
        "success": 0,
        "errors": 0,
        "timeouts": 0,
        "ask_attempts": 0,
        "ask_success": 0,
        "request_model": None,
        "response_model": None,
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
        self.cloud = cloud or CloudProvider(self.settings)
        self.local = local or LocalProvider(self.settings)
        self.stats = {
            "providers": {"cloud": _provider_stats(), "local": _provider_stats()},
            "generated_routes": {"cloud": 0, "local": 0, "template": 0},
            "ask_routes": {"cloud": 0, "local": 0, "template": 0},
            "cloud_skipped_offline": 0,
            "cloud_skipped_unhealthy": 0,
        }
        self.stats["providers"]["cloud"]["request_model"] = self.cloud.request_model
        self.stats["providers"]["local"]["request_model"] = self.local.request_model
        self.last_route: dict | None = None
        self.warmup: dict = {"ok": False, "status": "not_started"}
        self.cloud_retry_after = 0.0
        self.cloud_circuit_reason: str | None = None

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
        return result

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
            stat["response_model"] = response.response_model
            raw = response.text
            try:
                draft = parse_model_draft(raw, known_ids, option_ids)
            except DraftOutputError as exc:
                stat["draft_invalid"] += 1
                error = str(exc)
                stat["last_error"] = error[:240]
                continue
            stat["draft_raw_valid"] += 1
            stat["success"] += 1
            stat["last_error"] = None
            return draft, response, attempt + 1
        return None

    def _record_route(
        self,
        model: Route,
        provider: str,
        request_model: str | None,
        response_model: str | None,
    ) -> None:
        self.stats["generated_routes"][model] += 1
        self.last_route = {
            "operation": "recommendation",
            "model": model,
            "provider": provider,
            "request_model": request_model,
            "response_model": response_model,
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
            cloud_deadline = min(
                generation_end,
                time.perf_counter() + self.settings.agent_cloud_budget_s,
            )
            value = await self._draft_from_provider(
                "cloud",
                self.cloud,
                context_json,
                known_ids,
                option_ids,
                cloud_deadline,
                self.settings.anthropic_timeout_s,
            )
            if value is not None:
                draft, response, attempts = value
                self._record_route("cloud", self.cloud.provider, self.cloud.request_model, response.response_model)
                return GenerationResult(
                    draft=draft,
                    model="cloud",
                    latency_ms=round((time.perf_counter() - started) * 1000.0, 1),
                    provider=self.cloud.provider,
                    request_model=self.cloud.request_model,
                    response_model=response.response_model,
                    attempts=attempts,
                )
            self._trip_cloud_circuit()

        if self.local.enabled and time.perf_counter() < generation_end:
            value = await self._draft_from_provider(
                "local",
                self.local,
                context_json,
                known_ids,
                option_ids,
                generation_end,
                self.settings.ollama_timeout_s,
            )
            if value is not None:
                draft, response, attempts = value
                self._record_route("local", self.local.provider, self.local.request_model, response.response_model)
                return GenerationResult(
                    draft=draft,
                    model="local",
                    latency_ms=round((time.perf_counter() - started) * 1000.0, 1),
                    provider=self.local.provider,
                    request_model=self.local.request_model,
                    response_model=response.response_model,
                    attempts=attempts,
                )

        draft = normalize_draft(generate_security(context))
        errors = validate_draft(draft, known_ids, option_ids)
        if errors:
            raise ValueError("模板建议未通过双重校验: " + "; ".join(errors))
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
        stat["response_model"] = response.response_model
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
            cloud_deadline = min(end, time.perf_counter() + min(8.0, self.settings.anthropic_timeout_s))
            value = await self._answer_from_provider(
                "cloud", self.cloud, prompt, cloud_deadline, self.settings.anthropic_timeout_s
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
                }
                return AnswerResult(
                    answer, "cloud", round((time.perf_counter() - started) * 1000.0, 1),
                    self.cloud.provider, self.cloud.request_model, response.response_model,
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
            }
            return AnswerResult(
                answer, "local", round((time.perf_counter() - started) * 1000.0, 1),
                self.local.provider, self.local.request_model, response.response_model,
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
