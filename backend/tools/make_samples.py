"""Generate complete, validated contract fixtures for A and C, without running the simulator."""
import json

from backend.app.config import DATA_DIR, ROOT
from backend.app.geo import to_geo, to_local
from backend.app.models import EventMsg, StateMsg


def samples():
    zones = json.loads((DATA_DIR / "zones.geojson").read_text(encoding="utf-8"))["features"]
    assets = json.loads((DATA_DIR / "assets.json").read_text(encoding="utf-8"))
    buoys = json.loads((DATA_DIR / "buoys.json").read_text(encoding="utf-8"))
    vessels = json.loads((DATA_DIR / "vessels.json").read_text(encoding="utf-8"))
    protected = next(a for a in assets if a["id"] == "asset_container_1")
    ax, ay = to_local(protected["lat"], protected["lon"])
    lat, lon = to_geo(ax, ay-200)
    previous_lat, previous_lon = to_geo(ax, ay-320)
    predicted_lat, predicted_lon = to_geo(ax, ay-140)
    track = dict(
        id="T1", status="confirmed", cls="uuv", conf=0.85, cue="narrowband", lat=lat,
        lon=lon, depth_m=12, vel_e=0, vel_n=2, vel_d=0, speed_mps=2, heading_deg=0,
        err={"a_m": 25, "b_m": 15, "angle_deg": 0},
        history=[[previous_lat, previous_lon, 12, 60], [lat, lon, 12, 120]],
        predicted=[[predicted_lat, predicted_lon, 12, 150]], level=3, risk=0.867, detection_id="det-1",
    )
    vessel = {**track, "id": "T2", "cls": "vessel", "cue": "broadband", "depth_m": 0,
              "level": 0, "risk": 0, "detection_id": None}
    vessel["history"] = [[p[0],p[1],0,p[3]] for p in vessel["history"]]
    vessel["predicted"] = [[p[0],p[1],0,p[3]] for p in vessel["predicted"]]
    alert = dict(id="A1", track_id="T1", level=3, risk=0.867,
                 breakdown={"C": .94, "P": .9, "B": 1, "Z": .6, "D": .4}, zone_id="channel_main_s",
                 asset_id="asset_container_1", distance_m=200, eta_s=100,
                 raised_t=60, updated_t=120, options_ready=True)
    options = [
        dict(id="opt-1", label="最小封闭", is_baseline=False, zones_closed=["berth_container_1"],
             speed_limit_zones=[], berths_open_pct=.85, vessels_affected=2, delay_vessel_hours=4, residual_risk=.1),
        dict(id="opt-2", label="扩大缓冲 + 限速", is_baseline=False,
             zones_closed=["berth_container_1", "channel_main_s"], speed_limit_zones=["channel_entrance"],
             berths_open_pct=.85, vessels_affected=4, delay_vessel_hours=8, residual_risk=0),
        dict(id="port-closure", label="全港关闭", is_baseline=True,
             zones_closed=["berth_container_1", "channel_main_s", "channel_entrance"], speed_limit_zones=[],
             berths_open_pct=0, vessels_affected=40, delay_vessel_hours=240, residual_risk=0),
    ]
    options[-1]["zones_closed"] = [zone["properties"]["id"] for zone in zones]
    berths = {zone["properties"]["id"]:zone["properties"]["berths"] for zone in zones}
    for option in options:
        closed = set(option["zones_closed"])
        duration_h = 6 if option["is_baseline"] else 2
        option["berths_open_pct"] = 1-sum(berths[zid] for zid in closed)/sum(berths.values())
        option["vessels_affected"] = sum(v["zone_id"] in closed and v["movement"] in ("arrive","depart")
                                          and v["t_h"] <= duration_h for v in vessels)
        option["delay_vessel_hours"] = option["vessels_affected"]*duration_h
    recommendation = dict(
        id="rec-sample-1", kind="security", alert_id="A1", model="template", summary="建议审核最小封闭方案",
        explanation="此为契约样例。请结合航迹和风险指标由操作员确认方案。", recommended_option_id="opt-1",
        evidence_ids=["T1", "A1", "det-1"], uncertainties=["演示数据"], confidence="medium", created_t=120,
        latency_ms=0,
    )
    detection = dict(id="det-1", track_id="T1", buoy_id="B1", t=120, cls="uuv", conf=.85,
                     bbox=[200, 250, 300, 300], image_url="/api/sonar/det-1.png", model="stub")
    state = StateMsg(type="state", seq=1, t=120, mode="security", network="online", scenario="a", paused=False,
                     speed=10, buoys=[{**buoy,"status":"ok","pinging":False} for buoy in buoys],
                     tracks=[track,vessel], alerts=[alert],
                     zones=[dict(id=zone["properties"]["id"],state="open",coverage=0) for zone in zones])
    payloads = {
        "alert_raised": {"alert": alert},
        "alert_changed": {"alert": alert, "from_level": 2, "to_level": 3},
        "alert_cleared": {"alert_id": "A1"}, "detection": {"detection": detection},
        "options_ready": {"alert_id": "A1", "options": options, "ranked": [o["id"] for o in options]},
        "recommendation": {"recommendation": recommendation},
        "decision": {"alert_id":"A1", "option_id":"opt-1", "action":"approve", "operator":"demo"},
        "zone_changed": {"zone_id":"channel_main_s", "state":"restricted"},
        "reopen_plan": {"route_zone_ids":["channel_main_s"], "reopen_berth_zone_ids":["berth_container_1"],
                        "unsurveyed_zone_ids":[], "blocked_zone_ids":[], "est_hours_saved":3},
        "buoy_changed": {"buoy_id":"B1", "status":"down"}, "network_changed": {"network":"offline"},
        "mode_changed": {"mode":"disaster"}, "scenario_changed": {"scenario":"a", "status":"started"},
        "log": {"log":{"t":120,"level":"info","source":"sim","text":"契约样例"}},
    }
    events = [EventMsg(type="event",seq=i+2,t=120,event=name,data=data).model_dump(mode="json")
              for i,(name,data) in enumerate(payloads.items())]
    return state.model_dump(mode="json"), events


def main():
    state, events = samples()
    for filename, data in (("sample_state.json", state), ("sample_events.json", events)):
        (ROOT / "shared" / filename).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Generated shared/sample_state.json and shared/sample_events.json")


if __name__ == "__main__":
    main()
