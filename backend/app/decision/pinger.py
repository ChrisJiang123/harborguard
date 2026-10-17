"""Active sonar scheduler and bounded detection/image cache."""
from __future__ import annotations

from math import atan2, degrees, hypot

from .. import config
from ..geo import to_local
from .alerts import AlertManager


def value(target, key, default=None):
    return target.get(key, default) if isinstance(target, dict) else getattr(target, key, default)


class Pinger:
    def __init__(self, classifier=None):
        if classifier is None:
            from ..perception.classifier import SonarClassifier
            classifier = SonarClassifier()
        self.classifier = classifier
        self.last_ping: dict[str, float] = {}
        self.counts: dict[str, int] = {}
        self.warning_at: dict[str, float] = {}
        self.pinging_until: dict[str, float] = {}
        self.detections: dict[str, dict] = {}
        self.images: dict[str, bytes] = {}
        self.counter = 0

    def update_timers(self, world):
        for bid, buoy in world.buoys.items():
            buoy["pinging"] = buoy["status"] == "ok" and self.pinging_until.get(bid, -1) > world.t

    def safe(self, buoy: dict, tracks: list[dict]) -> bool:
        bx, by = to_local(buoy["lat"], buoy["lon"])
        for track in tracks:
            if track.get("cls") != "marine_mammal" and track.get("cue") != "call":
                continue
            x, y = to_local(track["lat"], track["lon"])
            if hypot(x-bx, y-by) <= config.MAMMAL_NO_PING_M:
                return False
        return True

    def scene(self, buoy: dict, track: dict, world) -> list[dict]:
        bx, by = to_local(buoy["lat"], buoy["lon"])
        tx, ty = to_local(track["lat"], track["lon"])
        heading = degrees(atan2(tx-bx, ty-by))
        targets = []
        for target in world.targets:
            if value(target, "cls") not in config.SONAR_TARGET_CLASSES:
                continue
            dx, dy = value(target, "x")-bx, value(target, "y")-by
            distance = hypot(dx, dy)
            bearing = (degrees(atan2(dx, dy))-heading+180) % 360-180
            if distance > config.PING_RANGE_M or abs(bearing) > config.SONAR_FOV_DEG/2:
                continue
            targets.append({"cls": value(target, "cls"), "range_m": distance, "bearing_deg": bearing,
                            "length_m": value(target, "length_m", 2.0),
                            "width_m": value(target, "width_m", 0.5),
                            "aspect_deg": degrees(atan2(value(target, "vx", 0), value(target, "vy", 0)))-heading})
        return targets

    def detect(self, track_id: str, buoy: dict, targets: list[dict], world,
               expected_range: float | None = None) -> tuple[dict, list[tuple]]:
        seed = int(world.rng.integers(0, 2**31-1))
        result = self.classifier.classify(targets, seed=seed)
        detections = result.get("detections", [])
        # Aim toward the track. Select the detection closest to its predicted central pixel.
        target_range = expected_range if expected_range is not None else min(
            (p["range_m"] for p in targets), default=0)
        expected_y = config.SONAR_SIZE-1-target_range/config.PING_RANGE_M*(config.SONAR_SIZE-1)
        def rank(item):
            box = item["bbox"]
            return ((box[0]+box[2])/2-config.SONAR_SIZE/2)**2 + ((box[1]+box[3])/2-expected_y)**2
        chosen = min(detections, key=rank) if detections else {"cls": "unknown", "conf": 0.0, "bbox": [0, 0, 0, 0]}
        self.counter += 1
        did = f"det-{self.counter}"
        detection = {"id": did, "track_id": track_id, "buoy_id": buoy["id"], "t": world.t,
                     "cls": chosen["cls"], "conf": float(chosen["conf"]), "bbox": list(chosen["bbox"]),
                     "image_url": f"/api/sonar/{did}.png", "model": result["model"]}
        self.detections[did] = detection
        self.images[did] = result["image"]
        while len(self.detections) > config.DETECTION_CACHE_SIZE:
            oldest = next(iter(self.detections))
            self.detections.pop(oldest)
            self.images.pop(oldest, None)
        self.pinging_until[buoy["id"]] = world.t+config.PING_DURATION_S
        buoy["pinging"] = True
        return detection, [("detection", {"detection": detection.copy()})]

    def step(self, tracks: list[dict], world) -> list[tuple]:
        self.update_timers(world)
        events = []
        live_ids = {tr["id"] for tr in tracks}
        for mapping in (self.last_ping, self.counts, self.warning_at):
            for tid in set(mapping)-live_ids:
                mapping.pop(tid, None)
        for track in tracks:
            tid = track["id"]
            if track.get("level", 0) < 2 or self.counts.get(tid, 0) >= config.PING_MAX:
                continue
            if world.t-self.last_ping.get(tid, -float("inf")) < config.PING_EVERY_S:
                continue
            x, y = to_local(track["lat"], track["lon"])
            available = []
            for buoy in world.buoys.values():
                bx, by = to_local(buoy["lat"], buoy["lon"])
                distance = hypot(x-bx, y-by)
                if buoy["status"] == "ok" and distance <= config.PING_RANGE_M:
                    available.append((distance, buoy["id"], buoy))
            if not available:
                continue
            buoy = min(available, key=lambda item: (item[0], item[1]))[2]
            if not self.safe(buoy, tracks):
                if world.t-self.warning_at.get(tid, -float("inf")) >= config.PING_EVERY_S:
                    events.append(AlertManager.log(world.t, "附近有海洋哺乳动物，禁止主动 ping", "warn"))
                    self.warning_at[tid] = world.t
                continue
            bx, by = to_local(buoy["lat"], buoy["lon"])
            detection, generated = self.detect(tid, buoy, self.scene(buoy, track, world), world,
                                                expected_range=hypot(x-bx, y-by))
            events.extend(generated)
            self.last_ping[tid] = world.t
            self.counts[tid] = self.counts.get(tid, 0)+1
            if detection["conf"] >= config.DETECTION_MIN_CONF:
                track.update(cls=detection["cls"], conf=detection["conf"], detection_id=detection["id"])
        return events
