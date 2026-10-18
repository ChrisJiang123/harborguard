"""Disaster sonar coverage and connectivity-based reopening recommendations."""
from __future__ import annotations

from collections import deque
from math import hypot

from shapely.geometry import Point

from .. import config
from ..geo import to_local
from ..sim.sonar import sonar_scene, survey_contacts
from .alerts import AlertManager
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
        # Sensor positions are synthetic observations, not truth classes/IDs.
        # Misses, non-debris predictions and unusable geometry are all unresolved.
        associated = set()
        for contact in survey_contacts(world):
            x, y = contact.x, contact.y
            available = []
            for bid, buoy in world.buoys.items():
                bx, by = to_local(buoy["lat"], buoy["lon"])
                distance = hypot(x-bx, y-by)
                if buoy["status"] == "ok" and distance <= config.DISASTER_DETECT_RANGE_M:
                    available.append((distance, bid, buoy))
            if not available:
                continue
            matches = [(hypot(x-a["x"], y-a["y"]), key) for key, a in self.attempts.items()
                       if key not in associated and hypot(x-a["x"], y-a["y"]) <= config.DISASTER_ASSOCIATION_M]
            key = min(matches)[1] if matches else contact.key
            associated.add(key)
            point = Point(x, y)
            zone_ids = [zid for zid, polygon in self.zones.polygons.items()
                        if polygon.distance(point) <= contact.uncertainty_m]
            if key not in self.attempts:
                self.attempts[key] = {"zone_id": self.zones.zone_of(x, y), "count": 0,
                                      "zone_ids": zone_ids, "last_t": None, "buoy_ids": [], "reason": None}
            attempt = self.attempts[key]
            attempt.update(x=x, y=y, zone_ids=sorted(set(attempt["zone_ids"]) | set(zone_ids)))
            if key in self.detected_debris:
                self.blocked_zones.update(attempt["zone_ids"])
                continue
            if (attempt["count"] >= config.DISASTER_RETRY_MAX
                    or (attempt["last_t"] is not None
                        and world.t-attempt["last_t"] < config.DISASTER_RETRY_S-config.SIM_TIME_EPSILON_S)):
                if attempt["reason"] is not None:
                    self._unresolved(attempt, attempt["reason"], world.t, events)
                continue
            min_range = getattr(pinger.classifier, "survey_min_range_m", config.DISASTER_MIN_RANGE_M)
            suitable = [item for item in available if item[0] >= min_range
                        and pinger.safe(item[2], tracks)]
            if not suitable:
                reason = "near_field" if all(item[0] < min_range for item in available) else "protected"
                self._unresolved(attempt, reason, world.t, events)
                continue  # Near-field/mammal-protected candidates remain uncertain.
            distance, bid, buoy = min(suitable, key=lambda item: (
                item[1] in attempt["buoy_ids"], item[0], item[1]))
            # The simulator renders ALL visible reflectors with their physical
            # shapes. Policy sees only the detector's output, not those labels.
            scene = sonar_scene(world, buoy, x, y)
            detection, generated = pinger.detect("", buoy, scene, world, expected_range=distance)
            events.extend(generated)
            attempt["count"] += 1
            attempt["last_t"] = world.t
            attempt["buoy_ids"].append(bid)
            if detection["cls"] == "debris" and detection["conf"] >= config.DETECTION_MIN_CONF:
                attempt["reason"] = "confirmed"
                self.detected_debris.add(key)
                if attempt["zone_ids"]:
                    self.blocked_zones.update(attempt["zone_ids"])
                    events.append(AlertManager.log(world.t,
                        f"Debris detected in zones {'/'.join(attempt['zone_ids'])}; awaiting manual clearance", "warn"))
            else:
                reason = "no_detection" if detection["cls"] == "unknown" else (
                    "low_confidence" if detection["conf"] < config.DETECTION_MIN_CONF else "non_debris")
                self._unresolved(attempt, reason, world.t, events)
        uncertain = {zid for key, a in self.attempts.items() if key not in self.detected_debris
                     for zid in a["zone_ids"]}
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

    @staticmethod
    def _unresolved(attempt, reason, t, events):
        # Explain using existing log events; no new wire fields/status enums.
        marker = [reason, attempt["count"], attempt["zone_ids"]]
        if attempt.get("reported") == marker:
            return
        attempt["reason"] = reason
        attempt["reported"] = marker
        reasons = {"near_field": "near-field imaging boundary; no reliable observation position",
                   "protected": "marine mammal protection; ping withheld",
                   "no_detection": "no sonar detection", "low_confidence": "insufficient detection confidence",
                   "non_debris": "classified as non-debris; an obstruction cannot be ruled out"}
        if attempt["zone_ids"]:
            events.append(AlertManager.log(t,
                f"Zones {'/'.join(attempt['zone_ids'])}: {reasons[reason]}; remain unsurveyed/pending review "
                f"(pings {attempt['count']}/{config.DISASTER_RETRY_MAX}; retry exhaustion does not clear the zone)", "warn"))

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
        surveyed = sum(s["state"] == "clear" for s in statuses.values())
        return {"route_zone_ids": sorted(reachable), "reopen_berth_zone_ids": sorted(berths),
                "unsurveyed_zone_ids": unsurveyed, "blocked_zone_ids": blocked,
                "est_hours_saved": surveyed*config.SURVEY_H}
