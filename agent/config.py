"""HarborGuard Agent 配置模块（C0）。

所有模型名、API 地址、后端地址均通过环境变量配置：
- 模块导入时**显式加载**仓库根目录的 ``.env``（python-dotenv，override=False，
  即已存在的进程环境变量优先于 .env），不存在 .env 时静默跳过并使用默认值。
- ``.env`` 由 .gitignore 忽略；模板见 ``.env.example``。

用法::

    from agent.config import get_settings
    cfg = get_settings()
    print(cfg.cloud_provider, cfg.backend_base_url, cfg.ollama_model)
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = REPO_ROOT / ".env"

# 显式加载 .env（任务书 C0 硬性要求：运行环境必须明确加载 .env，而不是只建文件不读取）。
# override=False：进程里已有的环境变量（CI、shell export）优先，.env 只补缺。
load_dotenv(dotenv_path=ENV_PATH, override=False)


def _get_str(key: str, default: str) -> str:
    """读字符串；空串/纯空白视为未设置。"""
    value = os.environ.get(key)
    if value is None or value.strip() == "":
        return default
    return value.strip()


def _get_opt(key: str) -> str | None:
    """读可选字符串；未设置或空返回 None。"""
    value = os.environ.get(key)
    if value is None or value.strip() == "":
        return None
    return value.strip()


def _get_int(key: str, default: int) -> int:
    raw = _get_opt(key)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _get_float(key: str, default: float) -> float:
    raw = _get_opt(key)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    """Agent 服务与模型调用的全部可配置项。"""

    # ---- 云端 LLM（显式选择；不会根据凭据自动推断） ----
    cloud_provider: str
    openrouter_api_key: str | None
    openrouter_base_url: str
    openrouter_model: str
    openrouter_timeout_s: float

    # ---- 旧 Anthropic 兼容适配（保留，但仅 CLOUD_PROVIDER=anthropic 时启用） ----
    anthropic_model: str
    anthropic_api_key: str | None      # 平台 API key
    anthropic_auth_token: str | None   # 代理模式 Bearer token（与 api_key 二选一）
    anthropic_base_url: str | None     # 代理地址；None = 官方默认 https://api.anthropic.com
    anthropic_timeout_s: float         # 契约：云端超时 15 秒

    # ---- B 的后端 ----
    backend_base_url: str
    backend_ws_url: str
    backend_timeout_s: float

    # ---- Agent 服务自身 ----
    agent_host: str
    agent_port: int
    agent_event_budget_s: float         # options_ready 到 POST 的整体预算
    agent_post_reserve_s: float         # 为模板组装和 POST 预留
    agent_cloud_budget_s: float         # 云端最多占用的整体预算切片
    agent_ask_budget_s: float           # /ask 总预算（B 代理为 20 秒）
    agent_failure_log: str              # 脱敏事实校验失败样例（不入库）

    # ---- 本地 LLM（Ollama，OpenAI 兼容接口） ----
    ollama_base_url: str
    ollama_model: str
    ollama_timeout_s: float            # 契约：本地超时 30 秒
    ollama_keep_alive: str
    ollama_format_overrides: str       # 显式按模型覆盖输出格式："model:json,…";空 = 全部完整 schema（C3 现状，可回退）
    agent_lang: str = "en"


def load_settings() -> Settings:
    """每次调用重新读取环境变量（便于测试）；常规入口用 get_settings()。"""
    from .language import language

    return Settings(
        agent_lang=language(),
        # 云端 LLM
        cloud_provider=_get_str("CLOUD_PROVIDER", "disabled").lower(),
        openrouter_api_key=_get_opt("OPENROUTER_API_KEY"),
        openrouter_base_url=_get_str("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
        openrouter_model=_get_str("OPENROUTER_MODEL", "google/gemini-2.5-flash"),
        openrouter_timeout_s=_get_float("OPENROUTER_TIMEOUT_S", 15.0),
        anthropic_model=_get_str("ANTHROPIC_MODEL", "claude-sonnet-5"),
        anthropic_api_key=_get_opt("ANTHROPIC_API_KEY"),
        anthropic_auth_token=_get_opt("ANTHROPIC_AUTH_TOKEN"),
        anthropic_base_url=_get_opt("ANTHROPIC_BASE_URL"),
        anthropic_timeout_s=_get_float("ANTHROPIC_TIMEOUT_S", 15.0),
        # B 的后端
        backend_base_url=_get_str("BACKEND_BASE_URL", "http://localhost:8000"),
        backend_ws_url=_get_str("BACKEND_WS_URL", "ws://localhost:8000/ws"),
        backend_timeout_s=_get_float("BACKEND_TIMEOUT_S", 5.0),
        # Agent 服务
        agent_host=_get_str("AGENT_HOST", "127.0.0.1"),
        agent_port=_get_int("AGENT_PORT", 8001),
        agent_event_budget_s=_get_float("AGENT_EVENT_BUDGET_S", 9.5),
        agent_post_reserve_s=_get_float("AGENT_POST_RESERVE_S", 0.5),
        agent_cloud_budget_s=_get_float("AGENT_CLOUD_BUDGET_S", 4.0),
        agent_ask_budget_s=_get_float("AGENT_ASK_BUDGET_S", 18.0),
        agent_failure_log=_get_str("AGENT_FAILURE_LOG", "agent/runtime/fact_failures.jsonl"),
        # 本地 LLM
        ollama_base_url=_get_str("OLLAMA_BASE_URL", "http://localhost:11434/v1"),
        ollama_model=_get_str("OLLAMA_MODEL", "qwen3:1.7b"),
        ollama_timeout_s=_get_float("OLLAMA_TIMEOUT_S", 30.0),
        ollama_keep_alive=_get_str("OLLAMA_KEEP_ALIVE", "30m"),
        ollama_format_overrides=_get_str("OLLAMA_FORMAT_OVERRIDES", ""),
    )


_settings: Settings | None = None


def get_settings() -> Settings:
    """进程级单例（首次调用时读取 .env + 环境变量）。"""
    global _settings
    if _settings is None:
        _settings = load_settings()
    return _settings
