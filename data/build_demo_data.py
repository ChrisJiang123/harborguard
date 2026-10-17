"""Regenerate the deliberately schematic demo fixtures and frontend copies.

Run from the repository root: python data/build_demo_data.py
This is synthetic scenario design, not chart digitization. See data/README.md.
"""
import json
import sys
from pathlib import Path

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.app.geo import to_geo  # noqa: E402

DATA = ROOT / "data"
FRONTEND = ROOT / "frontend" / "public" / "data"


def geo_point(x, y, depth=None):
    lat, lon = to_geo(x, y)
    return [round(lat, 10), round(lon, 10)] + ([] if depth is None else [depth])


def rectangle(x0, y0, x1, y1):
    return [[geo_point(x, y)[::-1] for x, y in
             [(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)]]]


def main():
    DATA.mkdir(exist_ok=True)
    FRONTEND.mkdir(parents=True, exist_ok=True)
    neighbors = {
        "channel_entrance": ["channel_main_s", "anchorage_outer", "anchorage_north"],
        "channel_main_s": ["channel_entrance", "channel_main_n", "berth_container_1"],
        "channel_main_n": ["channel_main_s", "channel_turning", "berth_container_1"],
        "channel_turning": ["channel_main_n", "berth_container_2", "berth_container_3",
                            "berth_fuel", "berth_cruise", "berth_bulk"],
        "berth_container_1": ["channel_main_s", "channel_main_n"],
        "berth_container_2": ["channel_turning"],
        "berth_container_3": ["channel_turning"],
        "berth_fuel": ["channel_turning"],
        "berth_cruise": ["channel_turning"],
        "berth_bulk": ["channel_turning"],
        "anchorage_outer": ["channel_entrance", "anchorage_north"],
        "anchorage_north": ["channel_entrance", "anchorage_outer"],
    }
    entries = [
        ("channel_entrance", "演示入口航道", "channel", .6, 0, (-1200, -1750, -700, -1050)),
        ("channel_main_s", "演示主航道南段", "channel", .6, 0, (-700, -1450, -150, -1000)),
        ("channel_main_n", "演示主航道北段", "channel", .6, 0, (-350, -1000, -150, -550)),
        ("channel_turning", "演示掉头水域", "channel", .6, 0, (-350, -550, 250, 150)),
        ("berth_container_1", "演示集装箱泊位一", "berth", .7, 3, (-150, -1125, 150, -900)),
        ("berth_container_2", "演示集装箱泊位二", "berth", .7, 2, (-650, -550, -350, -300)),
        ("berth_container_3", "演示集装箱泊位三", "berth", .7, 2, (-350, 150, -50, 450)),
        ("berth_fuel", "演示液体散货泊位", "berth", 1., 2, (250, -550, 550, -250)),
        ("berth_cruise", "演示邮轮泊位", "berth", .9, 2, (-50, 150, 250, 450)),
        ("berth_bulk", "演示杂货泊位", "berth", .7, 1, (-650, -300, -350, 150)),
        ("anchorage_outer", "演示外侧锚地", "anchorage", .3, 0, (-2200, -2050, -1000, -1450)),
        ("anchorage_north", "演示北侧锚地", "anchorage", .3, 0, (-1900, -1450, -1200, -900)),
    ]
    features = []
    for zid, name, kind, sensitivity, berths, bounds in entries:
        coordinates = rectangle(*bounds)
        if zid == "channel_main_n":
            # A north-side survey pocket, disjoint from the southern berth.
            coordinates = [[geo_point(x, y)[::-1] for x, y in
                            [(-350, -1000), (-150, -1000), (-150, -900), (150, -900),
                             (150, -550), (-350, -550), (-350, -1000)]]]
        elif zid == "anchorage_outer":
            coordinates = [[geo_point(x, y)[::-1] for x, y in
                            [(-2200, -2050), (-1000, -2050), (-1000, -1450), (-1900, -1450),
                             (-1900, -1300), (-2200, -1300), (-2200, -2050)]]]
        features.append({"type": "Feature", "properties": {
            "id": zid, "name": name, "kind": kind, "sensitivity": sensitivity,
            "berths": berths, "neighbors": neighbors[zid], "entrance": zid == "channel_entrance",
        }, "geometry": {"type": "Polygon", "coordinates": coordinates}})
    zones = {"type": "FeatureCollection", "features": features}
    assets = []
    for aid, name, kind, x, y, sensitivity in [
        ("asset_container_1", "演示集装箱码头一", "container_terminal", -50, -1000, .7),
        ("asset_container_2", "演示集装箱码头二", "container_terminal", -500, -400, .7),
        ("asset_container_3", "演示集装箱码头三", "container_terminal", -200, 300, .7),
        ("asset_fuel", "演示燃料码头", "fuel_terminal", 400, -400, 1.),
        ("asset_cruise", "演示邮轮码头", "cruise_terminal", 100, 300, .9),
    ]:
        lat, lon = geo_point(x, y)
        assets.append({"id": aid, "name": name, "kind": kind, "lat": lat, "lon": lon,
                       "sensitivity": sensitivity, "rings_m": [1500, 800, 400]})
    buoy_positions = [(-2150, -1400), (-1700, -1450), (-1250, -1350), (-800, -1100),
                      (-350, -900), (100, -700), (-100, -350), (100, -980),
                      (-500, -400), (350, -400)]
    buoys = []
    for index, (x, y) in enumerate(buoy_positions, 1):
        lat, lon = geo_point(x, y)
        buoys.append({"id": f"B{index}", "lat": lat, "lon": lon, "range_m": 600})
    rng = np.random.default_rng(2026)
    berth_ids = [row[0] for row in entries if row[2] == "berth"]
    vessels = [{"id": f"V{i:02}", "name": f"MV HARBOR {i:02}", "zone_id": berth_ids[(i - 1) % 6],
                "movement": ["arrive", "depart", "at_berth"][(i - 1) % 3],
                "t_h": round(float(rng.uniform(0, 6)), 2)} for i in range(1, 41)]
    for name, data in [("zones.geojson", zones), ("assets.json", assets),
                       ("buoys.json", buoys), ("vessels.json", vessels)]:
        content = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
        (DATA / name).write_text(content, encoding="utf-8")
        (FRONTEND / name).write_text(content, encoding="utf-8")
    scenario_a = {
        "id": "a", "seed": 42, "mode": "security", "duration_s": 1200, "default_speed": 10,
        "routes": {"channel_main": [geo_point(x, y, 0) for x, y in
                    [(-1050, -1500), (-500, -1250), (-250, -900), (-200, -350),
                     (-250, -900), (-500, -1250)]]},
        "targets": [
            {"id": "uuv1", "cls": "uuv", "speed_mps": 2.0,
             "waypoints": [geo_point(x, y, 12) for x, y in
                           [(-2010, -1750), (-1600, -1750), (-50, -1000)]]},
            {"id": "fish1", "cls": "fish_school", "center": geo_point(-1700, -1100), "radius_m": 120},
            {"id": "fish2", "cls": "fish_school", "center": geo_point(-1050, -1450), "radius_m": 100},
            {"id": "ship1", "cls": "vessel", "route": "channel_main", "speed_mps": 4.0},
            {"id": "ship2", "cls": "vessel", "speed_mps": 5.0,
             "waypoints": [geo_point(x, y, 0) for x, y in
                           [(-150, -350), (-250, -900), (-500, -1250), (-1050, -1500),
                            (-500, -1250), (-250, -900)]]},
            {"id": "ship3", "cls": "vessel", "speed_mps": 6.0,
             "waypoints": [geo_point(x, y, 0) for x, y in
                           [(-650, -1300), (-300, -1050), (-200, -800), (-200, -600), (-100, -350),
                            (-200, -600), (-200, -800), (-300, -1050)]]},
            {"id": "mm1", "cls": "marine_mammal", "center": geo_point(1800, -2400)},
        ],
        "events": [{"t": 0, "type": "log", "text": "场景 A 开始：示意港区 UUV 接近受保护资产"}],
    }
    scenario_b = {
        "id": "b", "seed": 7, "mode": "disaster", "duration_s": 600, "default_speed": 10,
        "targets": [{"id": f"debris{i}", "cls": "debris", "center": geo_point(x, y), "drift": False}
                    for i, (x, y) in enumerate([(-220, -800), (0, -350), (350, -400), (-1550, -1250)], 1)],
        "events": [{"t": 0, "type": "log", "text": "场景 B 开始：灾后分区勘测与复航评估"},
                   {"t": 60, "type": "buoy_down", "target": "B4"},
                   {"t": 60, "type": "buoy_down", "target": "B7"}],
    }
    (DATA / "scenarios").mkdir(exist_ok=True)
    for scenario in (scenario_a, scenario_b):
        content = "# Synthetic demonstration geometry; see ../README.md.\n"
        content += yaml.safe_dump(scenario, allow_unicode=True, sort_keys=False)
        (DATA / "scenarios" / f"scenario_{scenario['id']}.yaml").write_text(content, encoding="utf-8")


if __name__ == "__main__":
    main()
