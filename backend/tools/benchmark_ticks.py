"""Offline tick timings and deterministic public-output digests, with real SQLite.

These timings are not a 5Hz network test or a 20-minute wall-clock soak. Uses a
new output directory/database and never the operator's demonstration database.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import platform
import statistics
import time
from pathlib import Path

from PIL import Image

from backend.app import checkpoint, config
from backend.app.engine import GameEngine
from backend.app.storage import HistoryStore


def summary(values):
    ordered = sorted(values)
    if not ordered:
        return {"n": 0}
    return {"n": len(values), "mean_ms": round(statistics.mean(values), 4),
            "p95_ms": round(ordered[min(len(ordered)-1, int(.95*len(ordered)))], 4),
            "max_ms": round(max(values), 4), "over_20ms": sum(v > 20 for v in values)}


def timed_call(method, sink):
    def wrapped(*args, **kwargs):
        begin = time.perf_counter()
        try:
            return method(*args, **kwargs)
        finally:
            sink.append((time.perf_counter()-begin)*1000)
    return wrapped


def run(directory: Path, scenarios, speed, until=None):
    directory.mkdir(parents=True, exist_ok=True)
    if (directory / "report.json").exists() or any(directory.glob("*.sqlite3")):
        raise RuntimeError("Use a new output directory; existing results are preserved")
    report = {"scope": "offline engine, real disk SQLite; no frontend/C Agent/network rate claim",
              "python": platform.python_version(), "platform": platform.platform(), "speed": speed, "scenarios": {}}
    logging.getLogger("backend.app.engine").setLevel(logging.ERROR)
    for scenario in scenarios:
        store = HistoryStore(directory / f"{scenario}.sqlite3")
        game = GameEngine(debug_truth=False, store=store)
        samples = {key: [] for key in ("outer_tick", "compute", "publish_state", "capture", "sqlite_commit", "sequence_commit", "classify_png")}
        original_capture = checkpoint.capture

        messages = []
        game.bus.listeners.append(messages.append)
        digest = hashlib.sha256()
        pngs, models = {}, set()
        begin = time.perf_counter()
        checkpoint.capture = timed_call(original_capture, samples["capture"])
        store.commit = timed_call(store.commit, samples["sqlite_commit"])
        if hasattr(store, "commit_sequence"):
            store.commit_sequence = timed_call(store.commit_sequence, samples["sequence_commit"])
        try:
            game.start(scenario, speed)
            classifier = game.decision.pinger.classifier
            classifier.classify = timed_call(classifier.classify, samples["classify_png"])
            tick = 0
            duration = min(game.world.duration_s, until) if until is not None else game.world.duration_s
            while game.world.t < duration - 1e-8:
                started = time.perf_counter()
                game.step(min(speed/config.TICK_HZ, duration-game.world.t))
                samples["outer_tick"].append((time.perf_counter()-started)*1000)
                samples["compute"].append(game.compute_ms)
                if tick % (config.TICK_HZ // config.STATE_HZ) == 0:
                    started = time.perf_counter()
                    game.publish_state()
                    samples["publish_state"].append((time.perf_counter()-started)*1000)
                for message in messages:
                    digest.update(json.dumps(message, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode())
                    if message.get("event") == "detection":
                        detection = message["data"]["detection"]
                        image = game.image(detection["id"])
                        pngs[detection["id"]] = hashlib.sha256(image).hexdigest()
                        models.add(detection["model"])
                messages.clear()
                tick += 1
            # Validate archived images as well as raw byte reproducibility.
            from io import BytesIO
            for identifier in pngs:
                with Image.open(BytesIO(game.image(identifier))) as image:
                    assert image.size == (config.SONAR_SIZE, config.SONAR_SIZE)
                    image.load()
            report["scenarios"][scenario] = {"elapsed_s": round(time.perf_counter()-begin, 3), "sim_t": game.world.t,
                "timings": {key: summary(values) for key, values in samples.items()},
                "message_sha256": digest.hexdigest(), "png_sha256": pngs, "models": sorted(models),
                "last_seq": game.bus.seq}
        finally:
            checkpoint.capture = original_capture
            store.close()
        report["scenarios"][scenario]["db_bytes"] = (directory / f"{scenario}.sqlite3").stat().st_size
        print(json.dumps({scenario: report["scenarios"][scenario]}, ensure_ascii=False), flush=True)
    (directory / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--scenario", choices=["a", "b", "all"], default="all")
    parser.add_argument("--speed", type=float, choices=[1, 4, 10], default=10)
    parser.add_argument("--until", type=float)
    args = parser.parse_args()
    if args.until is not None and args.until <= 0:
        parser.error("--until must be positive")
    run(args.directory, ["a", "b"] if args.scenario == "all" else [args.scenario], args.speed, args.until)


if __name__ == "__main__":
    main()
