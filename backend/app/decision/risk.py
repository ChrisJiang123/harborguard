"""Five explainable risk components from the frozen taskbook formula."""
from __future__ import annotations

from math import cos, hypot, radians

import numpy as np

from .. import config
from ..geo import to_local
from .zones import Zones


class RiskScorer:
    def __init__(self, zones: Zones):
        self.zones = zones
        self.first_seen: dict[str, float] = {}

    def score(self, track: dict, t: float) -> dict:
        history = track.get("history", [])
        if track["id"] not in self.first_seen:
            self.first_seen[track["id"]] = min((p[3] for p in history), default=t)
        x, y = to_local(track["lat"], track["lon"])
        asset, distance = self.zones.nearest_asset(x, y)
        zone_id = self.zones.zone_of(x, y)
        passive = config.PASSIVE_CLASS_SCORE.get(track.get("cue", "none"), 0.2)
        conf = float(np.clip(track.get("conf", 0.0), 0, 1))
        cls = track.get("cls", "unknown")
        classified = bool(track.get("detection_id")) or (cls != "unknown" and conf > 0)
        category = conf*config.DETECTED_CLASS_SCORE.get(cls, passive)+(1-conf)*passive if classified else passive
        behavior = self.behavior(track, t, asset)
        parts = {
            "C": category,
            "P": float(np.clip(1-distance/config.D_MAX_M, 0, 1)),
            "B": behavior,
            "Z": self.zones.properties[zone_id]["sensitivity"] if zone_id else config.OUTSIDE_ZONE_SENSITIVITY,
            "D": min(max(t-self.first_seen[track["id"]], 0)/config.DURATION_NORMALIZE_S, 1),
        }
        return {
            "risk": float(sum(config.W[k]*v for k, v in parts.items())),
            "breakdown": parts, "zone_id": zone_id, "asset_id": asset["id"],
            "distance_m": distance,
            "eta_s": self.zones.eta(x, y, track.get("vel_e", 0), track.get("vel_n", 0), asset),
        }

    def behavior(self, track: dict, t: float, asset: dict) -> float:
        history = track.get("history", [])
        recent = [p for p in history if t-config.BEHAVIOR_WINDOW_S <= p[3] <= t]
        if len(recent) < 2 or recent[-1][3]-recent[0][3] < config.BEHAVIOR_MIN_HISTORY_S:
            return 0.0
        xyz = np.array([[*to_local(p[0], p[1]), p[2]] for p in recent])
        displacement = float(np.linalg.norm(xyz[-1, :2]-xyz[0, :2]))
        traveled = float(np.linalg.norm(np.diff(xyz[:, :2], axis=0), axis=1).sum())
        terms = [float(np.std(xyz[:, 2])) < config.DEPTH_STD_MAX_M,
                 traveled > 0 and displacement/traveled > config.STRAIGHTNESS_MIN]
        vx, vy = track.get("vel_e", 0), track.get("vel_n", 0)
        speed = hypot(vx, vy)
        x, y = to_local(track["lat"], track["lon"])
        ax, ay = self.zones.asset_points[asset["id"]]
        distance = hypot(ax-x, ay-y)
        toward = speed > config.MIN_BEHAVIOR_SPEED_MPS and distance > 0 and (
            (vx*(ax-x)+vy*(ay-y))/(speed*distance) > cos(radians(config.APPROACH_ANGLE_DEG)))
        against = speed > config.MIN_BEHAVIOR_SPEED_MPS and (
            vx*config.CURRENT_MPS[0]+vy*config.CURRENT_MPS[1] < 0)
        terms.extend((toward, against))
        return config.BEHAVIOR_TERM_WEIGHT*sum(terms)
