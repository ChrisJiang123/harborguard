"""Seeded passive acoustic measurements; no source identity crosses this boundary."""
from __future__ import annotations

import math
from typing import Any

from .. import config
from ..geo import to_local


def _value(obj: Any, name: str, default: Any = None) -> Any:
    return obj.get(name, default) if isinstance(obj, dict) else getattr(obj, name, default)


class Acoustics:
    """Build anonymous bearing/elevation observations using the world's RNG."""

    def observe(self, world: Any, dt: float = 1.0) -> list[dict]:
        observations = []
        buoys = world.buoys.values() if isinstance(world.buoys, dict) else world.buoys
        noise_level = config.NL_DB + (config.NOISE_INCREASE_DB if world.noise_up else 0.0)
        for buoy in buoys:
            if _value(buoy, "status", "ok") != "ok":
                continue
            bx, by = to_local(_value(buoy, "lat"), _value(buoy, "lon"))
            for target in world.targets:
                cls = _value(target, "cls")
                if cls not in config.SL_DB:
                    continue
                if cls == "marine_mammal":
                    calling = _value(target, "calling")
                    if not callable(calling) or not calling(world.t):
                        continue
                dx, dy = _value(target, "x") - bx, _value(target, "y") - by
                depth = _value(target, "depth", 0.0)
                horizontal_range = math.hypot(dx, dy)
                distance = math.hypot(horizontal_range, depth)
                if distance > _value(buoy, "range_m", 600.0):
                    continue
                snr = config.SL_DB[cls] - 20 * math.log10(max(distance, 1.0)) - noise_level
                if snr <= config.DT_DB or world.rng.random() >= config.DETECT_PROBABILITY:
                    continue
                sigma = config.BEARING_BASE_SIGMA_DEG + config.BEARING_EXTRA_SIGMA_DEG * math.exp(-snr / 10)
                cue = "narrowband" if cls == "uuv" else ("call" if cls == "marine_mammal" else "broadband")
                observations.append({
                    "buoy_id": _value(buoy, "id"),
                    "bearing_deg": (math.degrees(math.atan2(dx, dy)) + world.rng.normal(0, sigma)) % 360,
                    "elevation_deg": math.degrees(math.atan2(depth, horizontal_range)) + world.rng.normal(0, sigma),
                    "snr_db": snr,
                    "noise_level_db": noise_level,
                    "bearing_sigma_deg": sigma,
                    "cue": cue,
                })
            if world.rng.random() < -math.expm1(-config.FALSE_ALARM_RATE * max(dt, 0.0)):
                observations.append({
                    "buoy_id": _value(buoy, "id"), "bearing_deg": float(world.rng.uniform(0, 360)),
                    "elevation_deg": float(world.rng.uniform(0, 10)),
                    "snr_db": float(world.rng.uniform(0, config.DT_DB)),
                    "noise_level_db": noise_level,
                    "bearing_sigma_deg": config.BEARING_BASE_SIGMA_DEG + config.BEARING_EXTRA_SIGMA_DEG,
                    "cue": "none",
                })
        return observations
