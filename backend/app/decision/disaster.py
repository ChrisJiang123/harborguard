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

    def reset(self):
        self.detected_debris.clear()
        self.blocked_zones.clear()
        self.coverage_weights.clear()

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
            for index, target in enumerate(world.targets):
                if value(target, "cls") != "debris":
                    continue
                target_key = str(value(target, "id", index))
                if target_key in self.detected_debris:
                    continue
                x, y = value(target, "x"), value(target, "y")
                if hypot(x-bx, y-by) > config.DISASTER_DETECT_RANGE_M:
                    continue
                if not pinger.safe(buoy, tracks):
                    continue
                scene = [{"cls": "debris", "range_m": hypot(x-bx, y-by), "bearing_deg": 0.0,
                          "length_m": value(target, "length_m", 2.0),
                          "width_m": value(target, "width_m", 0.5), "aspect_deg": 0.0}]
                detection, generated = pinger.detect("", buoy, scene, world)
                events.extend(generated)
                self.detected_debris.add(target_key)
                if detection["cls"] == "debris" and detection["conf"] >= config.DETECTION_MIN_CONF:
                    zid = self.zones.zone_of(x, y)
                    if zid:
                        self.blocked_zones.add(zid)
                        events.append(AlertManager.log(world.t, f"分区 {zid} 检测到碎片，等待人工清理", "warn"))
        for zid, status in statuses.items():
            if zid in restrictions:
                state = "restricted"
            elif zid in self.blocked_zones:
                state = "blocked"
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
