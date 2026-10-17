"""Anonymous nearest-neighbor track management and cooperative AIS matching."""
from __future__ import annotations

import math
from collections import Counter, deque
from dataclasses import dataclass, field

import numpy as np

from .. import config
from ..geo import to_geo
from .kalman import Kalman3D


@dataclass
class _Track:
    id: str
    filter: Kalman3D
    created_t: float
    updated_t: float
    hits: deque = field(default_factory=lambda: deque(maxlen=config.PERCEPTION_TENTATIVE_SCANS))
    cues: deque = field(default_factory=lambda: deque(maxlen=config.PERCEPTION_CUE_WINDOW))
    status: str = "tentative"
    cls: str = "unknown"
    conf: float = 0.0
    detection_id: str | None = None
    history: list = field(default_factory=list)


def _value(obj, name, default=None):
    return obj.get(name, default) if isinstance(obj, dict) else getattr(obj, name, default)


class Tracker:
    def __init__(self):
        self._tracks: dict[str, _Track] = {}
        self._next_id = 1
        self._t = 0.0

    def predict(self, dt: float):
        for track in self._tracks.values():
            track.filter.predict(dt)
        self._t += dt

    def update(self, measurements: list[dict], t: float, targets=()):
        self._t = t
        for track_id in list(self._tracks):
            if t - self._tracks[track_id].updated_t >= config.TRACK_DELETE_S:
                del self._tracks[track_id]
        candidates = []
        for track in self._tracks.values():
            track.hits.append(0)
            for i, measurement in enumerate(measurements):
                residual = np.array([measurement["x"], measurement["y"]]) - track.filter.x[:2]
                innovation = track.filter.P[:2, :2] + np.asarray(measurement["covariance"])[:2, :2]
                distance = float(residual @ np.linalg.solve(innovation, residual))
                # Incompatible acoustic cues do not exchange tracks at crossings.
                cue = Counter(track.cues).most_common(1)[0][0] if track.cues else "none"
                compatible = cue == "none" or measurement.get("cue", "none") in (cue, "none")
                if distance <= config.ASSOCIATION_GATE and compatible:
                    # Established tracks receive gated nearest-neighbor matches
                    # first. Otherwise a single noisy birth with a large initial
                    # covariance can repeatedly steal a confirmed track's hits.
                    candidates.append((track.status != "confirmed", distance, track.id, i))
        assigned_tracks, assigned_measurements = set(), set()
        for _, _, track_id, index in sorted(candidates):
            if track_id in assigned_tracks or index in assigned_measurements:
                continue
            track, measurement = self._tracks[track_id], measurements[index]
            track.filter.update([measurement["x"], measurement["y"], measurement["depth"]], measurement["covariance"])
            track.updated_t = t
            track.hits[-1] = 1
            track.cues.append(measurement.get("cue", "none"))
            if sum(track.hits) >= config.PERCEPTION_CONFIRM_HITS:
                track.status = "confirmed"
            assigned_tracks.add(track_id)
            assigned_measurements.add(index)
        for index, measurement in enumerate(measurements):
            if index in assigned_measurements:
                continue
            track_id = f"T{self._next_id}"
            self._next_id += 1
            track = _Track(track_id, Kalman3D([measurement["x"], measurement["y"], measurement["depth"]], measurement["covariance"]), t, t)
            track.hits.append(1)
            track.cues.append(measurement.get("cue", "none"))
            self._tracks[track_id] = track
        vessels = [target for target in targets if _value(target, "cls") == "vessel"]
        for track in self._tracks.values():
            track.filter.x[2] = float(np.clip(track.filter.x[2], 0, config.SEABED_DEPTH_M))
            cue = Counter(track.cues).most_common(1)[0][0] if track.cues else "none"
            # AIS corroborates a surface vessel's broadband track. A ship
            # passing over a narrowband UUV must not overwrite sonar identity.
            if cue == "broadband" and any(math.hypot(track.filter.x[0] - _value(v, "x"), track.filter.x[1] - _value(v, "y")) <= config.AIS_MATCH_M for v in vessels):
                track.cls, track.conf = "vessel", 1.0
            if not track.history or t - track.history[-1][3] >= config.HISTORY_EVERY_S - 1e-8:
                lat, lon = to_geo(track.filter.x[0], track.filter.x[1])
                track.history.append([lat, lon, float(track.filter.x[2]), t])
        return self.tracks(t)

    def tracks(self, t: float | None = None):
        t = self._t if t is None else t
        result = []
        for track in self._tracks.values():
            if t - track.updated_t >= config.TRACK_DELETE_S:
                continue
            state = track.filter.x
            lat, lon = to_geo(state[0], state[1])
            speed = math.hypot(state[3], state[4])
            predicted = []
            for ahead in np.arange(config.PREDICT_EVERY_S, config.PREDICT_HORIZON_S + 1e-9, config.PREDICT_EVERY_S):
                plat, plon = to_geo(state[0] + state[3] * ahead, state[1] + state[4] * ahead)
                predicted.append([plat, plon, float(np.clip(state[2] + state[5] * ahead, 0, config.SEABED_DEPTH_M)), float(t + ahead)])
            result.append({"id": track.id, "status": track.status, "cls": track.cls, "conf": track.conf,
                           "cue": Counter(track.cues).most_common(1)[0][0] if track.cues else "none",
                           "lat": float(lat), "lon": float(lon), "depth_m": float(state[2]),
                           "vel_e": float(state[3]), "vel_n": float(state[4]), "vel_d": float(state[5]),
                           "speed_mps": speed, "heading_deg": math.degrees(math.atan2(state[3], state[4])) % 360,
                           "err": track.filter.error_ellipse(), "history": [p[:] for p in track.history], "predicted": predicted,
                           "level": 0, "risk": 0.0, "detection_id": track.detection_id})
        return result

    def set_classification(self, track_id, cls, conf, detection_id):
        if track_id in self._tracks:
            track = self._tracks[track_id]
            track.cls, track.conf, track.detection_id = cls, float(conf), detection_id
