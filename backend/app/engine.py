"""Deterministic application state; independent of HTTP and the wall clock."""
import copy
import json
import logging
import math
import os
import time
from collections import deque
from functools import wraps

from . import checkpoint, config
from .bus import EventBus
from .decision import DecisionEngine
from .geo import to_geo
from .models import EventMsg, Recommendation, StateMsg
from .perception.localize import localize
from .perception.tracker import Tracker
from .sim.acoustics import Acoustics
from .sim.world import World
from .storage import StorageError

logger = logging.getLogger(__name__)


def durable(method):
    """Commit a complete mutation before its first public broadcast/HTTP success."""
    @wraps(method)
    def wrapped(self, *args, **kwargs):
        if self.store is None or self.bus.pending is not None:
            return method(self, *args, **kwargs)
        previous = checkpoint.capture(self)
        images = dict(self.decision.images)  # PNG bytes are immutable; do not copy/encode them.
        sequence = self.bus.seq
        self.bus.begin()
        try:
            result = method(self, *args, **kwargs)
            self.store.commit(seq=self.bus.seq, fingerprint=self._fingerprint,
                checkpoint=checkpoint.encode(checkpoint.capture(self, copy_values=False)), messages=self.bus.pending,
                objects=self._history_objects(), images=self.decision.images)
        except Exception as exc:
            checkpoint.restore(self, previous, images)
            self.bus.seq = sequence
            self.bus.pending = None
            if isinstance(exc, StorageError):
                self.persistence_error = str(exc)
            raise
        self.persistence_error = None
        self.bus.commit()
        return result
    return wrapped


class GameEngine:
    def __init__(self, *, debug_truth: bool | None = None, store=None):
        self.store = store
        self.persistence_error = None
        self.bus = EventBus()
        self.world = World()
        self.zones = json.loads((config.DATA_DIR / "zones.geojson").read_text(encoding="utf-8"))
        self.assets = json.loads((config.DATA_DIR / "assets.json").read_text(encoding="utf-8"))
        self.vessels = json.loads((config.DATA_DIR / "vessels.json").read_text(encoding="utf-8"))
        self.decision = DecisionEngine(self.zones, self.assets, self.vessels)
        self.tracker = Tracker()
        self.acoustics = Acoustics()
        self.logs: deque[dict] = deque(maxlen=config.LOG_CACHE_SIZE)
        self.recommendations: dict[str, dict] = {}
        self._tracks: list[dict] = []
        self._scan_elapsed = 0.0
        self._ended = False
        self._truth_history: dict[str, list] = {}
        self.debug_truth = (os.getenv("DEBUG_TRUTH_TRACKS") == "1") if debug_truth is None else debug_truth
        self.tick_ms = 0.0
        if store is not None:
            self._fingerprint = checkpoint.fingerprint()
            saved = store.load(self._fingerprint)
            if saved:
                try:
                    seq, encoded, events = saved
                    snapshot = checkpoint.decode(encoded)
                    if snapshot["engine"]["debug_truth"] != self.debug_truth:
                        raise StorageError("Checkpoint DEBUG_TRUTH_TRACKS differs from configured mode")
                    images = {did: store.get_image(did) for did in snapshot["pinger"]["detections"]}
                    if any(image is None for image in images.values()):
                        raise StorageError("Checkpoint references missing sonar images")
                    checkpoint.restore(self, snapshot, images)
                    self.bus.seq = seq
                    self.bus.events.extend(EventMsg.model_validate(e).model_dump(mode="json") for e in events)
                    if any(e["seq"] > seq for e in events):
                        raise StorageError("History sequence exceeds checkpoint")
                    # Downtime never advances simulated time. An operator explicitly resumes.
                    self.world.paused = True
                    self.state()
                except (KeyError, TypeError, ValueError) as exc:
                    raise StorageError("Invalid runtime checkpoint; preserve DB for inspection") from exc
            self.save()

    def _history_objects(self):
        objects = []
        for kind, entries in (("alert", self.decision.alerts), ("options", self.decision.options),
                              ("detection", self.decision.detections)):
            objects.extend((kind, key, value) for key, value in entries.items())
        objects.extend(("track", track["id"], track) for track in self._tracks)
        for message in self.bus.pending or []:
            data = message.get("data", {})
            if message.get("event") == "recommendation":
                rec = data["recommendation"]
                objects.append(("recommendation", rec["id"], rec))
            elif message.get("event") == "decision":
                objects.append(("decision", str(message["seq"]), data))
                objects.append(("latest_decision", data["alert_id"], data))
        return objects

    @durable
    def save(self):
        """Explicit checkpoint (also useful for deterministic offline validation)."""

    def detail(self, kind, identifier):
        current = {"alert": self.decision.alerts, "options": self.decision.options,
                   "detection": self.decision.detections, "track": {t["id"]: t for t in self._tracks}}
        result = current[kind].get(identifier)
        if result is None and self.store is not None:
            result = self.store.get_object(kind, identifier)
        return result

    def image(self, identifier):
        result = self.decision.images.get(identifier)
        if result is None and self.store is not None:
            result = self.store.get_image(identifier)
        return result

    @durable
    def emit(self, name, data):
        message = self.bus.publish_event(name, data, round(self.world.t, 6))
        if name == "log":
            self.logs.appendleft(message["data"]["log"])
        return message

    def emit_all(self, events):
        for name, data in events or []:
            self.emit(name, data)

    def log(self, level, source, text):
        self.emit("log", {"log": dict(t=self.world.t, level=level, source=source, text=text)})

    @durable
    def start(self, scenario_id, speed=None):
        self.world.start(scenario_id, speed)
        self.decision.reset(self.world.mode)
        self.tracker = Tracker()
        self.acoustics = Acoustics()
        self.logs.clear()
        self.recommendations.clear()
        self._tracks = []
        self._truth_history.clear()
        self._scan_elapsed = 0.0
        self._ended = False
        self.emit("scenario_changed", {"scenario": scenario_id, "status": "started"})
        self.emit("mode_changed", {"mode": self.world.mode})
        self.log("info", "sim", f"Scenario {scenario_id.upper()} started, speed={self.world.speed:g}")
        if self.debug_truth:
            self.log("warn", "perception", "DEBUG_TRUTH_TRACKS=1: using truth-track demonstration fallback")

    @durable
    def reset(self):
        previous = self.world.scenario_id
        self.world.reset()
        self.decision.reset("security")
        self.tracker = Tracker()
        self.acoustics = Acoustics()
        self.logs.clear()
        self.recommendations.clear()
        self._tracks = []
        self._truth_history.clear()
        self._scan_elapsed = 0.0
        self._ended = False
        self.emit("scenario_changed", {"scenario": previous, "status": "reset"})
        self.emit("mode_changed", {"mode": "security"})

    @durable
    def control(self, action, value=None):
        if action == "reset":
            self.reset()
        elif action == "speed":
            self.world.speed = value
        elif action == "pause":
            self.world.paused = True
        elif action == "resume":
            if not self.world.scenario_id or self._ended:
                raise ValueError("Start a scenario before resuming")
            self.world.paused = False

    @durable
    def decide(self, alert_id, option_id, action, operator):
        self.emit_all(self.decision.approve(alert_id, option_id, action, operator, self.world.t))

    @durable
    def set_mode(self, mode):
        if self.world.mode != mode:
            self.world.mode = mode
            self.emit_all(self.decision.set_mode(mode, self.world.t))

    @durable
    def inject(self, kind, target=None):
        if kind.startswith("buoy_"):
            if target not in self.world.buoys:
                raise ValueError(f"Unknown buoy: {target}")
            buoy = self.world.buoys[target]
            buoy["status"] = "down" if kind == "buoy_down" else "ok"
            buoy["pinging"] = False
            self.emit("buoy_changed", {"buoy_id": target, "status": buoy["status"]})
        elif kind.startswith("network_"):
            self.world.network = "offline" if kind == "network_down" else "online"
            self.emit("network_changed", {"network": self.world.network})
        elif kind.startswith("noise_"):
            self.world.noise_up = kind == "noise_up"
        else:
            raise ValueError(f"Unknown fault: {kind}")
        self.log("warn", "operator", f"Fault injected: {kind}" + (f": {target}" if target else ""))

    def _truth_tracks(self):
        tracks = []
        for index, target in enumerate(self.world.targets):
            tid = f"T{index+1}"
            lat, lon = to_geo(target.x, target.y)
            history = self._truth_history.setdefault(tid, [])
            if not history or self.world.t-history[-1][3] >= config.HISTORY_EVERY_S - 1e-6:
                history.append([lat, lon, target.depth, self.world.t])
            predicted = []
            for offset in range(int(config.PREDICT_EVERY_S), int(config.PREDICT_HORIZON_S) + 1,
                                int(config.PREDICT_EVERY_S)):
                plat, plon = to_geo(target.x + target.vx*offset, target.y + target.vy*offset)
                predicted.append([plat, plon, max(0, min(config.SEABED_DEPTH_M, target.depth+target.vz*offset)),
                                  self.world.t + offset])
            tracks.append(dict(id=tid, status="confirmed", cls=target.cls, conf=1, cue="narrowband"
                               if target.cls == "uuv" else ("call" if target.calling(self.world.t) else "none")
                               if target.cls == "marine_mammal" else "broadband",
                               lat=lat, lon=lon, depth_m=target.depth, vel_e=target.vx, vel_n=target.vy,
                               vel_d=target.vz, speed_mps=math.hypot(target.vx, target.vy),
                               heading_deg=math.degrees(math.atan2(target.vx,target.vy)) % 360,
                               err=dict(a_m=10,b_m=10,angle_deg=0), history=list(history), predicted=predicted,
                               level=0,risk=0,detection_id=None))
        return tracks

    def step(self, dt):
        """Advance simulated seconds using fixed substeps; no sleeps and no wall-clock randomness."""
        if self.world.paused or not self.world.scenario_id or self._ended:
            return
        begin = time.perf_counter()
        self._advance(dt)
        # Include checkpoint preparation and SQLite commit in the actual tick cost.
        self.tick_ms = (time.perf_counter() - begin) * 1000
        if self.tick_ms > config.TICK_WARN_MS:
            logger.warning("Simulation tick including persistence %.1f ms at speed %s", self.tick_ms, self.world.speed)

    @durable
    def _advance(self, dt):
        begin = time.perf_counter()
        remaining = float(dt)
        while remaining > 1e-8 and not self._ended:
            sub = min(1/config.TICK_HZ, remaining, max(0, self.world.duration_s - self.world.t))
            if sub <= 1e-8:
                self._finish()
                break
            self.emit_all(self.world.step(sub))
            if self.debug_truth:
                tracks = self._truth_tracks()
            else:
                self.tracker.predict(sub)
                self._scan_elapsed += sub
                if self._scan_elapsed >= config.SCAN_EVERY_S - 1e-8:
                    self._scan_elapsed -= config.SCAN_EVERY_S
                    observations = self.acoustics.observe(self.world, config.SCAN_EVERY_S)
                    measurements = localize(observations, self.world.buoys)
                    self.tracker.update(measurements, self.world.t, targets=self.world.targets, return_tracks=False)
                tracks = self.tracker.tracks(self.world.t)
            self.emit_all(self.decision.step(tracks, self.world, sub))
            if not self.debug_truth:
                for tr in tracks:
                    if tr["detection_id"]:
                        self.tracker.set_classification(tr["id"],tr["cls"],tr["conf"],tr["detection_id"])
            self._tracks = tracks
            remaining -= sub
            if self.world.t >= self.world.duration_s - 1e-8:
                self._finish()
        self.compute_ms = (time.perf_counter() - begin) * 1000

    def _finish(self):
        self._ended = True
        self.world.paused = True
        self.emit("scenario_changed", {"scenario":self.world.scenario_id, "status":"ended"})

    def state(self):
        # Bound the copy itself, not only the result after copying full histories.
        # Complete history remains available through the existing track detail.
        tracks = [copy.deepcopy({**track, "history": track["history"][-config.HISTORY_MAX:]})
                  for track in self._tracks]
        payload = dict(type="state",seq=self.bus.seq,t=round(self.world.t,6),mode=self.world.mode,
                       network=self.world.network,scenario=self.world.scenario_id,paused=self.world.paused,
                       speed=self.world.speed,buoys=list(self.world.buoys.values()), tracks=tracks,
                       alerts=list(self.decision.alerts.values()), zones=list(self.decision.zone_statuses.values()))
        state = StateMsg.model_validate(payload)
        # Reduce only optional history detail if the snapshot grows; REST retains complete histories.
        while len(state.model_dump_json().encode()) >= config.MAX_STATE_BYTES and any(t.history for t in state.tracks):
            for track in state.tracks:
                track.history = track.history[len(track.history)//2 + 1:]
        return state

    def publish_state(self):
        if self.store is None or self.bus.pending is not None:
            return self.bus.publish_state(self.state())
        # Every world mutation has already committed its checkpoint. Publishing
        # an unchanged snapshot must durably increment seq before broadcasting,
        # but need not copy/serialize/rewrite the entire checkpoint once again.
        previous = self.bus.seq
        self.bus.begin()
        try:
            message = self.bus.publish_state(self.state())
            self.store.commit_sequence(previous=previous, seq=self.bus.seq)
        except Exception as exc:
            self.bus.seq = previous
            self.bus.pending = None
            if isinstance(exc, StorageError):
                self.persistence_error = str(exc)
            raise
        self.persistence_error = None
        self.bus.commit()
        return message

    def get_track(self, track_id):
        return next((track for track in self._tracks if track["id"] == track_id), None)

    def zones_geojson(self):
        zones = copy.deepcopy(self.zones)
        for feature in zones["features"]:
            status = self.decision.zone_statuses[feature["properties"]["id"]]
            feature["properties"].update(state=status["state"],coverage=status["coverage"])
        return zones

    @durable
    def recommend(self, recommendation: Recommendation):
        rec = recommendation.model_dump(mode="json")
        existing = {t["id"] for t in self._tracks} | set(self.decision.alerts) | set(self.decision.detections)
        existing |= set(self.world.buoys) | set(self.decision.zone_statuses) | {a["id"] for a in self.assets}
        existing |= {o["id"] for entry in self.decision.options.values() for o in entry["options"]}
        if rec["alert_id"] is not None and rec["alert_id"] not in self.decision.alerts:
            raise ValueError("alert_id does not reference a current alert")
        if any(evidence not in existing for evidence in rec["evidence_ids"]):
            raise ValueError("evidence_ids must reference existing IDs")
        if rec["recommended_option_id"] is not None:
            choices = self.decision.options.get(rec["alert_id"], {}).get("options", [])
            if rec["recommended_option_id"] not in {o["id"] for o in choices}:
                raise ValueError("recommended_option_id does not belong to this alert")
        self.recommendations[rec["alert_id"] or rec["kind"]] = rec
        self.emit("recommendation", {"recommendation": rec})
