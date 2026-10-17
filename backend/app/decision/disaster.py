"""Disaster sonar coverage and connectivity-based reopening recommendations."""
from __future__ import annotations

from collections import deque
from math import hypot

from shapely.geometry import Point

from .. import config
from ..geo import to_local
from .alerts import AlertManager
from .pinger import value
from .zones import Zones


class DisasterSurvey:
    def __init__(self, zones: Zones):
        self.zones = zones
        self.detected_debris: set[str] = set()
        self.blocked_zones: set[str] = set()
        self.coverage_weights: dict[str, dict[str, float]] = {}
        self.attempts: dict[str, dict] = {}

    def reset(self):
        self.detected_debris.clear()
        self.blocked_zones.clear()
        self.coverage_weights.clear()
        self.attempts.clear()

    def step(self, world, tracks, dt, statuses, restrictions, pinger) -> list[tuple]:
        events = []
        for bid, buoy in world.buoys.items():
            if buoy["status"] != "ok":
                continue
            bx, by = to_local(buoy["lat"], buoy["lon"])
            if bid not in self.coverage_weights:
                footprint = Point(bx, by).buffer(config.DISASTER_SCAN_RANGE_M)
                self.coverage_weights[bid] = {zid: footprint.intersection(polygon).area/polygon.area
                                               for zid, polygon in self.zones.polygons.items()}
            for zid, fraction in self.coverage_weights[bid].items():
                statuses[zid]["coverage"] = min(1.0, statuses[zid]["coverage"]+
                                                dt*config.DISASTER_COVERAGE_RATE*fraction)
        # The simulation supplies survey candidates as before; their truth class
        # is never used as a successful classification. A failed observation is
        # neither confirmed debris nor evidence that its zone is safe to reopen.
        for index, target in enumerate(world.targets):
            if value(target, "cls") != "debris":
                continue
            key = str(value(target, "id", index))
            if key in self.detected_debris:
                continue
            x, y = value(target, "x"), value(target, "y")
            available = []
            for bid, buoy in world.buoys.items():
                bx, by = to_local(buoy["lat"], buoy["lon"])
                distance = hypot(x-bx, y-by)
                if buoy["status"] == "ok" and distance <= config.DISASTER_DETECT_RANGE_M:
                    available.append((distance, bid, buoy))
            if not available:
                continue
            if key not in self.attempts:
                self.attempts[key] = {"zone_id": self.zones.zone_of(x, y), "count": 0,
                                      "last_t": None, "buoy_ids": []}
            attempt = self.attempts[key]
            if (attempt["count"] >= config.DISASTER_RETRY_MAX
                    or (attempt["last_t"] is not None
                        and world.t-attempt["last_t"] < config.DISASTER_RETRY_S-config.SIM_TIME_EPSILON_S)):
                continue
            min_range = getattr(pinger.classifier, "survey_min_range_m", config.DISASTER_MIN_RANGE_M)
            suitable = [item for item in available if item[0] >= min_range
                        and pinger.safe(item[2], tracks)]
            if not suitable:
                continue  # Near-field/mammal-protected candidates remain uncertain.
            distance, bid, buoy = min(suitable, key=lambda item: (
                item[1] in attempt["buoy_ids"], item[0], item[1]))
            scene = [{"cls": "debris", "range_m": distance, "bearing_deg": 0.0,
                      "length_m": value(target, "length_m", 2.0),
                      "width_m": value(target, "width_m", 0.5), "aspect_deg": 0.0}]
            detection, generated = pinger.detect("", buoy, scene, world, expected_range=distance)
            events.extend(generated)
            attempt["count"] += 1
            attempt["last_t"] = world.t
            attempt["buoy_ids"].append(bid)
            zid = attempt["zone_id"]
            if detection["cls"] == "debris" and detection["conf"] >= config.DETECTION_MIN_CONF:
                self.detected_debris.add(key)
                if zid:
                    self.blocked_zones.add(zid)
                    events.append(AlertManager.log(world.t, f"分区 {zid} 检测到碎片，等待人工清理", "warn"))
            elif zid:
                events.append(AlertManager.log(world.t,
                    f"分区 {zid} 声呐结果未确认，保持未勘测（{attempt['count']}/{config.DISASTER_RETRY_MAX}）", "warn"))
        uncertain = {a["zone_id"] for key, a in self.attempts.items() if key not in self.detected_debris}
        for zid, status in statuses.items():
            if zid in restrictions:
                state = "restricted"
            elif zid in self.blocked_zones:
                state = "blocked"
            elif zid in uncertain:
                state = "unsurveyed"
            elif status["coverage"] >= config.DISASTER_CLEAR_COVERAGE:
                state = "clear"
            else:
                state = "unsurveyed"
            if status["state"] != state:
                status["state"] = state
                events.append(("zone_changed", {"zone_id": zid, "state": state}))
        return events

    def reopen(self, statuses: dict) -> dict:
        props = self.zones.properties
        entrances = sorted(zid for zid, p in props.items() if p.get("entrance")
                           and p["kind"] == "channel" and statuses[zid]["state"] == "clear")
        reachable = set(entrances)
        queue = deque(entrances)
        while queue:
            zid = queue.popleft()
            for neighbor in sorted(props[zid].get("neighbors", [])):
                if (neighbor not in reachable and props[neighbor]["kind"] == "channel"
                        and statuses[neighbor]["state"] == "clear"):
                    reachable.add(neighbor)
                    queue.append(neighbor)
        berths = {neighbor for zid in reachable for neighbor in props[zid].get("neighbors", [])
                  if props[neighbor]["kind"] == "berth" and statuses[neighbor]["state"] == "clear"}
        unsurveyed = sorted(z for z, s in statuses.items() if s["state"] == "unsurveyed")
        blocked = sorted(z for z, s in statuses.items() if s["state"] == "blocked")
        surveyed = len(statuses)-len(unsurveyed)-len(blocked)
        return {"route_zone_ids": sorted(reachable), "reopen_berth_zone_ids": sorted(berths),
                "unsurveyed_zone_ids": unsurveyed, "blocked_zone_ids": blocked,
                "est_hours_saved": surveyed*config.SURVEY_H}
