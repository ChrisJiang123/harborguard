"""Isolated real HTTP/WS + fixed C candidate smoke, not browser acceptance.

Uses new ports/DB; stops only its own processes. Never touches the active demo.
"""
import argparse
import asyncio
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx
import numpy as np
import psutil
import websockets

from backend.app import config


async def run(directory):
    directory = directory.resolve()
    directory.mkdir(parents=True, exist_ok=False)
    for port in (8004, 8006):
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", port))
    env = os.environ.copy()
    for key in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "OPENROUTER_API_KEY", "OPENAI_API_KEY"):
        env.pop(key, None)
    env.update(HARBORGUARD_DB=str(directory/"history.sqlite3"), DEBUG_TRUTH_TRACKS="0",
               BACKEND_BASE_URL="http://127.0.0.1:8004", BACKEND_WS_URL="ws://127.0.0.1:8004/ws",
               AGENT_HOST="127.0.0.1", AGENT_PORT="8006", CLOUD_PROVIDER="disabled",
               OLLAMA_BASE_URL="http://127.0.0.1:9/v1", OLLAMA_TIMEOUT_S="0.2",
               AGENT_FAILURE_LOG=str(directory/"agent-failures.jsonl"),
               YOLO_CONFIG_DIR=str(directory/"yolo-config"))
    # QA-only alternate internal Agent destination. Production config is untouched.
    (directory/"candidate_app.py").write_text(
        'from backend.app import config\nconfig.AGENT_URL="http://127.0.0.1:8006/ask"\n'
        'from backend.app.main import app\n', encoding="utf-8")
    env["PYTHONPATH"] = str(config.ROOT)
    processes, handles, messages, arrivals, sizes, resources, segments = [], [], [], [], [], [], []
    result = {"kind": "HTTP/WS integration, not browser/field acceptance", "directory": str(directory)}

    def start(name, args):
        handle = (directory/f"{name}.log").open("ab")
        handles.append(handle)
        process = subprocess.Popen([sys.executable, *args], cwd=config.ROOT, env=env,
                                   stdout=handle, stderr=subprocess.STDOUT,
                                   creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        processes.append(process)
        return process

    def stop(process):
        if process.poll() is not None:
            return
        parent = psutil.Process(process.pid)
        children = parent.children(recursive=True)
        for child in children:
            child.terminate()
        psutil.wait_procs(children, timeout=15)
        if process.poll() is None:
            process.terminate()
        process.wait(timeout=15)

    b_args = ["-m", "uvicorn", "candidate_app:app", "--app-dir", str(directory),
              "--host", "127.0.0.1", "--port", "8004"]
    backend = start("backend", b_args)
    startup_begin = time.perf_counter()
    start("agent", ["-m", "agent.main"])
    async with httpx.AsyncClient(base_url="http://127.0.0.1:8004", trust_env=False, timeout=20) as client:
        async def ready():
            begin = time.perf_counter()
            while time.perf_counter()-begin < 45:
                try:
                    if (await client.get("/api/health")).status_code == 200:
                        return time.perf_counter()-begin
                except httpx.TransportError:
                    pass
                await asyncio.sleep(.1)
            raise RuntimeError("Candidate did not become healthy")

        async def request(method, path, body=None):
            response = await client.request(method, path, json=body)
            response.raise_for_status()
            return response.json()

        async def monitor():
            segment = []
            segments.append(segment)
            async with websockets.connect("ws://127.0.0.1:8004/ws") as ws:
                async for raw in ws:
                    msg = json.loads(raw)
                    messages.append(msg)
                    if msg["type"] == "state":
                        arrivals.append(time.perf_counter())
                        segment.append(arrivals[-1])
                        sizes.append(len(raw.encode()))
                        procs = [psutil.Process(backend.pid), *psutil.Process(backend.pid).children(recursive=True)]
                        resources.append({"rss": sum(p.memory_info().rss for p in procs),
                                          "cpu_s": sum(sum(p.cpu_times()[:2]) for p in procs), "at": arrivals[-1]})

        task = None
        try:
            await ready()
            result["cold_start_to_health_s"] = time.perf_counter()-startup_begin
            task = asyncio.create_task(monitor())
            await asyncio.sleep(.4)
            start_index = len(messages)
            await request("POST", "/api/scenario/b/start", {"speed": 10})
            begin = time.perf_counter()
            while (await request("GET", "/api/state"))["t"] < 70:
                if time.perf_counter()-begin > 30:
                    raise TimeoutError("B did not reach t=70")
                await asyncio.sleep(.2)
            await request("POST", "/api/control", {"action": "pause"})
            b_events = [m for m in messages[start_index:] if m.get("event") == "detection"]
            assert b_events and all(m["data"]["detection"]["model"] == "yolo26n" for m in b_events)
            result["b"] = {"state": await request("GET", "/api/state"), "detections": b_events}
            png = await client.get(b_events[0]["data"]["detection"]["image_url"])
            assert png.status_code == 200 and png.content.startswith(b"\x89PNG")
            start_index = len(messages)
            await request("POST", "/api/scenario/a/start", {"speed": 10})
            begin = time.perf_counter()
            ready_event = None
            while time.perf_counter()-begin < 90:
                ready_event = next((m for m in messages[start_index:] if m.get("event") == "options_ready"), None)
                recs = [m for m in messages[start_index:] if m.get("event") == "recommendation"
                        and m["data"]["recommendation"]["kind"] == "security"]
                if ready_event and recs:
                    break
                await asyncio.sleep(.1)
            assert ready_event and recs, "Real C candidate did not publish a security recommendation"
            await request("POST", "/api/control", {"action": "pause"})
            payload = ready_event["data"]
            aid = payload["alert_id"]
            # Fetch current options to avoid approving a stale optimization event.
            option = (await request("GET", f"/api/options/{aid}"))["options"][0]["id"]
            bodies = []
            for action in ("reject", "approve"):
                body = dict(alert_id=aid, option_id=option, action=action, operator="B candidate QA")
                assert await request("POST", "/api/decision", body) == {"ok": True}
                bodies.append(body)
            result["a"] = {"options_t": ready_event["t"], "recs": recs, "decisions": bodies,
                           "state": await request("GET", "/api/state")}
            # A real transport disconnection; this is API compensation, not UI recovery.
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
            cursor = messages[-1]["seq"]
            await request("POST", "/api/log", dict(level="info", source="operator", text="offline compensation"))
            compensated = await request("GET", f"/api/events?since_seq={cursor}")
            assert compensated and all(m["seq"] > cursor for m in compensated)
            task = asyncio.create_task(monitor())
            await asyncio.sleep(.4)
            events = await request("GET", "/api/events")
            assert [m["data"] for m in events if m.get("event") == "decision"][-2:] == bodies
            state = await request("GET", "/api/state")
            result["transport_compensation"] = compensated
            result["state_before_restart"] = state
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
            task = None
            await asyncio.to_thread(stop, backend)
            backend = start("backend-restart", b_args)
            result["restart_to_health_s"] = await ready()
            after = await request("GET", "/api/state")
            assert after["t"] == state["t"] and after["paused"]
            assert after["seq"] >= state["seq"] and after["zones"] == state["zones"]
            assert [m["data"] for m in await request("GET", "/api/events") if m.get("event") == "decision"][-2:] == bodies
            result["restart_persistence"] = "PASS"
            result["state_after_restart"] = after
            gaps = np.concatenate([np.diff(segment) for segment in segments if len(segment) > 1])
            cpu = (resources[-1]["cpu_s"]-resources[0]["cpu_s"])/(resources[-1]["at"]-resources[0]["at"])*100
            result["stream"] = {"frames": len(arrivals), "mean_hz": len(gaps)/float(sum(gaps)),
                                "max_gap_ms": float(max(gaps)*1000), "p99_gap_ms": float(np.percentile(gaps, 99)*1000),
                                "max_bytes": max(sizes), "max_rss_mb": max(r["rss"] for r in resources)/1024**2,
                                "cpu_percent_one_core": cpu, "cpu_percent_machine": cpu/(os.cpu_count() or 1)}
            result["runtime_health"] = await request("GET", "/api/health")
            result["result"] = "PASS (HTTP/WS only)"
        except Exception as exc:
            result["result"] = "FAIL"
            result["error"] = repr(exc)
            raise
        finally:
            if task:
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)
            for process in processes:
                await asyncio.to_thread(stop, process)
            for handle in handles:
                handle.close()
            (directory/"results.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
            print(json.dumps({k: v for k, v in result.items() if k not in {
                "a", "b", "state_before_restart", "state_after_restart", "transport_compensation"}}, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    asyncio.run(run(parser.parse_args().out))
