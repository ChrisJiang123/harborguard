"""Small deterministic response optimizer, including a full-port baseline."""
from __future__ import annotations

from shapely.geometry import LineString, Point
from shapely.ops import unary_union

from .. import config
from ..geo import to_local
from .zones import Zones


class Optimizer:
    def __init__(self, zones: Zones, vessels: list[dict]):
        self.zones = zones
        self.vessels = vessels

    @staticmethod
    def future_points(track: dict, horizon: float) -> list[tuple]:
        x, y = to_local(track["lat"], track["lon"])
        vx, vy = track.get("vel_e", 0), track.get("vel_n", 0)
        return [(x+vx*t, y+vy*t) for t in range(0, int(horizon)+1, int(config.PREDICT_EVERY_S))]

    def generate(self, track: dict, alert: dict) -> dict:
        points = self.future_points(track, config.PREDICT_HORIZON_S)
        path = LineString(points) if len(set(points)) > 1 else Point(points[0])
        polygons, props = self.zones.polygons, self.zones.properties
        asset = next(a for a in self.zones.assets if a["id"] == alert["asset_id"])
        asset_xy = self.zones.asset_points[asset["id"]]
        asset_zone = self.zones.zone_of(*asset_xy)
        all_zones = set(polygons)
        candidates = []
        for index, buffer in enumerate(config.OPTION_BUFFERS_M, 1):
            closed = {zid for zid, polygon in polygons.items() if path.buffer(buffer).intersects(polygon)}
            if asset_zone:
                closed.add(asset_zone)
            neighbors = {neighbor for zid in closed for neighbor in props[zid].get("neighbors", [])}
            speed_limit = {zid for zid in neighbors-closed if props[zid]["kind"] == "channel"} if index == 2 else set()
            candidates.append((f"opt-{index}", "最小封闭" if index == 1 else "扩大缓冲 + 限速", False, closed, speed_limit))
        surrounding = Point(asset_xy).buffer(config.ASSET_CLOSURE_RADIUS_M)
        candidates.append(("opt-3", "资产周边封闭", False,
                           {zid for zid, polygon in polygons.items() if surrounding.intersects(polygon)}, set()))
        # Deduplicate local sets and retain the explicit full-port baseline.
        seen = {frozenset(all_zones)}
        options = []
        for oid, label, baseline, closed, limited in candidates:
            key = frozenset(closed)
            if key in seen:
                continue
            seen.add(key)
            options.append(self.option(oid, label, baseline, closed, limited, track))
        options.append(self.option("port-closure", "全港关闭", True, all_zones, set(), track))
        ranked = sorted(options, key=lambda o: (
            0 if o["residual_risk"] <= config.RESIDUAL_ACCEPTABLE else 1,
            o["delay_vessel_hours"] if o["residual_risk"] <= config.RESIDUAL_ACCEPTABLE else o["residual_risk"],
            o["residual_risk"], o["id"]))
        return {"alert_id": alert["id"], "options": options, "ranked": [o["id"] for o in ranked]}

    def option(self, oid, label, baseline, closed, limited, track):
        props = self.zones.properties
        duration = config.CLOSURE_H_FULL if baseline else config.CLOSURE_H_LOCAL
        berth_total = sum(p.get("berths", 0) for p in props.values())
        berth_closed = sum(props[z].get("berths", 0) for z in closed)
        affected = sum(v["zone_id"] in closed and v["movement"] in {"arrive", "depart"}
                       and v["t_h"] <= duration for v in self.vessels)
        footprint = unary_union([self.zones.polygons[zid] for zid in closed])
        predicted = self.future_points(track, config.RESIDUAL_HORIZON_S)[1:]
        residual = sum(not footprint.covers(Point(x, y)) for x, y in predicted)/max(len(predicted), 1)
        return {"id": oid, "label": label, "is_baseline": baseline,
                "zones_closed": sorted(closed), "speed_limit_zones": sorted(limited),
                "berths_open_pct": 1-berth_closed/berth_total if berth_total else 0.0,
                "vessels_affected": affected, "delay_vessel_hours": affected*duration,
                "residual_risk": residual}
