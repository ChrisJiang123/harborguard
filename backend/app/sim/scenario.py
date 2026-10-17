"""Read the versioned YAML demo scripts without executing arbitrary YAML tags."""
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import yaml

from .. import config
from ..geo import to_local
from .targets import UUV, Debris, FishSchool, Mammal, Target, Vessel


def _point(point: list[float]) -> tuple[float, float, float]:
    x, y = to_local(point[0], point[1])
    return x, y, float(point[2] if len(point) > 2 else 0.0)


@dataclass(frozen=True)
class Scenario:
    id: str
    seed: int
    mode: str
    duration_s: float
    default_speed: float
    targets: list[dict[str, Any]]
    events: list[dict[str, Any]]
    routes: dict[str, list[list[float]]]

    def make_targets(self, rng: np.random.Generator) -> list[Target]:
        result: list[Target] = []
        for item in self.targets:
            cls, target_id = item["cls"], item["id"]
            if cls in {"uuv", "vessel"}:
                points = item.get("waypoints") or self.routes.get(item.get("route"))
                if not points:
                    raise ValueError(f"Target {target_id} has no route")
                local_points = [_point(point) for point in points]
                if cls == "uuv":
                    target = UUV(target_id, local_points,
                                 float(item.get("speed_mps", config.SIM_UUV_SPEED_MPS)))
                else:
                    target = Vessel(target_id, local_points,
                                    float(item.get("speed_mps", config.SIM_VESSEL_SPEED_MPS)),
                                    loop=bool(item.get("loop", True)))
            elif cls in {"fish_school", "marine_mammal", "debris"}:
                x, y, _ = _point(item["center"])
                if cls == "fish_school":
                    target = FishSchool(target_id, x, y, rng,
                                        float(item.get("radius_m", config.SIM_FISH_WANDER_RADIUS_M)))
                elif cls == "marine_mammal":
                    target = Mammal(target_id, x, y, rng)
                else:
                    target = Debris(target_id, x, y, drift=bool(item.get("drift", False)))
            else:
                raise ValueError(f"Unknown target class: {cls}")
            result.append(target)
        if len({target.id for target in result}) != len(result):
            raise ValueError("Scenario target IDs must be unique")
        return result


def load_scenario(scenario_id: str, data_dir: Path | None = None) -> Scenario:
    if scenario_id not in {"a", "b"}:
        raise ValueError("Scenario must be a or b")
    path = (data_dir or config.DATA_DIR) / "scenarios" / f"scenario_{scenario_id}.yaml"
    with path.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if data["id"] != scenario_id or data["mode"] not in {"security", "disaster"}:
        raise ValueError("Invalid scenario metadata")
    duration = float(data.get("duration_s", config.SIM_DEFAULT_DURATION_S))
    speed = float(data.get("default_speed", config.SIM_DEFAULT_SPEED))
    if not np.isfinite(duration) or duration <= 0 or not 0 < speed <= config.MAX_SPEED:
        raise ValueError("Scenario duration and speed must be positive and finite")
    events = sorted(data.get("events", []), key=lambda event: float(event["t"]))
    if any(not 0 <= float(event["t"]) <= duration for event in events):
        raise ValueError("Script event outside scenario duration")
    return Scenario(scenario_id, int(data["seed"]), data["mode"], duration, speed,
                    data.get("targets", []), events, data.get("routes", {}))
