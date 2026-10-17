"""Metric geometry for decision rules; outward coordinates remain WGS84."""
from __future__ import annotations

from math import hypot

from shapely.geometry import Point, shape

from .. import config
from ..geo import to_local


class Zones:
    def __init__(self, geojson: dict, assets: list[dict]):
        self.features = {f["properties"]["id"]: f for f in geojson["features"]}
        self.properties = {k: f["properties"] for k, f in self.features.items()}
        def project(coordinates):
            if isinstance(coordinates[0], (int, float)):
                return to_local(coordinates[1], coordinates[0])
            return [project(points) for points in coordinates]

        self.polygons = {k: shape({"type": f["geometry"]["type"],
                                   "coordinates": project(f["geometry"]["coordinates"])})
                         for k, f in self.features.items()}
        self.assets = assets
        self.asset_points = {a["id"]: to_local(a["lat"], a["lon"]) for a in assets}

    def zone_of(self, x: float, y: float) -> str | None:
        point = Point(x, y)
        return next((k for k, polygon in self.polygons.items() if polygon.covers(point)), None)

    def nearest_asset(self, x: float, y: float) -> tuple[dict, float]:
        if not self.assets:
            raise ValueError("At least one protected asset is required")
        asset = min(self.assets, key=lambda a: hypot(x-self.asset_points[a["id"]][0],
                                                    y-self.asset_points[a["id"]][1]))
        ax, ay = self.asset_points[asset["id"]]
        return asset, hypot(x-ax, y-ay)

    def eta(self, x: float, y: float, vx: float, vy: float, asset: dict) -> float | None:
        ax, ay = self.asset_points[asset["id"]]
        distance = hypot(ax-x, ay-y)
        if distance == 0:
            return 0.0
        approaching = ((ax-x)*vx + (ay-y)*vy) / distance
        return distance / approaching if approaching > config.MIN_ETA_SPEED_MPS else None
