"""Reproducible perception/demo acceptance metrics against simulation truth.

Run from the repository root: python -m backend.app.perception.benchmark --seconds 1200
Truth is used only to score output, never supplied to bearing association.
"""
from __future__ import annotations

import argparse
import json
import math
import time
from collections import Counter
from pathlib import Path

import numpy as np

from .. import config
from ..engine import GameEngine
from ..geo import to_local


def benchmark(seconds=1200.0):
    engine = GameEngine(debug_truth=False)
    events = []
    engine.bus.listeners.append(lambda message: events.append(message) if message["type"] == "event" else None)
    engine.start("a", speed=10)
    seconds = min(float(seconds), engine.world.duration_s)
    errors, velocities, tick_ms = [], [], []
    track_ids, arrival_track_ids, classifications = Counter(), Counter(), Counter()
    false_tracks = [set() for _ in range(math.ceil(seconds / 300))]
    matched, samples, vessel_alerts, max_state_bytes = 0, 0, 0, 0
    first_detected_t = None
    reached_asset_t = None
    begin = time.perf_counter()
    steps = round(seconds * config.TICK_HZ)
    for tick in range(steps):
        start = time.perf_counter()
        engine.step(1 / config.TICK_HZ)
        tick_ms.append((time.perf_counter() - start) * 1000)
        if (tick + 1) % config.TICK_HZ:
            continue
        samples += 1
        world = engine.world
        truth = next(target for target in world.targets if target.cls == "uuv")
        if reached_asset_t is None and math.hypot(truth.vx, truth.vy) < 0.01:
            reached_asset_t = world.t
        narrowband = [track for track in engine._tracks if track["cue"] == "narrowband"]
        if narrowband and first_detected_t is None:
            first_detected_t = world.t
        confirmed = [track for track in narrowband if track["status"] == "confirmed"]
        if confirmed:
            nearest = min(confirmed, key=lambda track: math.dist(to_local(track["lat"], track["lon"]), (truth.x, truth.y)))
            error = math.dist(to_local(nearest["lat"], nearest["lon"]), (truth.x, truth.y))
            if error <= 100:
                matched += 1
                errors.append(error)
                track_ids[nearest["id"]] += 1
                if reached_asset_t is None or world.t <= reached_asset_t:
                    arrival_track_ids[nearest["id"]] += 1
                classifications[nearest["cls"]] += 1
                if world.t >= 30:
                    velocities.append(math.hypot(nearest["vel_e"] - truth.vx, nearest["vel_n"] - truth.vy))
        for track in engine._tracks:
            if track["cls"] == "vessel":
                vessel_alerts += int(track["level"] > 0)
                continue
            if track["status"] != "confirmed":
                continue
            position = to_local(track["lat"], track["lon"])
            if min(math.dist(position, (target.x, target.y)) for target in world.targets) > 100:
                false_tracks[min(len(false_tracks) - 1, int((world.t - 1) // 300))].add(track["id"])
        max_state_bytes = max(max_state_bytes, len(engine.state().model_dump_json().encode()))
    first_levels = {}
    for event in events:
        if event["event"] in {"alert_raised", "alert_changed"} and event["data"]["alert"]["track_id"] in track_ids:
            first_levels.setdefault(str(event["data"]["alert"]["level"]), event["t"])
    return {
        "scenario": "a", "seed": 42, "seconds": seconds, "debug_truth": False,
        "first_detected_t": first_detected_t, "reached_asset_t": reached_asset_t,
        "confirmed_track_ids": dict(track_ids), "samples": samples, "matched_samples": matched,
        "dominant_id_fraction_all_samples": max(track_ids.values(), default=0) / max(samples, 1),
        "track_ids_first_detection_to_arrival": dict(arrival_track_ids),
        "first_detection_to_arrival_samples": int((reached_asset_t or seconds) - (first_detected_t or 1) + 1),
        "dominant_id_fraction_first_detection_to_arrival": max(arrival_track_ids.values(), default=0) / max(1, (reached_asset_t or seconds) - (first_detected_t or 1) + 1),
        "position_rmse_m": float(np.sqrt(np.mean(np.square(errors)))) if errors else None,
        "velocity_rmse_after_30s_mps": float(np.sqrt(np.mean(np.square(velocities)))) if velocities else None,
        "classifications": dict(classifications),
        "anonymous_false_confirmed_ids_per_300s": [sorted(ids) for ids in false_tracks],
        "ais_vessel_alert_violations": vessel_alerts, "first_level_t": first_levels,
        "options_ready_t": [event["t"] for event in events if event["event"] == "options_ready"],
        "detections": [{"t": event["t"], "cls": event["data"]["detection"]["cls"],
                        "model": event["data"]["detection"]["model"]} for event in events if event["event"] == "detection"],
        "max_state_bytes": max_state_bytes,
        "tick_p99_ms": float(np.percentile(tick_ms, 99)), "tick_max_ms": max(tick_ms, default=0),
        "elapsed_wall_s": time.perf_counter() - begin,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seconds", type=float, default=1200)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    result = benchmark(args.seconds)
    encoded = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(encoded + "\n", encoding="utf-8")
    print(encoded)


if __name__ == "__main__":
    main()
