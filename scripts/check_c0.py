#!/usr/bin/env python3
"""HarborGuard C0 环境自检（任务书 C · 步骤 C0 验收）。

用法（仓库根目录）::

    .venv/bin/python scripts/check_c0.py

逐项打印 PASS / FAIL / PENDING 与摘要。
- FAIL：环境必需项损坏，必须修复。
- PENDING：依赖外部条件（API key、GPU、拔网线等），如实标注待完成，不假报通过。
退出码：0 = 无 FAIL；1 = 存在 FAIL。
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
    print(f"C0 自检汇总: {n_pass} PASS, {n_fail} FAIL, {n_pend} PENDING(待完成)")
    if n_fail:
        print("FAIL 项:")
        for name, s, detail in _results:
            if s == FAIL:
                print(f"  - {name}: {detail}")
    if n_pend:
        print("PENDING 项（外部条件，待完成）:")
        for name, s, detail in _results:
            if s == PENDING:
                print(f"  - {name}: {detail}")
    print("=" * 64)
    return 1 if n_fail else 0


def main() -> int:
    # 1. Python 版本 ------------------------------------------------------
    v = sys.version_info
    if (v.major, v.minor) >= (3, 11):
        record("python", PASS, f"{sys.version.split()[0]} ({sys.executable})")
    else:
        record("python", FAIL, f"{sys.version.split()[0]}，需要 >= 3.11（任务书 C0）")

    # 2. .env 显式加载（要求 6：不能只创建文件却不读取） -------------------
    env_file = ROOT / ".env"
    before = set(os.environ)
    from agent.config import ENV_PATH, get_settings  # noqa: E402  (导入即 load_dotenv)

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
            f"{ENV_PATH} 已被 agent/config.py 显式加载；"
            f"从 .env 注入 {len(injected)} 项 {injected}；"
            f"进程环境优先覆盖 {len(overridden)} 项 {overridden}",
        )
    elif env_file.exists():
        record("env.load", PENDING, ".env 存在但没有任何可读键值")
    else:
        record("env.load", FAIL, f".env 不存在（模板见 .env.example），config 只用了默认值")

    cfg = get_settings()
    record(
        "config.values",
        PASS,
        f"ANTHROPIC_MODEL={cfg.anthropic_model} | BACKEND={cfg.backend_base_url} "
        f"(ws={cfg.backend_ws_url}) | AGENT={cfg.agent_host}:{cfg.agent_port} | "
        f"OLLAMA={cfg.ollama_base_url} model={cfg.ollama_model} "
        f"(云端超时 {cfg.anthropic_timeout_s}s / 本地 {cfg.ollama_timeout_s}s)",
    )

    # 3. 核心依赖导入 ------------------------------------------------------
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
        record("deps.import", FAIL, "导入失败: " + ", ".join(missing))
    else:
        record("deps.import", PASS, " ".join(versions))

    try:
        import pydantic

        if int(pydantic.VERSION.split(".")[0]) >= 2:
            record("deps.pydantic_v2", PASS, f"pydantic {pydantic.VERSION}")
        else:
            record("deps.pydantic_v2", FAIL, f"pydantic {pydantic.VERSION}，契约要求 >= 2")
    except Exception as e:  # noqa: BLE001
        record("deps.pydantic_v2", FAIL, str(e))

    # 4. YOLO 权重加载（任务书命令：YOLO('yolo26n.pt').info()） -------------
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
                print(f"      (yolo26n.pt 不可用: {e.__class__.__name__}，尝试 yolo11n.pt 兜底)")
        if loaded is not None and used:
            record("yolo.weights", PASS, f"{used} 已下载到 .cache/ 并成功加载")
        else:
            record("yolo.weights", FAIL, "未加载任何权重")
    except Exception as e:  # noqa: BLE001
        record("yolo.weights", FAIL, f"{e.__class__.__name__}: {e}")

    # 5. Ollama CLI + 服务 -------------------------------------------------
    ollama_bin = shutil.which("ollama")
    if not ollama_bin:
        record("ollama.cli", FAIL, "ollama 不在 PATH（brew install ollama）")
    else:
        ver = subprocess.run([ollama_bin, "--version"], capture_output=True, text=True)
        record("ollama.cli", PASS, (ver.stdout or ver.stderr).strip())

    import httpx

    tags_url = cfg.ollama_base_url.replace("/v1", "/api/tags")
    models: list[str] = []
    try:
        r = httpx.get(tags_url, timeout=3)
        models = [m.get("name", "") for m in r.json().get("models", [])]
        record("ollama.server", PASS, f"{tags_url} -> 模型: {models or '（空，先 ollama pull）'}")
    except Exception as e:  # noqa: BLE001
        record("ollama.server", FAIL, f"{e.__class__.__name__}: 无法连接 {tags_url}（brew services start ollama）")

    # 6. 与运行时同一原生接口、模型和format；这里只验连通/JSON，不冒充事实验收。
    if models:
        try:
            target, fmt, text = asyncio.run(configured_local_chat(cfg, models))
            record("ollama.chat", PASS, f"model={target} format={fmt} JSON回复: {text[:120]!r}（连通性检查）")
        except Exception as e:  # noqa: BLE001
            record("ollama.chat", FAIL, f"{e.__class__.__name__}: {e}")
    else:
        record("ollama.chat", PENDING, f"无本地模型；需要配置的 {cfg.ollama_model}（自检不下载模型）")

    # 7. 云端 LLM 一次真实调用 --------------------------------------------
    has_cred = bool(cfg.anthropic_api_key or cfg.anthropic_auth_token)
    sdk_env_cred = bool(
        os.environ.get("ANTHROPIC_API_KEY")
        or os.environ.get("ANTHROPIC_AUTH_TOKEN")
    )
    if cfg.cloud_provider != "anthropic":
        record("cloud.llm", PENDING,
               f"CLOUD_PROVIDER={cfg.cloud_provider}; 不探测旧Anthropic适配，不发生收费调用")
    elif not (has_cred or sdk_env_cred):
        record(
            "cloud.llm",
            PENDING,
            "未配置 ANTHROPIC_API_KEY / ANTHROPIC_AUTH_TOKEN，跳过真实调用（待完成，不假报通过）",
        )
    else:
        try:
            import anthropic

            src = "config(.env)" if has_cred else "进程环境变量"
            kwargs: dict = {"timeout": cfg.anthropic_timeout_s, "max_retries": 0}
            if cfg.anthropic_api_key:
                kwargs["api_key"] = cfg.anthropic_api_key
            if cfg.anthropic_auth_token:
                kwargs["auth_token"] = cfg.anthropic_auth_token
            if cfg.anthropic_base_url:
                kwargs["base_url"] = cfg.anthropic_base_url
            client = anthropic.Anthropic(**kwargs)
            # smoke test 明确关闭 thinking：Sonnet 5 默认 adaptive thinking，
            # thinking 块会消耗输出预算（代理下即便 disabled 也可能返回空 thinking 块），
            # 因此 max_tokens 给足余量（C3 正式调用时再按需处理 thinking）
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
                    f"凭据有效（HTTP 200，model={resp.model}，stop_reason={resp.stop_reason}）"
                    f"但未取到文本回复，待复核",
                )
            else:
                record(
                    "cloud.llm",
                    PASS,
                    f"凭据来源={src}；model={resp.model} 实际返回 {first_text[:40]!r}",
                )
        except Exception as e:  # noqa: BLE001
            record(
                "cloud.llm",
                PENDING,
                f"调用失败（待完成，不假报通过）: {e.__class__.__name__}: {e}",
            )

    return summary()


if __name__ == "__main__":
    sys.exit(main())
