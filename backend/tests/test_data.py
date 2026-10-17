import json
from collections import deque

import yaml
from shapely.geometry import LineString, Point, shape
from shapely.ops import unary_union

from backend.app import config


def read(name):
    return json.loads((config.DATA_DIR / name).read_text(encoding="utf-8"))


def test_polygons_metadata_and_symmetric_navigation_graph():
    features = read("zones.geojson")["features"]
    by_id = {feature["properties"]["id"]: feature for feature in features}
    assert len(features) >= 12
    assert len(by_id) == len(features)
    counts = {kind: sum(feature["properties"]["kind"] == kind for feature in features)
              for kind in ["berth", "channel", "anchorage"]}
    assert counts["berth"] >= 6 and counts["channel"] >= 4 and counts["anchorage"] >= 1
    for feature in features:
        props, polygon = feature["properties"], shape(feature["geometry"])
        assert polygon.is_valid and not polygon.is_empty and polygon.area > 0
        assert 0 <= props["sensitivity"] <= 1
        assert props["berths"] >= 0
        for adjacent in props["neighbors"]:
            assert props["id"] in by_id[adjacent]["properties"]["neighbors"]


def test_entrance_reaches_every_berth_through_channels():
    by_id = {feature["properties"]["id"]: feature["properties"]
             for feature in read("zones.geojson")["features"]}
    entrance = next(key for key, props in by_id.items() if props["entrance"])
    queue, reached = deque([entrance]), {entrance}
    while queue:
        current = queue.popleft()
        for neighbor in by_id[current]["neighbors"]:
            if neighbor in reached:
                continue
            reached.add(neighbor)
            if by_id[neighbor]["kind"] == "channel":
                queue.append(neighbor)
    assert all(key in reached for key, props in by_id.items() if props["kind"] == "berth")


def test_buoys_are_in_schematic_water_and_assets_in_berths():
    features = read("zones.geojson")["features"]
    water = [shape(feature["geometry"]) for feature in features]
    berths = [shape(feature["geometry"]) for feature in features if feature["properties"]["kind"] == "berth"]
    buoys, assets = read("buoys.json"), read("assets.json")
    assert [buoy["id"] for buoy in buoys] == [f"B{i}" for i in range(1, 11)]
    for buoy in buoys:
        assert buoy["range_m"] == 600
        assert any(polygon.covers(Point(buoy["lon"], buoy["lat"])) for polygon in water)
    assert 4 <= len(assets) <= 6
    for asset in assets:
        assert asset["rings_m"] == [1500, 800, 400]
        assert any(polygon.contains(Point(asset["lon"], asset["lat"])) for polygon in berths)


def test_fictional_schedules_and_frontend_data_are_consistent():
    vessels = read("vessels.json")
    berth_ids = {feature["properties"]["id"] for feature in read("zones.geojson")["features"]
                 if feature["properties"]["kind"] == "berth"}
    assert len(vessels) == 40 and len({vessel["id"] for vessel in vessels}) == 40
    assert all(vessel["name"].startswith("MV HARBOR") and vessel["zone_id"] in berth_ids
               and 0 <= vessel["t_h"] <= 6
               and vessel["movement"] in {"arrive", "depart", "at_berth"} for vessel in vessels)
    # A #11 intentionally uses proposed stations for offline demos. Those are
    # not B observations; do not relocate LIVE buoys to match the proposal.
    # A's check:sonar verifies its proposal/fallback/replays and no relocation.
    for name in ["zones.geojson", "assets.json", "vessels.json"]:
        assert (config.DATA_DIR / name).read_bytes() == (config.ROOT / "frontend/public/data" / name).read_bytes()


def test_live_buoys_keep_canonical_B_coordinates_when_frontend_has_a_proposal(client):
    from backend.app.models import Buoy

    expected = read("buoys.json")
    proposed = json.loads((config.ROOT / "frontend/public/data/buoys.json").read_text(encoding="utf-8"))
    assert {b["id"] for b in proposed} == {b["id"] for b in expected}
    for buoy in proposed:
        Buoy.model_validate({**buoy, "status": "ok", "pinging": False})

    def check_live():
        actual = client.get("/api/buoys").json()
        assert [{key: buoy[key] for key in ("id", "lat", "lon", "range_m")} for buoy in actual] == expected
        assert client.get("/api/state").json()["buoys"] == actual

    check_live()
    assert client.post("/api/scenario/a/start", json={"speed": 10}).status_code == 200
    check_live()


def test_scripted_uuv_and_vessel_routes_stay_in_schematic_water():
    # Tiny buffer permits WGS84 serialization rounding at shared boundaries.
    water = unary_union([shape(feature["geometry"]) for feature in read("zones.geojson")["features"]]).buffer(1e-8)
    scenario = yaml.safe_load((config.DATA_DIR / "scenarios/scenario_a.yaml").read_text(encoding="utf-8"))
    for target in scenario["targets"]:
        if target["cls"] not in {"uuv", "vessel"}:
            continue
        route = target.get("waypoints") or scenario["routes"][target["route"]]
        coordinates = [(point[1], point[0]) for point in route]
        if target["cls"] == "vessel":
            coordinates.append(coordinates[0])
        assert water.covers(LineString(coordinates)), target["id"]
