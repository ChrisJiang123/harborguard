"""Run from repository root: python -m uvicorn backend.app.main:app --port 8000."""
import asyncio
import logging
import os
from contextlib import asynccontextmanager, suppress

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from . import config
from .api import rest, ws
from .engine import GameEngine
from .storage import HistoryStore, StorageError

logger = logging.getLogger(__name__)


def _cors_origins():
    configured = os.getenv("ALLOWED_ORIGINS")
    if configured is None:
        return config.ALLOWED_ORIGINS
    return [origin.strip().rstrip("/") for origin in configured.split(",") if origin.strip()]


def create_app(*, run_loop=True, debug_truth=None, storage_path=None):
    @asynccontextmanager
    async def lifespan(app):
        path = storage_path if storage_path is not None else os.getenv(
            "HARBORGUARD_DB", str(config.ROOT / "backend/runtime/harborguard.sqlite3"))
        store = HistoryStore(path)
        try:
            app.state.engine = GameEngine(debug_truth=debug_truth, store=store)
            warmed = app.state.engine.decision.pinger.classifier.warmup()
            logger.info("Sonar startup warmup model=%s elapsed_ms=%.1f", warmed["model"], warmed["ms"])
            if warmed["model"] == "stub":
                logger.warning("Sonar running in explicit stub mode: %s",
                               app.state.engine.decision.pinger.classifier.last_error)
        except Exception:
            store.close()
            raise
        app.state.runtime_error = None
        app.state.agent_client = httpx.AsyncClient(timeout=config.AGENT_TIMEOUT_S, trust_env=False)

        async def loop():
            tick = 0
            next_tick = asyncio.get_running_loop().time()
            while True:
                try:
                    game = app.state.engine
                    game.step(game.world.speed / config.TICK_HZ)
                    if tick % (config.TICK_HZ // config.STATE_HZ) == 0:
                        game.publish_state()
                except Exception:
                    logger.exception("Simulation failed; paused for inspection")
                    app.state.runtime_error = "simulation failure"
                    app.state.engine.world.paused = True
                    try:
                        app.state.engine.log("critical", "sim", "仿真发生错误，已暂停；请检查后端日志")
                    except StorageError:
                        logger.exception("Cannot persist failure log; backend remains unhealthy")
                tick += 1
                next_tick += 1 / config.TICK_HZ
                now = asyncio.get_running_loop().time()
                if now - next_tick > 1 / config.TICK_HZ:
                    next_tick = now  # Bound catch-up after a slow optional detector call.
                await asyncio.sleep(max(0, next_tick - now))

        task = asyncio.create_task(loop()) if run_loop else None
        try:
            yield
        finally:
            if task:
                task.cancel()
                with suppress(asyncio.CancelledError):
                    await task
            try:
                await app.state.agent_client.aclose()
            finally:
                store.close()

    app = FastAPI(title="HarborGuard Backend", version="1.0.0", lifespan=lifespan)

    @app.exception_handler(StorageError)
    async def storage_error(request, exc):
        logger.error("Durable history failure: %s", exc, exc_info=exc)
        request.app.state.engine.persistence_error = str(exc)
        return JSONResponse(status_code=503, content={"detail": "Durable history unavailable; operation not confirmed. Inspect backend logs."})
    app.state.allowed_origins = tuple(_cors_origins())
    app.add_middleware(CORSMiddleware, allow_origins=app.state.allowed_origins,
                       allow_methods=["GET","POST","OPTIONS"], allow_headers=["*"])
    app.include_router(rest.router)
    app.include_router(ws.router)
    return app


app = create_app()
