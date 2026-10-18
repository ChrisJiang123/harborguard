"""Synthetic active sensor boundary, not a measured sonar contact extractor.

All simulated reflectors provide ideal, metre-quantized anonymous contact
positions, including near-field contacts whose image may be unusable. No truth
class or target ID is exported with contacts. Classes are used only to generate
the physical image with C's renderer. Real raw-return extraction is not modeled.
"""
from dataclasses import dataclass
from math import atan2, degrees, hypot, sqrt

from .. import config
from ..geo import to_local


def value(target, key, default=None):
    return target.get(key, default) if isinstance(target, dict) else getattr(target, key, default)


@dataclass(frozen=True)
class SurveyContact:
    key: str
    x: float
    y: float
    uncertainty_m: float


def survey_contacts(world):
    """Ideal anonymous observations; never filter or identify by target class."""
    grid = config.DISASTER_OBSERVATION_GRID_M
    cells = dict.fromkeys((round(value(target, "x")/grid), round(value(target, "y")/grid))
                          for target in world.targets)
    return [SurveyContact(f"echo:{ix}:{iy}", ix*grid, iy*grid, grid/sqrt(2)) for ix, iy in cells]


def sonar_scene(world, buoy, aim_x, aim_y):
    """Generate renderer inputs only. Never use these labels as model results."""
    bx, by = to_local(buoy["lat"], buoy["lon"])
    heading = degrees(atan2(aim_x-bx, aim_y-by))
    targets = []
    for target in world.targets:
        cls = value(target, "cls")
        if cls not in config.SONAR_TARGET_CLASSES:
            continue
        dx, dy = value(target, "x")-bx, value(target, "y")-by
        distance = hypot(dx, dy)
        # At the origin azimuth is undefined. Keep the true zero range; do not
        # discard its degenerate return merely because the aiming angle differs.
        bearing = 0.0 if distance <= config.SIM_POSITION_EPSILON_M else (
            (degrees(atan2(dx, dy))-heading+180) % 360-180)
        if distance > config.PING_RANGE_M or abs(bearing) > config.SONAR_FOV_DEG/2:
            continue
        targets.append({"cls": cls, "range_m": distance, "bearing_deg": bearing,
                        "length_m": value(target, "length_m", 2.0),
                        "width_m": value(target, "width_m", 0.5),
                        "aspect_deg": degrees(atan2(value(target, "vx", 0), value(target, "vy", 0)))-heading})
    return targets
