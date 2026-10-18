"""Versioned JSON checkpoint of explicitly selected runtime fields; no pickle.

Geometry, classifiers and static data are rebuilt normally. Only allowlisted
simulation objects can be decoded. PNG bytes live separately in SQLite.
"""
from __future__ import annotations

import copy
import hashlib
from collections import deque

import numpy as np

from . import config
from .perception.kalman import Kalman3D
from .perception.tracker import _Track
from .sim.targets import UUV, Debris, FishSchool, Mammal, Target, Vessel, WaypointTarget
from .storage import StorageError

VERSION = 1
CLASSES = {cls.__name__: cls for cls in (Target, WaypointTarget, UUV, Vessel, FishSchool, Debris, Mammal, _Track, Kalman3D)}
WORLD = "t mode network scenario_id paused speed duration_s rng targets buoys noise_up _events _event_index".split()
DECISION = "mode options last_optimized option_sets operator_restrictions zone_statuses reopen_plan".split()
PINGER = "last_ping counts warning_at pinging_until detections counter".split()
ENGINE = "logs recommendations _tracks _scan_elapsed _ended _truth_history debug_truth tick_ms".split()


def fingerprint():
    digest = hashlib.sha256(f"harborguard-checkpoint-{VERSION}".encode())
    paths = [config.ROOT / "backend/app/config.py"] + sorted(config.DATA_DIR.rglob("*.json"))
    paths += sorted(config.DATA_DIR.rglob("*.geojson"))
    paths += sorted(config.DATA_DIR.rglob("*.yaml"))
    for path in paths:
        digest.update(str(path.relative_to(config.ROOT)).encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def encode(value):
    # The great majority of values are ordinary history coordinates/timestamps.
    # Handle them before NumPy/object dispatch without changing the JSON format.
    if value is None or type(value) in (str, bool, int, float):
        return value
    if isinstance(value, dict):
        return {k: encode(v) for k, v in value.items()}
    if isinstance(value, list):
        return [encode(v) for v in value]
    if isinstance(value, np.ndarray):
        return {"__hg__": "array", "value": value.tolist()}
    if isinstance(value, np.random.Generator):
        return {"__hg__": "rng", "value": value.bit_generator.state}
    if isinstance(value, np.generic):
        return value.item()
    if type(value).__name__ in CLASSES and type(value) is CLASSES[type(value).__name__]:
        return {"__hg__": type(value).__name__, "value": encode(vars(value))}
    if isinstance(value, (set, tuple, deque)):
        return {"__hg__": type(value).__name__, "value": [encode(v) for v in value],
                "maxlen": value.maxlen if isinstance(value, deque) else None}
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    raise TypeError(f"Unsupported checkpoint type: {type(value).__name__}")


def decode(value):
    if isinstance(value, list):
        return [decode(v) for v in value]
    if not isinstance(value, dict):
        return value
    kind = value.get("__hg__")
    if kind is None:
        return {k: decode(v) for k, v in value.items()}
    data = value["value"]
    if kind == "array":
        return np.asarray(data, dtype=float)
    if kind == "rng":
        rng = np.random.default_rng()
        rng.bit_generator.state = data
        return rng
    if kind == "set":
        return set(decode(v) for v in data)
    if kind == "tuple":
        return tuple(decode(v) for v in data)
    if kind == "deque":
        return deque((decode(v) for v in data), maxlen=value["maxlen"])
    if kind in CLASSES:
        obj = CLASSES[kind].__new__(CLASSES[kind])
        obj.__dict__.update(decode(data))
        return obj
    raise StorageError(f"Unsupported checkpoint object: {kind}")


def fields(obj, names):
    return {name: getattr(obj, name) for name in names}


def capture(game, *, copy_values=True):
    """Copy for rollback, or borrow synchronously while encoding before commit."""
    decision = game.decision
    snapshot = {"version": VERSION, "engine": fields(game, ENGINE),
        "world": fields(game.world, WORLD), "tracker": vars(game.tracker),
        "decision": fields(decision, DECISION), "risk": {"first_seen": decision.risk.first_seen},
        "alerts": vars(decision.alert_manager), "pinger": fields(decision.pinger, PINGER),
        "disaster": fields(decision.disaster, ["detected_debris", "blocked_zones", "coverage_weights", "attempts"])}
    return copy.deepcopy(snapshot) if copy_values else snapshot


def restore(game, snapshot, images):
    if snapshot["version"] != VERSION:
        raise StorageError("Unsupported checkpoint format")
    decision = game.decision
    for obj, key in ((game, "engine"), (game.world, "world"), (game.tracker, "tracker"),
                     (decision, "decision"), (decision.risk, "risk"), (decision.alert_manager, "alerts"),
                     (decision.pinger, "pinger"), (decision.disaster, "disaster")):
        obj.__dict__.update(snapshot[key])
    decision.alerts = decision.alert_manager.alerts
    decision.detections = decision.pinger.detections
    decision.images = decision.pinger.images = images
