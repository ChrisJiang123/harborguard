"""Offline real-model evidence; never edits frontend assets or the demo database.

python -m backend.tools.model_acceptance --out artifacts/model-before.json
This is numerical/API evidence, not a browser or field sonar acceptance.
"""
import argparse
import hashlib
import json
import logging
import platform
import time
from collections import Counter
from pathlib import Path

import numpy as np

from backend.app import config
from backend.app.engine import GameEngine
from backend.app.models import EventMsg


def run(scenario):
    started = time.perf_counter()
    game = GameEngine(debug_truth=False)
    game.start(scenario, 10)
    classifier = game.decision.pinger.classifier
    if classifier.detector is None:
        raise RuntimeError(f"Real detector required: {classifier.last_error}")
    calls, events, costs = [], [], []
    classify = classifier.classify

    def measured(targets, seed=0):
        begin = time.perf_counter()
        result = classify(targets, seed)
        calls.append({"t": game.world.t, "targets": targets, "seed": seed,
                      "ms": (time.perf_counter()-begin)*1000,
                      "model": result["model"], "detections": result["detections"]})
        if result["model"] != "yolo26n":
            raise RuntimeError(f"Unexpected fallback: {classifier.last_error}")
        return result

    classifier.classify = measured
    game.bus.listeners.append(lambda m: events.append(m) if m["type"] == "event" else None)
    max_bytes = 0
    while not game._ended:
        game.step(1)
        costs.append(game.tick_ms)
        max_bytes = max(max_bytes, len(game.state().model_dump_json().encode()))
    for event in events:
        EventMsg.model_validate(event)
    first_levels = {}
    for msg in events:
        if msg["event"] in ("alert_raised", "alert_changed"):
            first_levels.setdefault(str(msg["data"]["alert"]["level"]), msg["t"])
    debris = []
    for target in game.world.targets:
        if target.cls == "debris":
            zid = game.decision.zones.zone_of(target.x, target.y)
            debris.append({"target": target.id, "zone": zid,
                           "state": game.decision.zone_statuses[zid]["state"] if zid else None})
    semantic = {"events": events, "zones": game.decision.zone_statuses,
                "reopen": game.decision.reopen_plan,
                "pngs": {k: hashlib.sha256(v).hexdigest() for k, v in game.decision.images.items()}}
    return {"scenario": scenario, "simulated_s": game.world.t,
            "wall_s": time.perf_counter()-started, "max_state_bytes": max_bytes,
            "first_levels": first_levels,
            "first_uuv_t": next((e["t"] for e in events if e["event"] == "detection"
                                  and e["data"]["detection"]["cls"] == "uuv"), None),
            "zone_counts": dict(Counter(s["state"] for s in game.decision.zone_statuses.values())),
            "debris_zones": debris, "reopen": game.decision.reopen_plan,
            "calls": calls, "events": events,
            "tick_ms": {"p50": float(np.percentile(costs, 50)), "p95": float(np.percentile(costs, 95)),
                        "p99": float(np.percentile(costs, 99)), "max": max(costs)},
            "semantic_sha256": hashlib.sha256(json.dumps(semantic, sort_keys=True).encode()).hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--scenario", choices=["a", "b", "both"], default="both")
    args = parser.parse_args()
    logging.basicConfig(level=logging.ERROR)
    scenarios = ("b", "a") if args.scenario == "both" else (args.scenario,)
    result = {"platform": platform.platform(), "weights_sha256": hashlib.sha256(
        config.SONAR_WEIGHTS_PATH.read_bytes()).hexdigest(), "runs": []}
    for _ in range(args.repeat):
        for scenario in scenarios:
            row = run(scenario)
            result["runs"].append(row)
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
            print(json.dumps({k: v for k, v in row.items() if k not in {"calls", "events"}}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
