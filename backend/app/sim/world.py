"""Simulation state and scheduled faults, independent of HTTP and wall clock."""
import json
from copy import deepcopy
from math import isfinite
from pathlib import Path

import numpy as np

from .. import config
from .scenario import load_scenario


class World:
    """The engine owns scheduling; ``step`` only advances simulated seconds.

    Fixed internal substeps also make offline ``step(120)`` and 1,200 calls to
    ``step(0.1)`` use the same seeded kinematics. Paused/idle/ended worlds do not
    advance. Reaching duration pauses the world with ``t == duration_s``.
    """

    def __init__(self, data_dir: Path | None = None):
        self.data_dir = Path(data_dir or config.DATA_DIR)
        self.zones_geojson = self._read_json("zones.geojson")
        self.assets = self._read_json("assets.json")
        self.vessels = self._read_json("vessels.json")
        self._initial_buoys = self._read_json("buoys.json")
        self.reset()

    def _read_json(self, name: str):
        with (self.data_dir / name).open(encoding="utf-8") as handle:
            return json.load(handle)

    def reset(self) -> None:
        self.t = 0.0
        self.mode = "security"
        self.network = "online"
        self.scenario_id = None
        self.paused = True
        self.speed = config.SIM_DEFAULT_SPEED
        self.duration_s = config.SIM_DEFAULT_DURATION_S
        self.rng = np.random.default_rng(config.SIM_SEED_IDLE)
        self.targets = []
        self.buoys = {item["id"]: {**deepcopy(item), "status": "ok", "pinging": False}
                      for item in self._initial_buoys}
        self.noise_up = False
        self._events = []
        self._event_index = 0

    def start(self, scenario_id: str, speed: float | None = None) -> None:
        scenario = load_scenario(scenario_id, self.data_dir)
        chosen_speed = float(scenario.default_speed if speed is None else speed)
        if not isfinite(chosen_speed) or not 0 < chosen_speed <= config.MAX_SPEED:
            raise ValueError(f"Speed must be positive and at most {config.MAX_SPEED}")
        self.reset()
        self.scenario_id, self.mode = scenario.id, scenario.mode
        self.speed, self.duration_s, self.paused = chosen_speed, scenario.duration_s, False
        self.rng = np.random.default_rng(scenario.seed)
        self.targets = scenario.make_targets(self.rng)
        self._events = deepcopy(scenario.events)

    def inject(self, event_type: str, target: str | None = None) -> list[tuple[str, dict]]:
        """Apply explicit/scripted faults using the same state transitions."""
        changes = []
        if event_type in {"buoy_down", "buoy_up"}:
            if target not in self.buoys:
                raise ValueError(f"Unknown buoy: {target}")
            buoy = self.buoys[target]
            status = "down" if event_type == "buoy_down" else "ok"
            buoy["status"] = status
            if status == "down":
                buoy["pinging"] = False
            changes.append(("buoy_changed", {"buoy_id": target, "status": status}))
        elif event_type in {"network_down", "network_up"}:
            self.network = "offline" if event_type == "network_down" else "online"
            changes.append(("network_changed", {"network": self.network}))
        elif event_type in {"noise_up", "noise_down"}:
            self.noise_up = event_type == "noise_up"
        else:
            raise ValueError(f"Unknown injection: {event_type}")
        changes.append(("log", {"log": {"t": self.t, "level": "warn", "source": "sim",
                                          "text": f"Injected {event_type}" + (f": {target}" if target else "")}}))
        return changes

    def _due_events(self) -> list[tuple[str, dict]]:
        result = []
        while self._event_index < len(self._events):
            event = self._events[self._event_index]
            if float(event["t"]) > self.t + config.SIM_TIME_EPSILON_S:
                break
            self._event_index += 1
            if event["type"] == "log":
                result.append(("log", {"log": {"t": self.t, "level": event.get("level", "info"),
                                                "source": "sim", "text": event["text"]}}))
            else:
                result.extend(self.inject(event["type"], event.get("target")))
        return result

    def step(self, dt: float) -> list[tuple[str, dict]]:
        dt = float(dt)
        if not isfinite(dt) or dt < 0:
            raise ValueError("Simulation dt must be finite and nonnegative")
        if self.paused or self.scenario_id is None:
            return []
        events = self._due_events()
        until = min(self.duration_s, round(self.t + dt, 10))
        while self.t + config.SIM_TIME_EPSILON_S < until:
            step = round(min(config.SIM_FIXED_STEP_S, until - self.t), 10)
            if self._event_index < len(self._events):
                event_t = float(self._events[self._event_index]["t"])
                if self.t < event_t < self.t + step:
                    step = event_t - self.t
            for target in self.targets:
                target.step(step, self.rng)
            self.t = round(self.t + step, 10)
            events.extend(self._due_events())
        if self.t + config.SIM_TIME_EPSILON_S >= self.duration_s:
            self.t, self.paused = self.duration_s, True
        return events
