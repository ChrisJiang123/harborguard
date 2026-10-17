"""Deterministic application state; independent of HTTP and the wall clock."""
import copy
import json
import logging
import math
import os
import time
from collections import deque

from . import config
from .bus import EventBus
from .decision import DecisionEngine
from .geo import to_geo
from .models import Recommendation, StateMsg
from .perception.localize import localize
from .perception.tracker import Tracker
from .sim.acoustics import Acoustics
from .sim.world import World

logger = logging.getLogger(__name__)


class GameEngine:
    def __init__(self, *, debug_truth: bool | None = None):
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

    def emit(self, name, data):
        if name == "log":
            self.logs.appendleft(data["log"])
        return self.bus.publish_event(name, data, round(self.world.t, 6))

    def emit_all(self, events):
        for name, data in events or []:
            self.emit(name, data)

    def log(self, level, source, text):
        self.emit("log", {"log": dict(t=self.world.t, level=level, source=source, text=text)})

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
        self.log("info", "sim", f"场景 {scenario_id.upper()} 开始，speed={self.world.speed:g}")
        if self.debug_truth:
            self.log("warn", "perception", "DEBUG_TRUTH_TRACKS=1：当前为真值航迹演示兜底")

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

    def set_mode(self, mode):
        if self.world.mode != mode:
            self.world.mode = mode
            self.emit_all(self.decision.set_mode(mode, self.world.t))

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
        self.log("warn", "operator", f"故障注入 {kind}" + (f"：{target}" if target else ""))

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
                    self.tracker.update(measurements, self.world.t, targets=self.world.targets)
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
        self.tick_ms = (time.perf_counter() - begin) * 1000
        if self.tick_ms > config.TICK_WARN_MS:
            logger.warning("Simulation tick %.1f ms at speed %s", self.tick_ms, self.world.speed)

    def _finish(self):
        self._ended = True
        self.world.paused = True
        self.emit("scenario_changed", {"scenario":self.world.scenario_id, "status":"ended"})

    def state(self):
        tracks = copy.deepcopy(self._tracks)
        for track in tracks:
            track["history"] = track["history"][-config.HISTORY_MAX:]
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
        return self.bus.publish_state(self.state())

    def get_track(self, track_id):
        return next((track for track in self._tracks if track["id"] == track_id), None)

    def zones_geojson(self):
        zones = copy.deepcopy(self.zones)
        for feature in zones["features"]:
            status = self.decision.zone_statuses[feature["properties"]["id"]]
            feature["properties"].update(state=status["state"],coverage=status["coverage"])
        return zones

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
