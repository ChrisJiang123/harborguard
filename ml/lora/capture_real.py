"""Capture C3 contexts from a running B simulation for C4. Subscribe through BackendClient
reconnect/compensation and collect_* using C3 triggers (options_ready, level-2 alert_changed,
reopen_plan, down buoy_changed). Deduplicate and append JSONL; distill --append-train adds new
records only to training, retaining the synthetic test benchmark. Unlike the online worker, offline
capture has no 10-second deadline/latest-only dropping policy: newer triggers replace pending
parameters while completed contexts remain. Real here means runtime simulation, not physical sonar
observations.
"""


from __future__ import annotations

import argparse
import asyncio
import contextlib
import json
from collections import Counter
from pathlib import Path

from agent.backend_client import BackendClient
from agent.context import collect_buoy, collect_disaster, collect_security
from ml.lora.distill import context_key

REPO_ROOT = Path(__file__).resolve().parents[2]


class RealContextCapture:
    """Collect actual runtime context by C3 triggers, flush each event and deduplicate keys."""

    def __init__(self):
        self.by_key: dict[str, dict] = {}
        self.counts: Counter = Counter()
        self.pending_security: dict[str, tuple] = {}  # alert_id -> (options, ranked)

    async def _collect_security(self, client: BackendClient, alert_id: str,
                                options: list | None, ranked: list | None) -> None:
        try:
            context = await collect_security(client, alert_id, options, ranked)
        except Exception as exc:  # noqa: BLE001 - Record and discard reset/expired alerts.
            self.counts[f"dropped:{type(exc).__name__}"] += 1
            return
        self.counts["security"] += 1
        self.by_key[context_key(context)] = context

    async def flush_security(self, client: BackendClient) -> None:
        pending, self.pending_security = self.pending_security, {}
        for alert_id, (options, ranked) in pending.items():
            await self._collect_security(client, alert_id, options, ranked)

    async def handle_event(self, client: BackendClient, msg: dict) -> None:
        event, data = msg.get("event"), msg.get("data") or {}
        self.counts[f"event:{event}"] += 1
        if event == "options_ready" and data.get("alert_id"):
            self.pending_security[data["alert_id"]] = (data.get("options"), data.get("ranked"))
        elif event == "alert_changed":
            alert = data.get("alert") or {}
            if data.get("to_level") == 2 and alert.get("id"):
                self.pending_security[alert["id"]] = (None, None)
        elif event == "reopen_plan":
            try:
                context = await collect_disaster(client, data)
            except Exception as exc:  # noqa: BLE001
                self.counts[f"dropped:{type(exc).__name__}"] += 1
            else:
                self.counts["disaster"] += 1
                self.by_key[context_key(context)] = context
        elif event == "buoy_changed":
            if data.get("status") == "down" and data.get("buoy_id"):
                try:
                    context = await collect_buoy(client, data["buoy_id"])
                except Exception as exc:  # noqa: BLE001
                    self.counts[f"dropped:{type(exc).__name__}"] += 1
                else:
                    self.counts["buoy"] += 1
                    self.by_key[context_key(context)] = context
        elif event == "scenario_changed" and data.get("status") == "reset":
            self.pending_security.clear()  # An alert expired before context collection.
        await self.flush_security(client)

    async def run(self, *, seconds: float, stop: asyncio.Event) -> BackendClient:
        client = BackendClient()

        async def on_event(msg: dict) -> None:
            await self.handle_event(client, msg)

        stream = asyncio.create_task(client.stream_events(on_event, stop=stop))
        try:
            await asyncio.wait_for(stop.wait(), timeout=seconds)
        except asyncio.TimeoutError:
            pass
        finally:
            stop.set()
            with contextlib.suppress(Exception):
                await asyncio.wait_for(stream, timeout=5)
            await self.flush_security(client)
            await client.aclose()
        return client


def write_contexts(contexts: dict[str, dict], out: Path) -> tuple[int, int]:
    """Append contexts not already recorded; return (added, skipped)."""
    existing: set[str] = set()
    if out.exists():
        with out.open(encoding="utf-8") as stream:
            existing = {context_key(json.loads(line)) for line in stream if line.strip()}
    fresh = {key: ctx for key, ctx in contexts.items() if key not in existing}
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("a", encoding="utf-8") as stream:
        for key, ctx in fresh.items():
            stream.write(json.dumps(ctx, ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n")
    return len(fresh), len(contexts) - len(fresh)


async def run_capture(args: argparse.Namespace) -> int:
    capture = RealContextCapture()
    stop = asyncio.Event()
    # Preflight backend availability instead of silently waiting the full duration.
    probe = BackendClient()
    try:
        await probe.get_state()
    except Exception as exc:  # noqa: BLE001
        await probe.aclose()
        print(f"Error: backend unavailable ({type(exc).__name__}: {str(exc)[:160]}).")
        print("Start the backend and a scenario first: make backend && curl -X POST localhost:8000/api/scenario/a/start "
              "-H 'content-type: application/json' -d '{\"speed\": 10}'")
        return 2
    await probe.aclose()
    print(
        f"Subscribe to {args.ws or 'BACKEND_WS_URL'} for {args.seconds} seconds"
        " (C3 triggers: options_ready / level2 / reopen_plan / buoy down)"
    )
    try:
        await capture.run(seconds=args.seconds, stop=stop)
    except Exception as exc:  # noqa: BLE001
        print(f"Error: capture interrupted ({type(exc).__name__}: {str(exc)[:160]})")
        return 2

    total = len(capture.by_key)
    if total == 0:
        print("No contexts captured; check that the scenario emitted alert/disaster/buoy events.")
        print("Received event counts: " + (", ".join(f"{k}={v}" for k, v in sorted(capture.counts.items())) or "none"))
        return 1
    added, skipped = write_contexts(capture.by_key, args.out)
    dropped = {k: v for k, v in capture.counts.items() if k.startswith("dropped:")}
    summary = ", ".join(
        f"{k}={v}" for k, v in sorted(capture.counts.items())
        if k in {"security", "disaster", "buoy"}
    )
    print(f"Captured {total} unique contexts ({summary}); added {added}, skipped existing {skipped} -> {args.out}")
    if dropped:
        print(f"Dropped (e.g. expired alerts): {dropped}")
    print("Next: python -m ml.lora.distill --contexts " + str(args.out) +
          " --append-train   # Distill new records only and append to training")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Capture running B simulation contexts (C4 supplements)")
    parser.add_argument("--seconds", type=float, default=180.0, help="Capture duration in seconds (default180)")
    parser.add_argument("--out", type=Path,
                        default=REPO_ROOT / "ml/lora/datasets/real_contexts.jsonl")
    parser.add_argument("--ws", default=None, help="WebSocket URL (default BACKEND_WS_URL)")
    args = parser.parse_args()
    raise SystemExit(asyncio.run(run_capture(args)))


if __name__ == "__main__":
    main()
