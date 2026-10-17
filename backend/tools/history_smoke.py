"""Real Uvicorn + WebSocket + abrupt restart persistence check (no frontend).

Run from repo root. Uses a NEW isolated directory, never the demo database.
All PNG/model results retain their actual model label (stub is not real YOLO).
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import socket
import sqlite3
import subprocess
import sys
import time
from contextlib import closing, suppress
from pathlib import Path

import httpx
import psutil
import websockets

from backend.app import config
from backend.app.models import EventMsg, StateMsg


async def exercise(directory: Path, port: int):
    directory = directory.resolve()
    directory.mkdir(parents=True, exist_ok=True)
    database = directory / "history.sqlite3"
    if database.exists():
        raise RuntimeError("Use a new --directory; existing history is never overwritten")
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", port))
    report = {"scope": "B backend REST/WebSocket only; no frontend or live C Agent", "status": "running",
              "database": str(database), "port": port, "levels": {}, "errors": []}
    process = log = None
    begin = time.perf_counter()

    def write(name, value):
        (directory / name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")

    def stop():
        nonlocal process, log
        if process is not None:
            with suppress(psutil.Error):
                parent = psutil.Process(process.pid)
                children = parent.children(recursive=True)
                for child in reversed(children):
                    with suppress(psutil.Error):
                        child.terminate()
                psutil.wait_procs(children, timeout=5)
            if process.poll() is None:
                process.terminate()
            process.wait(timeout=10)
            process = None
        if log is not None:
            log.close()
            log = None

    async def launch(client, number):
        nonlocal process, log
        env = {**os.environ, "HARBORGUARD_DB": str(database), "DEBUG_TRUTH_TRACKS": "0"}
        log = (directory / f"server-{number}.log").open("w", encoding="utf-8")
        started = time.perf_counter()
        process = subprocess.Popen([sys.executable, "-m", "uvicorn", "backend.app.main:app", "--host", "127.0.0.1", "--port", str(port)],
            cwd=config.ROOT, env=env, stdout=log, stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        for _ in range(150):
            try:
                if (await client.get("/api/health")).status_code == 200:
                    return round(time.perf_counter()-started, 3)
            except httpx.HTTPError:
                pass
            if process.poll() is not None:
                raise RuntimeError("Backend exited; inspect server log")
            await asyncio.sleep(.1)
        raise RuntimeError("Backend startup timeout")

    async def get(client, path):
        response = await client.get(path)
        response.raise_for_status()
        return response.json()

    async def post(client, path, body):
        response = await client.post(path, json=body)
        response.raise_for_status()
        assert response.json() == {"ok": True}

    try:
        async with httpx.AsyncClient(base_url=f"http://127.0.0.1:{port}", trust_env=False, timeout=10) as client:
            report["startup_s"] = [await launch(client, 1)]
            await post(client, "/api/scenario/a/start", {"speed": 10})
            states, observed_events = [], []
            live_begin = time.perf_counter()
            async with websockets.connect(f"ws://127.0.0.1:{port}/ws", max_size=200_000) as ws:
                previous = -1
                while time.perf_counter()-live_begin < 100:
                    raw = await asyncio.wait_for(ws.recv(), 5)
                    msg = json.loads(raw)
                    assert msg["seq"] > previous
                    previous = msg["seq"]
                    elapsed = time.perf_counter()-live_begin
                    if msg["type"] == "state":
                        StateMsg.model_validate(msg)
                        states.append((elapsed, len(raw.encode())))
                    else:
                        EventMsg.model_validate(msg)
                        observed_events.append(msg)
                        if msg["event"] in {"alert_raised", "alert_changed"}:
                            level = str(msg["data"]["alert"]["level"])
                            if level not in report["levels"]:
                                report["levels"][level] = {"sim_t": msg["t"], "wall_s": round(elapsed, 3)}
                                print(f"Security L{level}: t={msg['t']}, wall={elapsed:.2f}s", flush=True)
                        if msg["event"] == "options_ready":
                            choices = msg["data"]
                            break
                else:
                    raise AssertionError("No real L3/options within 100 wall seconds")
            assert set(report["levels"]) == {"1", "2", "3"}
            report["live_state_hz"] = round((len(states)-1)/(states[-1][0]-states[0][0]), 3)
            report["max_state_bytes"] = max(size for _, size in states)
            assert 4.3 <= report["live_state_hz"] <= 5.5
            assert report["max_state_bytes"] < config.MAX_STATE_BYTES
            aid = choices["alert_id"]
            alert = await get(client, f"/api/alerts/{aid}")
            oid = next(o["id"] for o in choices["options"] if not o["is_baseline"])
            state = await get(client, "/api/state")
            recommendation = dict(id=f"rec-history-{aid}", kind="security", alert_id=aid, model="template",
                summary="持久化验收建议样例", explanation="B 接口验证 fixture；未调用 C Agent。请由操作员确认。",
                recommended_option_id=oid, evidence_ids=[aid, alert["track_id"]], uncertainties=["合成数据，非真实识别验收"],
                confidence="medium", created_t=state["t"], latency_ms=0)
            await post(client, "/api/recommendations", recommendation)
            body = dict(alert_id=aid, option_id=oid, action="reject", operator="history-smoke")
            await post(client, "/api/decision", body)
            rejected = await get(client, "/api/events")
            assert next(e for e in reversed(rejected) if e["event"] == "decision")["data"] == body
            assert not any(z["state"] == "restricted" for z in (await get(client, "/api/state"))["zones"])
            await post(client, "/api/decision", {**body, "action": "approve"})
            await post(client, "/api/control", {"action": "pause"})
            before = await get(client, "/api/state")
            assert any(z["state"] == "restricted" for z in before["zones"])
            before_events = await get(client, "/api/events")
            decisions = [e for e in before_events if e["event"] == "decision"]
            assert [e["data"]["action"] for e in decisions] == ["reject", "approve"]
            details = {path: await get(client, path) for path in (f"/api/alerts/{aid}", f"/api/options/{aid}")}
            report["detection_models"] = sorted({e["data"]["detection"]["model"] for e in before_events if e["event"] == "detection"})
            write("recommendation.json", recommendation)
            write("decision-reject.json", body)
            write("decision-approve.json", {**body, "action": "approve"})
            write("events-before-overflow.json", before_events)
            write("state-before-restart.json", before)
            # Terminate the owned server process, not a graceful app shutdown.
            stop()
            with closing(sqlite3.connect(database)) as connection:
                persisted_seq = connection.execute("SELECT seq FROM runtime").fetchone()[0]
            report["startup_s"].append(await launch(client, 2))
            restored = await get(client, "/api/state")
            assert restored["paused"] and restored["t"] == before["t"]
            assert restored["zones"] == before["zones"] and restored["alerts"] == before["alerts"]
            assert restored["seq"] >= persisted_seq
            assert await get(client, "/api/events") == before_events
            for path, payload in details.items():
                assert await get(client, path) == payload
            await post(client, "/api/log", dict(level="info", source="operator", text="post-restart marker"))
            fresh = await get(client, f"/api/events?since_seq={persisted_seq}")
            assert fresh[-1]["seq"] > persisted_seq
            report["restart_before_overflow"] = "PASS: paused state, restrictions, details, recommendations and both decisions retained"
            for i in range(520):
                await post(client, "/api/log", dict(level="info", source="operator", text=f"overflow-{i}"))
            recent = await get(client, "/api/events?since_seq=0")
            assert len(recent) == 500 and recent[0]["data"]["log"]["text"] == "overflow-20"
            assert not any(e["event"] in {"decision", "recommendation"} for e in recent)
            write("events-after-overflow.json", recent)
            stop()
            with closing(sqlite3.connect(database)) as connection:
                report["archive_events"] = connection.execute("SELECT count(*) FROM events").fetchone()[0]
                archived = [json.loads(r[0]) for r in connection.execute("SELECT payload FROM events ORDER BY seq")]
                assert [e for e in archived if e["event"] == "decision"] == decisions
                assert any(e["event"] == "recommendation" and e["data"]["recommendation"] == recommendation for e in archived)
            report["startup_s"].append(await launch(client, 3))
            assert await get(client, "/api/events") == recent
            report["public_events"] = 500
            report["public_old_decision_history"] = "PENDING contract approval: archive exists but v1 cannot query beyond recent 500"
            await post(client, "/api/scenario/b/start", {"speed": 10})
            for _ in range(30):
                recovery = await get(client, "/api/events")
                debris = [e["data"]["detection"] for e in recovery if e["event"] == "detection" and not e["data"]["detection"]["track_id"]]
                if debris:
                    break
                await asyncio.sleep(.2)
            assert len(debris) == 4
            for detection in debris:
                response = await client.get(detection["image_url"])
                response.raise_for_status()
                assert response.content.startswith(b"\x89PNG\r\n\x1a\n")
                write(detection["id"] + ".json", detection)
            report["recovery_debris_png"] = {"count": len(debris), "models": sorted({d["model"] for d in debris}), "status": "PASS backend PNG; not real model acceptance"}
            report["status"] = "passed"
    except BaseException as exc:
        report["status"] = "failed"
        report["errors"].append(repr(exc))
        raise
    finally:
        stop()
        report["elapsed_s"] = round(time.perf_counter()-begin, 3)
        report["database_bytes"] = database.stat().st_size if database.exists() else 0
        write("report.json", report)
        print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--port", type=int, default=8004)
    args = parser.parse_args()
    asyncio.run(exercise(args.directory, args.port))


if __name__ == "__main__":
    main()
