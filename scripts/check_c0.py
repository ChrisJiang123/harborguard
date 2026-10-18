#!/usr/bin/env python3
"""HarborGuard C0 environment self-check. Run .venv/bin/python scripts/check_c0.py from the repository
root. Report PASS/FAIL/PENDING per item and summary. FAIL means a required component is broken.
Missing external API/GPU/physical-network evidence stays PENDING. Exit0 means no FAIL; exit1 means
at least one FAIL.
"""


from __future__ import annotations

import importlib
import asyncio
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PASS, FAIL, PENDING = "PASS", "FAIL", "PENDING"
ICON = {PASS: "[ok]  ", FAIL: "[X]   ", PENDING: "[...] "}
_results: list[tuple[str, str, str]] = []


async def configured_local_chat(cfg, models: list[str]) -> tuple[str, str, str]:
    """Use the runtime adapter/format; never substitute another installed model."""
    from agent.prompts import SYSTEM_PROMPT
    from agent.router import LocalProvider

    def canonical(name):
        return name.removesuffix(":latest")

    if canonical(cfg.ollama_model) not in {canonical(m) for m in models}:
        raise ValueError(f"configured model {cfg.ollama_model!r} is not installed")
    provider = LocalProvider(cfg)
    context = {
        "kind": "security", "network": "offline", "options": [], "ranked": [],
        "alert": {"id": "A0", "level": 2, "risk": .4},
        "track": {"id": "T0", "cls": "unknown", "conf": .8},
        "buoys": {"down": [], "covering_track": ["B1", "B2"]},
    }
    try:
        response = await provider.complete(SYSTEM_PROMPT,
            [{"role": "user", "content": json.dumps(context, sort_keys=True)}], cfg.ollama_timeout_s)
        payload = json.loads(response.text)
        if not isinstance(payload, dict) or not payload:
            raise ValueError("configured model returned an empty/non-object JSON response")
        return cfg.ollama_model, provider.draft_output_format, response.text
    finally:
        await provider.aclose()


def record(name: str, status: str, detail: str = "") -> None:
    _results.append((name, status, detail))
    print(f"{ICON[status]}{name}: {detail}" if detail else f"{ICON[status]}{name}")


def summary() -> int:
    n_pass = sum(1 for _, s, _ in _results if s == PASS)
    n_fail = sum(1 for _, s, _ in _results if s == FAIL)
    n_pend = sum(1 for _, s, _ in _results if s == PENDING)
    print("\n" + "=" * 64)
    print(f"C0 self-check: {n_pass} PASS, {n_fail} FAIL, {n_pend} PENDING")
    if n_fail:
        print("FAIL items:")
        for name, s, detail in _results:
            if s == FAIL:
                print(f"  - {name}: {detail}")
    if n_pend:
        print("PENDING items (external prerequisites):")
        for name, s, detail in _results:
            if s == PENDING:
                print(f"  - {name}: {detail}")
    print("=" * 64)
    return 1 if n_fail else 0


def main() -> int:
    # 1. Python version.
    v = sys.version_info
    if (v.major, v.minor) >= (3, 11):
        record("python", PASS, f"{sys.version.split()[0]} ({sys.executable})")
    else:
        record("python", FAIL, f"{sys.version.split()[0]}; requires >=3.11 (C0)")

    # 2. Explicit dotenv loading, not just creating the file.
    env_file = ROOT / ".env"
    before = set(os.environ)
    from agent.config import ENV_PATH, get_settings  # noqa: E402 - Import explicitly loads dotenv.

    after = set(os.environ)
    injected = sorted(after - before)
    env_keys: list[str] = []
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                env_keys.append(line.split("=", 1)[0].strip())
    overridden = [k for k in env_keys if k not in injected]
    if env_file.exists() and env_keys:
        record(
            "env.load",
            PASS,
            f"{ENV_PATH} explicitly loaded by agent/config.py; "
            f"injected {len(injected)} dotenv values {injected}; "
            f"process environment overrides {len(overridden)} values {overridden}",
        )
    elif env_file.exists():
        record("env.load", PENDING, ".env exists but has no readable key/value pairs")
    else:
        record("env.load", FAIL, f".env is missing (see .env.example); configuration used defaults only")

    cfg = get_settings()
    record(
        "config.values",
        PASS,
        f"ANTHROPIC_MODEL={cfg.anthropic_model} | BACKEND={cfg.backend_base_url} "
        f"(ws={cfg.backend_ws_url}) | AGENT={cfg.agent_host}:{cfg.agent_port} | "
        f"OLLAMA={cfg.ollama_base_url} model={cfg.ollama_model} "
        f"(cloud timeout {cfg.anthropic_timeout_s}s / local {cfg.ollama_timeout_s}s)",
    )

    # 3. Core dependency imports.
    mods = [
        "numpy", "cv2", "yaml", "matplotlib", "fastapi", "uvicorn",
        "httpx", "websockets", "pydantic", "anthropic", "openai",
        "dotenv", "pytest", "ultralytics",
    ]
    missing: list[str] = []
    versions: list[str] = []
    for m in mods:
        try:
            mod = importlib.import_module(m)
            ver = getattr(mod, "__version__", "?")
            versions.append(f"{m}=={ver}")
        except Exception as e:  # noqa: BLE001
            missing.append(f"{m} ({e.__class__.__name__})")
    if missing:
        record("deps.import", FAIL, "Import failed: " + ", ".join(missing))
    else:
        record("deps.import", PASS, " ".join(versions))

    try:
        import pydantic

        if int(pydantic.VERSION.split(".")[0]) >= 2:
            record("deps.pydantic_v2", PASS, f"pydantic {pydantic.VERSION}")
        else:
            record("deps.pydantic_v2", FAIL, f"pydantic {pydantic.VERSION}; contract requires >=2")
    except Exception as e:  # noqa: BLE001
        record("deps.pydantic_v2", FAIL, str(e))

    # 4. YOLO weight loading.
    try:
        from ultralytics import YOLO

        cache = ROOT / ".cache"
        cache.mkdir(exist_ok=True)
        loaded, used = None, None
        for w in ("yolo26n.pt", "yolo11n.pt"):
            try:
                candidate = cache / w
                model = YOLO(str(candidate))
                loaded, used = model, w
                break
            except Exception as e:  # noqa: BLE001
                if w == "yolo11n.pt":
                    raise
                print(f"      (yolo26n.pt unavailable: {e.__class__.__name__}; trying yolo11n.pt fallback)")
        if loaded is not None and used:
            record("yolo.weights", PASS, f"{used} downloaded into .cache/ and loaded")
        else:
            record("yolo.weights", FAIL, "No weights loaded")
    except Exception as e:  # noqa: BLE001
        record("yolo.weights", FAIL, f"{e.__class__.__name__}: {e}")

    # 5. Ollama CLI and service.
    ollama_bin = shutil.which("ollama")
    if not ollama_bin:
        record("ollama.cli", FAIL, "ollama is not on PATH (brew install ollama)")
    else:
        ver = subprocess.run([ollama_bin, "--version"], capture_output=True, text=True)
        record("ollama.cli", PASS, (ver.stdout or ver.stderr).strip())

    import httpx

    tags_url = cfg.ollama_base_url.replace("/v1", "/api/tags")
    models: list[str] = []
    try:
        r = httpx.get(tags_url, timeout=3)
        models = [m.get("name", "") for m in r.json().get("models", [])]
        record("ollama.server", PASS, f"{tags_url} -> Models: {models or 'empty; run ollama pull first'}")
    except Exception as e:  # noqa: BLE001
        record("ollama.server", FAIL, f"{e.__class__.__name__}: cannot connect to {tags_url} (brew services start ollama)")

    # 6. Same native adapter/model/format as runtime; connectivity/JSON only, not facts.
    if models:
        try:
            target, fmt, text = asyncio.run(configured_local_chat(cfg, models))
            record("ollama.chat", PASS, f"model={target} format={fmt} JSON reply: {text[:120]!r} (connectivity check)")
        except Exception as e:  # noqa: BLE001
            record("ollama.chat", FAIL, f"{e.__class__.__name__}: {e}")
    else:
        record("ollama.chat", PENDING, f"Configured local model {cfg.ollama_model} is unavailable (self-check does not download it)")

    # 7. One actual cloud LLM call.
    has_cred = bool(cfg.anthropic_api_key or cfg.anthropic_auth_token)
    sdk_env_cred = bool(
        os.environ.get("ANTHROPIC_API_KEY")
        or os.environ.get("ANTHROPIC_AUTH_TOKEN")
    )
    if cfg.cloud_provider != "anthropic":
        record("cloud.llm", PENDING,
               f"CLOUD_PROVIDER={cfg.cloud_provider}; legacy Anthropic adapter is not probed; no billable call")
    elif not (has_cred or sdk_env_cred):
        record(
            "cloud.llm",
            PENDING,
            "ANTHROPIC_API_KEY / ANTHROPIC_AUTH_TOKEN unset; actual call skipped (PENDING, not PASS)",
        )
    else:
        try:
            import anthropic

            src = "config(.env)" if has_cred else "process environment"
            kwargs: dict = {"timeout": cfg.anthropic_timeout_s, "max_retries": 0}
            if cfg.anthropic_api_key:
                kwargs["api_key"] = cfg.anthropic_api_key
            if cfg.anthropic_auth_token:
                kwargs["auth_token"] = cfg.anthropic_auth_token
            if cfg.anthropic_base_url:
                kwargs["base_url"] = cfg.anthropic_base_url
            client = anthropic.Anthropic(**kwargs)
            # Smoke test explicitly disables thinking; Sonnet5 defaults to adaptive thinking.
            # Reasoning blocks consume output budget, including empty proxy blocks;
            # allow sufficient max_tokens and handle runtime thinking separately.
            resp = client.messages.create(
                model=cfg.anthropic_model,
                max_tokens=1024,
                thinking={"type": "disabled"},
                messages=[{"role": "user", "content": "ping"}],
            )
            first_text = next(
                (b.text for b in resp.content if getattr(b, "type", "") == "text"), ""
            )
            if resp.stop_reason == "max_tokens" or not first_text.strip():
                record(
                    "cloud.llm",
                    PENDING,
                    f"Credentials accepted (HTTP200, model={resp.model}, stop_reason={resp.stop_reason}) "
                    f"but no text response was obtained; review required",
                )
            else:
                record(
                    "cloud.llm",
                    PASS,
                    f"credential_source={src}; model={resp.model} returned {first_text[:40]!r}",
                )
        except Exception as e:  # noqa: BLE001
            record(
                "cloud.llm",
                PENDING,
                f"Call failed (PENDING, not PASS): {e.__class__.__name__}: {e}",
            )

    return summary()


if __name__ == "__main__":
    sys.exit(main())
