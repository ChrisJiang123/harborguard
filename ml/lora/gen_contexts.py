"""Generate synthetic C4 contexts matching C3 collect_* and the frozen contract. Kind ratios are
security70/disaster20/buoy10 with varied alerts, weighted risk, detections, options, buoy loss and
network. Risk weights match B; low-risk options rank by delay before remaining risk-ranked options.
Selection agrees with factcheck.security_selection. Clear/reachable routes, survey-hour estimates
and buoy geometry are internally consistent. IDs come from B data; _trim enforces <=3 KB UTF-8.
Fixed seed reproduces contexts. All observations are synthetic, not field data.
"""


from __future__ import annotations

import argparse
import json
import random
from collections import deque
from pathlib import Path

from agent.context import MAX_CONTEXT_BYTES, _trim, _zone_in_range

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT = REPO_ROOT / "ml" / "lora" / "datasets" / "contexts.jsonl"

RISK_WEIGHTS = {"C": 0.30, "P": 0.25, "B": 0.25, "Z": 0.15, "D": 0.05}
RESIDUAL_ACCEPTABLE = 0.2
CLOSURE_H_LOCAL, CLOSURE_H_FULL, SURVEY_H = 2.0, 6.0, 1.5  # Match backend/app/config.py.
ENTRANCE_ZONE = "channel_entrance"

KIND_RATIOS = (("security", 0.70), ("disaster", 0.20), ("buoy", 0.10))
CLS_RATIOS = (
    ("uuv", 0.40),
    ("debris", 0.20),
    ("fish_school", 0.20),
    ("marine_mammal", 0.15),
    ("unknown", 0.05),
)
CUE_BY_CLS = {
    "uuv": ("narrowband", "narrowband", "broadband", "none"),
    "fish_school": ("broadband", "broadband", "none"),
    "debris": ("none", "none", "broadband"),
    "marine_mammal": ("call", "call", "broadband"),
    "unknown": ("none", "narrowband", "broadband"),
}
DEPTH_RANGE = {
    "uuv": (5.0, 30.0),
    "fish_school": (5.0, 40.0),
    "debris": (2.0, 15.0),
    "marine_mammal": (2.0, 20.0),
    "unknown": (3.0, 25.0),
}


def _weighted(rng: random.Random, table) -> str:
    x = rng.random()
    acc = 0.0
    for value, weight in table:
        acc += weight
        if x < acc:
            return value
    return table[-1][0]


def _round(value: float, digits: int = 2) -> float:
    return round(value, digits)


def load_world(data_dir: Path | None = None) -> dict:
    """Read B-maintained scenario buoys, zones/adjacency, assets and vessel schedules."""
    root = data_dir or (REPO_ROOT / "data")
    geo = json.loads((root / "zones.geojson").read_text(encoding="utf-8"))
    zones = []
    for feature in geo["features"]:
        props = feature["properties"]
        zones.append(
            {
                "id": props["id"],
                "name": props.get("name", props["id"]),
                "kind": props.get("kind", "berth"),
                "berths": int(props.get("berths") or 0),
                "neighbors": list(props.get("neighbors", [])),
            }
        )
    return {
        "zones": zones,
        "zone_ids": [z["id"] for z in zones],
        "berth_zones": [z["id"] for z in zones if z["kind"] == "berth"],
        "channel_zones": [z["id"] for z in zones if z["kind"] == "channel"],
        "features": geo.get("features", []),
        "total_berths": sum(z["berths"] for z in zones) or 1,
        "buoys": json.loads((root / "buoys.json").read_text(encoding="utf-8")),
        "buoy_ids": [b["id"] for b in json.loads((root / "buoys.json").read_text(encoding="utf-8"))],
        "assets": json.loads((root / "assets.json").read_text(encoding="utf-8")),
        "vessels": json.loads((root / "vessels.json").read_text(encoding="utf-8")),
    }


def weighted_risk(breakdown: dict) -> float:
    """Contract risk is the weighted sum of components."""
    return _round(sum(float(breakdown[key]) * weight for key, weight in RISK_WEIGHTS.items()))


def _ranked(options: list[dict]) -> list[str]:
    """Rank risk<=0.2 options by delay first, matching factcheck.security_selection. B may break equal
    delays by risk/ID; training uses the taskbook first-in-list tie break so ranked[0] never
    contradicts the task rule or teaches a ranking-difference branch.
    """
    acceptable = [(i, o) for i, o in enumerate(options) if o["residual_risk"] <= RESIDUAL_ACCEPTABLE]
    rest = [(i, o) for i, o in enumerate(options) if o["residual_risk"] > RESIDUAL_ACCEPTABLE]
    ordered = sorted(acceptable, key=lambda pair: (pair[1]["delay_vessel_hours"], pair[0]))
    ordered += sorted(rest, key=lambda pair: (pair[1]["residual_risk"], pair[0]))
    return [o["id"] for _, o in ordered]


def _closed_vessels(world: dict, closed: set[str], duration: float) -> int:
    """Match B Optimizer.option: affected arrivals/departures lie in closed zones within closure duration."""
    return sum(
        1
        for v in world["vessels"]
        if v.get("zone_id") in closed and v.get("movement") in {"arrive", "depart"} and v["t_h"] <= duration
    )


def _make_options(rng: random.Random, world: dict, asset_zone: str) -> list[dict]:
    """Use the same option measures as B: three local closures and the full-port baseline."""
    neighbors = {z["id"]: z["neighbors"] for z in world["zones"]}
    channels = world["channel_zones"]
    berth_pool = [z for z in world["berth_zones"] if z != asset_zone]
    nearby_berths = [z for z in neighbors.get(asset_zone, []) if z in world["berth_zones"]]

    candidates = [
        ("opt-1", "最小封闭", {asset_zone, rng.choice(channels)}, set()),
        (
            "opt-2",
            "扩大缓冲 + 限速",
            {asset_zone, *rng.sample(channels, k=min(2, len(channels)))},
            set(rng.sample(channels, k=min(1 + (rng.random() < 0.5), len(channels)))),
        ),
        (
            "opt-3",
            "资产周边封闭",
            {asset_zone, *rng.sample(nearby_berths or berth_pool, k=min(2, len(nearby_berths or berth_pool)))},
            set(),
        ),
    ]
    options: list[dict] = []
    for oid, label, closed, limited in candidates:
        duration = CLOSURE_H_LOCAL
        affected = _closed_vessels(world, closed, duration)
        options.append(
            {
                "id": oid,
                "label": label,
                "is_baseline": False,
                "zones_closed": sorted(closed),
                "speed_limit_zones": sorted(limited),
                "berths_open_pct": _round(1 - sum(
                    z["berths"] for z in world["zones"] if z["id"] in closed) / world["total_berths"]),
                "vessels_affected": affected,
                "delay_vessel_hours": _round(affected * duration, 1),
                "residual_risk": _round(rng.uniform(0.05, 0.55) if oid == "opt-1" else rng.uniform(0.03, 0.30)),
            }
        )
    if rng.random() < 0.8:  # Full-port closure baseline.
        all_closed = set(world["zone_ids"])
        affected = _closed_vessels(world, all_closed, CLOSURE_H_FULL)
        options.append(
            {
                "id": "port-closure",
                "label": "全港关闭",
                "is_baseline": True,
                "zones_closed": sorted(all_closed),
                "speed_limit_zones": [],
                "berths_open_pct": 0.0,
                "vessels_affected": affected,
                "delay_vessel_hours": _round(affected * CLOSURE_H_FULL, 1),
                "residual_risk": _round(rng.uniform(0.0, 0.08)),
            }
        )
    # Ensure most samples have at least one option below the residual-risk threshold.
    if all(o["residual_risk"] > RESIDUAL_ACCEPTABLE for o in options):
        rng.choice(options)["residual_risk"] = _round(rng.uniform(0.05, 0.18))
    return options


def _security_context(rng: random.Random, world: dict, index: int) -> dict:
    cls = _weighted(rng, CLS_RATIOS)
    conf = _round(rng.uniform(0.30, 0.58) if cls == "unknown" else rng.uniform(0.40, 0.96))
    t = _round(rng.uniform(30, 1200), 1)
    asset = rng.choice(world["assets"])
    asset_zone = rng.choice(world["berth_zones"])
    has_options = rng.random() >= 0.10  # Before options_ready there is no option; recommendation must be null.

    breakdown = {key: _round(rng.uniform(0.10, 0.95)) for key in RISK_WEIGHTS}
    risk = weighted_risk(breakdown)
    level = 3 if risk >= 0.60 else 2

    down = set()
    roll = rng.random()
    if roll < 0.15:
        down = set(rng.sample(world["buoy_ids"], k=2))
    elif roll < 0.45:
        down = {rng.choice(world["buoy_ids"])}
    ok_buoys = [b for b in world["buoy_ids"] if b not in down]
    n_cover = _weighted(rng, ((0, 0.05), (1, 0.20), (2, 0.35), (3, 0.25), (4, 0.15)))
    covering = rng.sample(ok_buoys, k=min(n_cover, len(ok_buoys)))

    alert_id, track_id, det_id = f"A{index}", f"T{index}", f"det-{index}"
    detected = cls != "unknown"
    eta = None if rng.random() < 0.20 else int(rng.uniform(60, 600))

    context: dict = {
        "kind": "security",
        "t": t,
        "mode": "security",
        "network": "offline" if rng.random() < 0.15 else "online",
        "alert": {
            "id": alert_id,
            "track_id": track_id,
            "level": level,
            "risk": risk,
            "breakdown": breakdown,
            "zone_id": asset_zone if rng.random() < 0.8 else None,
            "asset_id": asset["id"],
            "distance_m": int(rng.uniform(100, 2500)),
            "eta_s": eta,
            "raised_t": _round(max(0.0, t - rng.uniform(30, 180)), 1),
            "updated_t": t,
            "options_ready": has_options,
        },
        "track": {
            "id": track_id,
            "status": "confirmed",
            "cls": cls,
            "conf": conf,
            "cue": rng.choice(CUE_BY_CLS[cls]),
            "lat": _round(asset["lat"] + rng.uniform(-0.01, 0.01), 6),
            "lon": _round(asset["lon"] + rng.uniform(-0.01, 0.01), 6),
            "depth_m": _round(rng.uniform(*DEPTH_RANGE[cls]), 1),
            "speed_mps": _round(rng.uniform(0.5, 3.5), 1),
            "heading_deg": rng.randint(0, 359),
            "level": level,
            "risk": risk,
            "detection_id": det_id if detected else None,
            "history_summary": {
                "depth_std_m": _round(rng.uniform(0.0, 3.0)),
                "straightness": _round(rng.uniform(0.60, 1.0), 3),
            },
        },
        "detections": (
            [{"id": det_id, "cls": cls, "conf": conf, "model": "yolo26n"}] if detected else []
        ),
        "options": [],
        "ranked": [],
        "buoys": {"ok": len(ok_buoys), "down": sorted(down), "covering_track": covering},
        "zones": [
            {
                "id": z["id"],
                "state": "restricted" if z["id"] == asset_zone and rng.random() < 0.2 else "open",
                "coverage": _round(rng.uniform(0.4, 1.0)),
            }
            for z in world["zones"]
        ],
        "recent_logs": [
            f"航迹 {track_id} 已确认，初步类别 {cls}",
            f"识别 {det_id}:{cls}，置信度 {conf:.2f}" if detected else f"航迹 {track_id} 尚无主动识别",
            f"警报 {alert_id} 升至 {level} 级",
            f"资产 {asset['id']} 周边加强监视",
            *( [f"浮标 {bid} 离线" for bid in sorted(down)] ),
        ][:6],
    }
    if has_options:
        options = _make_options(rng, world, asset_zone)
        context["options"] = options
        context["ranked"] = _ranked(options)
    return _trim(context)


def _reachable_clear(world: dict, clear: set[str]) -> set[str]:
    """Reachable set from entry channels using only clear zones, matching Recovery semantics."""
    neighbors = {z["id"]: z["neighbors"] for z in world["zones"]}
    visited: set[str] = set()
    queue = deque([ENTRANCE_ZONE] if ENTRANCE_ZONE in clear else [])
    while queue:
        current = queue.popleft()
        if current in visited:
            continue
        visited.add(current)
        queue.extend(n for n in neighbors.get(current, []) if n in clear and n not in visited)
    return visited


def _disaster_context(rng: random.Random, world: dict, index: int) -> dict:
    zone_ids = list(world["zone_ids"])
    rng.shuffle(zone_ids)
    blocked = set(zone_ids[: rng.randint(1, 3)])
    rest = [z for z in zone_ids if z not in blocked]
    unsurveyed = set(rest[: rng.randint(1, 4)])
    clear = {z for z in zone_ids if z not in blocked and z not in unsurveyed}
    if rng.random() < 0.9:  # Ensure most synthetic scenarios include a reachable clear route.
        clear.add(ENTRANCE_ZONE)
        unsurveyed.discard(ENTRANCE_ZONE)
        blocked.discard(ENTRANCE_ZONE)
    route = _reachable_clear(world, clear)
    berths = sorted(z for z in route if z in world["berth_zones"])
    surveyed = len(zone_ids) - len(unsurveyed) - len(blocked)

    down = set()
    roll = rng.random()
    if roll < 0.10:
        down = set(rng.sample(world["buoy_ids"], k=2))
    elif roll < 0.30:
        down = {rng.choice(world["buoy_ids"])}
    ok_buoys = [b for b in world["buoy_ids"] if b not in down]

    def _state(zid: str) -> str:
        if zid in blocked:
            return "blocked"
        if zid in unsurveyed:
            return "unsurveyed"
        return "clear"

    return _trim(
        {
            "kind": "disaster",
            "t": _round(rng.uniform(60, 1800), 1),
            "mode": "disaster",
            "network": "offline" if rng.random() < 0.15 else "online",
            "reopen_plan": {
                "route_zone_ids": sorted(route),
                "reopen_berth_zone_ids": berths,
                "unsurveyed_zone_ids": sorted(unsurveyed),
                "blocked_zone_ids": sorted(blocked),
                "est_hours_saved": _round(surveyed * SURVEY_H, 1),
            },
            "buoys": {"ok": len(ok_buoys), "ok_ids": ok_buoys, "down": sorted(down)},
            "zones": [
                {
                    "id": z["id"],
                    "state": _state(z["id"]),
                    "coverage": _round(1.0 if _state(z["id"]) == "clear" else rng.uniform(0.0, 0.5)),
                }
                for z in world["zones"]
            ],
            "options": [],
            "ranked": [],
            "recent_logs": [
                f"分区 {zid} 勘测完成，可复航" for zid in sorted(clear)[:3]
            ]
            + [f"分区 {zid} 阻塞，禁航" for zid in sorted(blocked)[:2]],
        }
    )


def _buoy_context(rng: random.Random, world: dict, index: int) -> dict:
    target_id = rng.choice(world["buoy_ids"])
    target = next(b for b in world["buoys"] if b["id"] == target_id)
    # Demo scenarios have few simultaneous offline buoys (B has two); add at most one
    # to avoid too many IDs exceeding teacher uncertainty limits.
    others = [b for b in world["buoy_ids"] if b != target_id]
    extra_down = {rng.choice(others)} if rng.random() < 0.12 else set()
    down = {target_id, *extra_down}
    ok_buoys = [b for b in world["buoy_ids"] if b not in down]

    affected = sorted(
        feature["properties"]["id"]
        for feature in world["features"]
        if feature.get("properties", {}).get("id") and _zone_in_range(target, feature)
    )
    remaining = {
        zone_id: sorted(
            b["id"]
            for b in world["buoys"]
            if b["id"] in ok_buoys
            and any(
                f.get("properties", {}).get("id") == zone_id and _zone_in_range(b, f)
                for f in world["features"]
            )
        )
        for zone_id in affected
    }
    return _trim(
        {
            "kind": "buoy",
            "t": _round(rng.uniform(30, 1500), 1),
            "mode": "security" if rng.random() < 0.7 else "disaster",
            "network": "offline" if rng.random() < 0.10 else "online",
            "buoy": {"id": target_id, "status": "down", "range_m": target["range_m"]},
            "buoys": {"ok": len(ok_buoys), "ok_ids": ok_buoys, "down": sorted(down)},
            "coverage_impact": {
                "method": "buoy_range_intersects_zone_geometry",
                "affected_zone_ids": affected,
                "remaining_ok_buoy_ids_by_zone": remaining,
            },
            "zones": [
                {
                    "id": z["id"],
                    "state": "open",
                    "coverage": _round(rng.uniform(0.4, 1.0)),
                }
                for z in world["zones"]
                if z["id"] in affected
            ],
            "options": [],
            "ranked": [],
            "recent_logs": [f"浮标 {target_id} 心跳丢失，状态 down"],
        }
    )


def kind_counts(n: int) -> dict[str, int]:
    """Allocate ratios to exactly n records, assigning the remainder to security."""
    counts = {kind: int(n * ratio) for kind, ratio in KIND_RATIOS}
    counts["security"] += n - sum(counts.values())
    return counts


def generate_contexts(n: int = 500, seed: int = 0, world: dict | None = None) -> list[dict]:
    """Generate n contexts; identical seeds produce identical results."""
    if n < 1:
        raise ValueError("n must be a positive integer")
    rng = random.Random(seed)
    world = world or load_world()
    counts = kind_counts(n)
    kinds = ["security"] * counts["security"] + ["disaster"] * counts["disaster"] + ["buoy"] * counts["buoy"]
    rng.shuffle(kinds)

    builders = {
        "security": _security_context,
        "disaster": _disaster_context,
        "buoy": _buoy_context,
    }
    contexts = []
    for index, kind in enumerate(kinds, start=1):
        context = builders[kind](rng, world, index)
        if context.get("kind") != kind:  # Defensive check: builder output matches allocation.
            raise ValueError(f"Context kind mismatch: expected {kind}, actual {context.get('kind')}")
        size = len(json.dumps(context, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
        if size > MAX_CONTEXT_BYTES:
            raise ValueError(f"Context {index} is {size} bytes after trimming, exceeds {MAX_CONTEXT_BYTES}")
        contexts.append(context)
    return contexts


def write_jsonl(contexts: list[dict], out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as stream:
        for context in contexts:
            stream.write(
                json.dumps(context, ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n"
            )


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate C4 distillation JSONL matching C3 context schema")
    parser.add_argument("--n", type=int, default=500, help="Record count (default500)")
    parser.add_argument("--seed", type=int, default=0, help="Random seed (default0)")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="Output JSONL path")
    args = parser.parse_args()

    contexts = generate_contexts(n=args.n, seed=args.seed)
    write_jsonl(contexts, args.out)

    counts = {"security": 0, "disaster": 0, "buoy": 0}
    network_offline = 0
    sizes = []
    covering_weak = 0
    conf_weak = 0
    down_buoy_ctx = 0
    no_options = 0
    for context in contexts:
        counts[context["kind"]] += 1
        network_offline += context.get("network") == "offline"
        sizes.append(len(json.dumps(context, ensure_ascii=False, separators=(",", ":")).encode("utf-8")))
        if context["kind"] != "security":
            continue
        buoys = context["buoys"]
        covering_weak += len(buoys["covering_track"]) <= 1
        down_buoy_ctx += bool(buoys["down"])
        track = context["track"] or {}
        conf_weak += (track.get("conf") is None) or (track.get("conf", 1.0) < 0.6)
        no_options += not context["options"]

    print(f"Wrote {len(contexts)} contexts -> {args.out}")
    print(
        "Kind distribution: "
        + ", ".join(f"{kind} {count} ({count / len(contexts):.0%})" for kind, count in counts.items())
    )
    print(f"network offline: {network_offline} ({network_offline / len(contexts):.0%})")
    print(
        "Security samples: no options "
        f"{no_options}/{counts['security']}, coverage<=1 {covering_weak}/{counts['security']}, "
        f"confidence<0.6 {conf_weak}/{counts['security']}, offline buoys {down_buoy_ctx}/{counts['security']}"
    )
    print(f"Bytes: min {min(sizes)} / median {sorted(sizes)[len(sizes) // 2]} / max {max(sizes)} (limit {MAX_CONTEXT_BYTES})")


if __name__ == "__main__":
    main()
