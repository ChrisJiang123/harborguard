"""HarborGuard Agent configuration (C0). Model names and service addresses come from environment
variables. Import explicitly loads the repository .env using python-dotenv with override=False;
existing process values win. Missing .env uses defaults. The file is ignored; .env.example is the
template. Use get_settings() for the process singleton.
"""


from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = REPO_ROOT / ".env"

# Explicit dotenv loading is a C0 runtime requirement.
# override=False preserves existing CI/shell environment; dotenv fills missing values.
load_dotenv(dotenv_path=ENV_PATH, override=False)


def _get_str(key: str, default: str) -> str:
    """Read a string; treat empty or whitespace-only values as unset."""
    value = os.environ.get(key)
    if value is None or value.strip() == "":
        return default
    return value.strip()


def _get_opt(key: str) -> str | None:
    """Read an optional string, returning None when absent or empty."""
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
    """Configurable Agent service and model-call settings."""

    # Cloud LLM: explicitly selected, never inferred from credentials.
    cloud_provider: str
    openrouter_api_key: str | None
    openrouter_base_url: str
    openrouter_model: str
    openrouter_timeout_s: float

    # Legacy Anthropic-compatible adapter, enabled only by explicit provider selection.
    anthropic_model: str
    anthropic_api_key: str | None      # Platform API key.
    anthropic_auth_token: str | None   # Proxy Bearer token, alternative to api_key.
    anthropic_base_url: str | None     # Proxy URL; None uses the official API default.
    anthropic_timeout_s: float         # Contract cloud timeout:15 seconds.

    # B backend.
    backend_base_url: str
    backend_ws_url: str
    backend_timeout_s: float

    # Agent service.
    agent_host: str
    agent_port: int
    agent_event_budget_s: float         # Overall options_ready-to-POST budget.
    agent_post_reserve_s: float         # Reserve for template assembly and POST.
    agent_cloud_budget_s: float         # Maximum cloud share of the overall budget.
    agent_ask_budget_s: float           # Overall /ask budget; B proxy has20 seconds.
    agent_failure_log: str              # Ignored redacted fact-check failure records.

    # Local LLM via Ollama OpenAI-compatible interface.
    ollama_base_url: str
    ollama_model: str
    ollama_timeout_s: float            # Contract local timeout:30 seconds.
    ollama_keep_alive: str
    ollama_format_overrides: str       # Exact per-model output overrides (model:json,...); empty retains complete schemas.
    agent_lang: str = "en"


def load_settings() -> Settings:
    """Reread environment on each call for tests; normal entry points use get_settings()."""
    from .language import language

    return Settings(
        agent_lang=language(),
        # Cloud LLM.
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
        # B backend.
        backend_base_url=_get_str("BACKEND_BASE_URL", "http://localhost:8000"),
        backend_ws_url=_get_str("BACKEND_WS_URL", "ws://localhost:8000/ws"),
        backend_timeout_s=_get_float("BACKEND_TIMEOUT_S", 5.0),
        # Agent service.
        agent_host=_get_str("AGENT_HOST", "127.0.0.1"),
        agent_port=_get_int("AGENT_PORT", 8001),
        agent_event_budget_s=_get_float("AGENT_EVENT_BUDGET_S", 9.5),
        agent_post_reserve_s=_get_float("AGENT_POST_RESERVE_S", 0.5),
        agent_cloud_budget_s=_get_float("AGENT_CLOUD_BUDGET_S", 4.0),
        agent_ask_budget_s=_get_float("AGENT_ASK_BUDGET_S", 18.0),
        agent_failure_log=_get_str("AGENT_FAILURE_LOG", "agent/runtime/fact_failures.jsonl"),
        # Local LLM.
        ollama_base_url=_get_str("OLLAMA_BASE_URL", "http://localhost:11434/v1"),
        ollama_model=_get_str("OLLAMA_MODEL", "qwen3:1.7b"),
        ollama_timeout_s=_get_float("OLLAMA_TIMEOUT_S", 30.0),
        ollama_keep_alive=_get_str("OLLAMA_KEEP_ALIVE", "30m"),
        ollama_format_overrides=_get_str("OLLAMA_FORMAT_OVERRIDES", ""),
    )


_settings: Settings | None = None


def get_settings() -> Settings:
    """Process singleton, loading dotenv/environment on first access."""
    global _settings
    if _settings is None:
        _settings = load_settings()
    return _settings
