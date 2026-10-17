"""Small, reproducible kinematic models; these are demo physics, not real craft."""
from dataclasses import dataclass
from math import atan2, cos, hypot, sin, sqrt

import numpy as np

from .. import config


@dataclass
class Target:
    id: str
    cls: str
    x: float
    y: float
    depth: float
    vx: float = 0.0
    vy: float = 0.0
    vz: float = 0.0
    length_m: float = config.SIM_DEFAULT_LENGTH_M
    width_m: float = config.SIM_DEFAULT_WIDTH_M

    def step(self, dt: float, rng: np.random.Generator) -> None:
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.depth = float(np.clip(self.depth + self.vz * dt, 0, config.SEABED_DEPTH_M))

    def calling(self, t: float) -> bool:
        return False


class WaypointTarget(Target):
    """Move along local (east, north, depth) waypoints, preserving travel time."""

    def __init__(self, id: str, cls: str, waypoints: list[tuple[float, float, float]],
                 speed_mps: float, *, loop: bool = False, heading_sigma: float = 0.0,
                 length_m: float = config.SIM_DEFAULT_LENGTH_M,
                 width_m: float = config.SIM_DEFAULT_WIDTH_M):
        if len(waypoints) < 2 or speed_mps <= 0:
            raise ValueError("A moving route needs at least two waypoints and positive speed")
        self.waypoints = [tuple(map(float, point)) for point in waypoints]
        if len({point[:2] for point in self.waypoints}) < 2:
            raise ValueError("A moving route needs distinct horizontal positions")
        super().__init__(id, cls, *self.waypoints[0], length_m=length_m, width_m=width_m)
        self.speed_mps = float(speed_mps)
        self.loop, self.heading_sigma = loop, heading_sigma
        self.waypoint_index = 1
        self._set_velocity()

    def _set_velocity(self) -> None:
        if self.waypoint_index >= len(self.waypoints):
            self.vx = self.vy = self.vz = 0.0
            return
        tx, ty, _ = self.waypoints[self.waypoint_index]
        distance = hypot(tx - self.x, ty - self.y)
        if distance > config.SIM_POSITION_EPSILON_M:
            self.vx = self.speed_mps * (tx - self.x) / distance
            self.vy = self.speed_mps * (ty - self.y) / distance
        else:
            self.vx = self.vy = 0.0
        self.vz = 0.0

    def step(self, dt: float, rng: np.random.Generator) -> None:
        remaining = float(dt)
        while remaining > config.SIM_TIME_EPSILON_S and self.waypoint_index < len(self.waypoints):
            tx, ty, target_depth = self.waypoints[self.waypoint_index]
            distance = hypot(tx - self.x, ty - self.y)
            travel_time = distance / self.speed_mps
            if travel_time <= remaining + config.SIM_TIME_EPSILON_S:
                self.x, self.y, self.depth = tx, ty, target_depth
                remaining = max(0.0, remaining - travel_time)
                self.waypoint_index += 1
                if self.loop and self.waypoint_index == len(self.waypoints):
                    self.waypoint_index = 0
                self._set_velocity()
                continue
            angle = atan2(ty - self.y, tx - self.x)
            if self.heading_sigma:
                angle += float(rng.normal(0.0, self.heading_sigma * sqrt(remaining)))
            self.vx = self.speed_mps * cos(angle)
            self.vy = self.speed_mps * sin(angle)
            self.vz = 0.0
            self.x += self.vx * remaining
            self.y += self.vy * remaining
            remaining = 0.0


class UUV(WaypointTarget):
    def __init__(self, id: str, waypoints: list[tuple[float, float, float]],
                 speed_mps: float = config.SIM_UUV_SPEED_MPS,
                 heading_sigma: float = config.SIM_UUV_HEADING_SIGMA):
        super().__init__(id, "uuv", waypoints, speed_mps, heading_sigma=heading_sigma,
                         length_m=config.SIM_UUV_LENGTH_M, width_m=config.SIM_UUV_WIDTH_M)


class Vessel(WaypointTarget):
    def __init__(self, id: str, waypoints: list[tuple[float, float, float]],
                 speed_mps: float = config.SIM_VESSEL_SPEED_MPS, loop: bool = True):
        surface_points = [(x, y, 0.0) for x, y, _ in waypoints]
        super().__init__(id, "vessel", surface_points, speed_mps, loop=loop,
                         length_m=config.SIM_VESSEL_LENGTH_M, width_m=config.SIM_VESSEL_WIDTH_M)


class FishSchool(Target):
    def __init__(self, id: str, x: float, y: float, rng: np.random.Generator,
                 radius_m: float = config.SIM_FISH_WANDER_RADIUS_M):
        angle = float(rng.uniform(-np.pi, np.pi))
        speed = float(rng.uniform(*config.SIM_FISH_SPEED_MPS))
        super().__init__(id, "fish_school", x, y, float(rng.uniform(*config.SIM_FISH_DEPTH_M)),
                         speed * cos(angle), speed * sin(angle),
                         length_m=config.SIM_FISH_LENGTH_M, width_m=config.SIM_FISH_WIDTH_M)
        self.center = (x, y)
        self.radius_m = radius_m

    def step(self, dt: float, rng: np.random.Generator) -> None:
        self.vx += float(rng.normal(0, config.SIM_FISH_ACCEL_SIGMA * sqrt(dt)))
        self.vy += float(rng.normal(0, config.SIM_FISH_ACCEL_SIGMA * sqrt(dt)))
        speed = hypot(self.vx, self.vy)
        limited = float(np.clip(speed, *config.SIM_FISH_SPEED_MPS))
        if speed:
            self.vx *= limited / speed
            self.vy *= limited / speed
        if hypot(self.x - self.center[0], self.y - self.center[1]) > self.radius_m:
            angle = atan2(self.center[1] - self.y, self.center[0] - self.x)
            self.vx, self.vy = limited * cos(angle), limited * sin(angle)
        self.vz += float(rng.normal(0, config.SIM_FISH_VERTICAL_SIGMA * sqrt(dt)))
        self.vz = float(np.clip(self.vz, -config.SIM_FISH_VERTICAL_MAX_MPS,
                               config.SIM_FISH_VERTICAL_MAX_MPS))
        super().step(dt, rng)
        self.depth = float(np.clip(self.depth, config.SIM_FISH_DEPTH_M[0],
                                   min(config.SIM_FISH_DEPTH_M[1], config.SEABED_DEPTH_M)))


class Debris(Target):
    def __init__(self, id: str, x: float, y: float, *, drift: bool = False):
        current_speed = hypot(*config.CURRENT_MPS)
        scale = config.SIM_DEBRIS_DRIFT_MPS / current_speed if drift and current_speed else 0.0
        super().__init__(id, "debris", x, y, config.SEABED_DEPTH_M - config.SIM_DEBRIS_SEABED_GAP_M,
                         config.CURRENT_MPS[0] * scale, config.CURRENT_MPS[1] * scale,
                         length_m=config.SIM_DEBRIS_LENGTH_M, width_m=config.SIM_DEBRIS_WIDTH_M)


class Mammal(Target):
    def __init__(self, id: str, x: float, y: float, rng: np.random.Generator):
        angle = float(rng.uniform(-np.pi, np.pi))
        speed = float(rng.uniform(*config.SIM_MAMMAL_SPEED_MPS))
        super().__init__(id, "marine_mammal", x, y, config.SIM_MAMMAL_DEPTH_M,
                         speed * cos(angle), speed * sin(angle),
                         length_m=config.SIM_MAMMAL_LENGTH_M, width_m=config.SIM_MAMMAL_WIDTH_M)

    def calling(self, t: float) -> bool:
        return float(t) % config.SIM_MAMMAL_CALL_PERIOD_S < config.SIM_MAMMAL_CALL_DURATION_S
