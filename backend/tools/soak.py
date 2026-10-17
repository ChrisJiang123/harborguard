"""Exercise a real Uvicorn process, REST controls and WebSocket for a bounded duration."""
import argparse
import asyncio
import json
import os
import subprocess
import sys
import time
from contextlib import suppress
from pathlib import Path

import httpx
import psutil
import websockets

from backend.app import config
from backend.app.models import EventMsg, StateMsg


async def exercise(seconds, port, report_path):
    report_path.parent.mkdir(parents=True, exist_ok=True)
    server_log = report_path.with_suffix(".server.log")
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    # Refuse occupied ports so the check cannot accidentally exercise an unrelated server.
    for connection in psutil.net_connections("tcp"):
        if connection.status == "LISTEN" and connection.laddr.port == port:
            raise RuntimeError(f"Port {port} is already in use")
    with server_log.open("w", encoding="utf-8") as log:
        process = subprocess.Popen(
            [sys.executable,"-m","uvicorn","backend.app.main:app","--host","127.0.0.1","--port",str(port)],
            cwd=config.ROOT, stdout=log, stderr=subprocess.STDOUT, creationflags=flags,
        )
        launcher = psutil.Process(process.pid)
        report = {"seconds_requested":seconds,"port":port,"states":0,"events":0,"max_state_bytes":0,
                  "rss_mb":[],"cpu_core_pct":[],"scenario_cycles":0,"errors":[],"status":"running"}
        try:
            async with httpx.AsyncClient(base_url=f"http://127.0.0.1:{port}",trust_env=False) as client:
                for _ in range(100):
                    try:
                        if (await client.get("/api/health")).status_code == 200:
                            break
                    except httpx.HTTPError:
                        pass
                    if process.poll() is not None:
                        raise RuntimeError(f"Uvicorn exited: {process.returncode}; inspect {server_log}")
                    await asyncio.sleep(.1)
                else:
                    raise RuntimeError("Uvicorn did not become healthy")
                # Windows virtualenv launchers may spawn a second python.exe.
                monitors = [launcher, *launcher.children(recursive=True)]
                report["server_pids"] = [p.pid for p in monitors]
                for monitored in monitors:
                    monitored.cpu_percent()
                for path in ("/api/state","/api/zones","/api/assets","/api/buoys","/api/metrics"):
                    (await client.get(path)).raise_for_status()
                await client.post("/api/scenario/a/start",json={"speed":10})
                report["scenario_cycles"] += 1
                begin = last_sample = time.monotonic()
                last_seq = -1
                scenario = "a"
                injected = False
                async with websockets.connect(f"ws://127.0.0.1:{port}/ws", max_size=200_000) as ws:
                    while time.monotonic()-begin < seconds:
                        raw = await asyncio.wait_for(ws.recv(),timeout=5)
                        msg = json.loads(raw)
                        if msg["seq"] <= last_seq:
                            raise AssertionError("Nonmonotonic live WebSocket sequence")
                        last_seq = msg["seq"]
                        if msg["type"] == "state":
                            StateMsg.model_validate(msg)
                            report["states"] += 1
                            report["max_state_bytes"] = max(report["max_state_bytes"],len(raw.encode()))
                            if msg["t"] >= 50 and not injected:
                                for kind,target in (("network_down",None),("network_up",None),
                                                    ("noise_up",None),("noise_down",None),
                                                    ("buoy_down","B10"),("buoy_up","B10")):
                                    response = await client.post("/api/inject",json={"type":kind,"target":target})
                                    response.raise_for_status()
                                injected = True
                            if msg["paused"] and msg["t"] > 0:
                                (await client.post("/api/control",json={"action":"reset"})).raise_for_status()
                                scenario = "b" if scenario == "a" else "a"
                                (await client.post(f"/api/scenario/{scenario}/start",json={"speed":10})).raise_for_status()
                                report["scenario_cycles"] += 1
                                injected = False
                        else:
                            EventMsg.model_validate(msg)
                            report["events"] += 1
                            if msg["event"] == "detection":
                                response = await client.get(msg["data"]["detection"]["image_url"])
                                response.raise_for_status()
                                assert response.content.startswith(b"\x89PNG")
                        now = time.monotonic()
                        if now-last_sample >= 30:
                            (await client.get("/api/health")).raise_for_status()
                            report["rss_mb"].append(round(sum(p.memory_info().rss for p in monitors)/1024**2,2))
                            report["cpu_core_pct"].append(round(sum(p.cpu_percent() for p in monitors),2))
                            report["elapsed_s"] = round(now-begin,2)
                            report_path.write_text(json.dumps(report,indent=2),encoding="utf-8")
                            print(f"soak {report['elapsed_s']}s states={report['states']} cycles={report['scenario_cycles']} "
                                  f"rss={report['rss_mb'][-1]}MB",flush=True)
                            last_sample = now
                report["elapsed_s"] = round(time.monotonic()-begin,2)
                report["state_hz"] = round(report["states"]/report["elapsed_s"],3)
                report["status"] = "passed"
                assert 4.3 <= report["state_hz"] <= 5.5, report["state_hz"]
                assert report["max_state_bytes"] < config.MAX_STATE_BYTES
        except BaseException as exc:
            report["status"] = "failed"
            report["errors"].append(repr(exc))
            raise
        finally:
            with suppress(psutil.Error):
                for child in reversed(launcher.children(recursive=True)):
                    with suppress(psutil.Error):
                        child.terminate()
            if process.poll() is None:
                process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
            report_path.write_text(json.dumps(report,indent=2),encoding="utf-8")
    print(json.dumps(report),flush=True)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seconds",type=float,default=1200)
    parser.add_argument("--port",type=int,default=8000)
    parser.add_argument("--report",type=Path,default=config.ROOT/"artifacts"/"soak.json")
    args = parser.parse_args()
    if args.seconds <= 0:
        parser.error("seconds must be positive")
    asyncio.run(exercise(args.seconds,args.port,args.report))


if __name__ == "__main__":
    main()
