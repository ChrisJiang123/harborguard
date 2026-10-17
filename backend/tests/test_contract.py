import re
from io import BytesIO

import pytest
from PIL import Image
from pydantic import TypeAdapter, ValidationError

from backend.app.models import (
    EVENT_DATA,
    Alert,
    Asset,
    Buoy,
    Detection,
    EventMsg,
    LogEntry,
    Metrics,
    Ok,
    OptionsPayload,
    Recommendation,
    StateMsg,
    Track,
    ZoneCollection,
)
from backend.tools.make_samples import samples


def test_upstream_c_contract_has_the_same_frozen_types():
    from backend.app.config import ROOT

    upstream = (ROOT/"docs/shared-contract-v1.md").read_text(encoding="utf-8")
    block = re.search(r"```(?:ts|typescript)\s*\n(.*?)```",upstream,re.DOTALL)
    assert block is not None
    local = (ROOT/"shared/types.ts").read_text(encoding="utf-8")

    def tokens(source):
        return re.sub(r"\s+","",re.sub(r"//[^\n]*","",source))

    assert tokens(block.group(1)) == tokens(local)


def test_all_contract_get_endpoints(seeded_client):
    expectations = {
        "/api/health":Ok, "/api/state":StateMsg, "/api/events?since_seq=0":list[EventMsg],
        "/api/zones":ZoneCollection, "/api/assets":list[Asset], "/api/buoys":list[Buoy],
        "/api/tracks/T1":Track, "/api/alerts/A1":Alert, "/api/detections/det-1":Detection,
        "/api/options/A1":OptionsPayload, "/api/log?limit=100":list[LogEntry], "/api/metrics":Metrics,
    }
    for path, schema in expectations.items():
        response = seeded_client.get(path)
        assert response.status_code == 200, (path,response.text)
        TypeAdapter(schema).validate_python(response.json())
    response = seeded_client.get("/api/sonar/det-1.png")
    assert response.headers["content-type"] == "image/png"
    with Image.open(BytesIO(response.content)) as image:
        assert image.size == (640,640)


def test_samples_cover_every_event_and_are_valid():
    state, events = samples()
    StateMsg.model_validate(state)
    assert {msg["event"] for msg in events} == set(EVENT_DATA)
    for msg in events:
        EventMsg.model_validate(msg)
    assert len(state["tracks"]) == 2
    assert len(next(msg for msg in events if msg["event"] == "options_ready")["data"]["options"]) == 3


def test_contract_rejects_wrong_fields_event_data_and_nonfinite():
    state, events = samples()
    state["simulation_time"] = state.pop("t")
    with pytest.raises(ValidationError):
        StateMsg.model_validate(state)
    with pytest.raises(ValidationError):
        EventMsg(type="event",seq=1,t=0,event="zone_changed",data={"zone":"x","state":"open"})
    with pytest.raises(ValidationError):
        EventMsg(type="event",seq=1,t=float("nan"),event="network_changed",data={"network":"online"})
    recommendation = next(msg for msg in events if msg["event"] == "recommendation")["data"]["recommendation"]
    recommendation["summary"] = "测"*61
    with pytest.raises(ValidationError):
        Recommendation.model_validate(recommendation)


def test_missing_resources_and_invalid_requests(client):
    for kind in ("tracks","alerts","detections","options"):
        assert client.get(f"/api/{kind}/does-not-exist").status_code == 404
    assert client.get("/api/sonar/missing.png").status_code == 404
    assert client.post("/api/scenario/c/start",json={}).status_code == 404
    assert client.post("/api/control",json={"action":"speed"}).status_code == 422
    assert client.post("/api/control",json={"action":"speed","value":0}).status_code == 422
    assert client.post("/api/inject",json={"type":"buoy_down"}).status_code == 422
    assert client.post("/api/inject",json={"type":"buoy_down","target":"missing"}).status_code == 404
    assert client.post("/api/recommendations",json={"summary":"invalid"}).status_code == 422


def test_recommendation_validates_references_and_broadcasts(seeded_client):
    _, events = samples()
    recommendation = next(msg for msg in events if msg["event"] == "recommendation")["data"]["recommendation"]
    assert seeded_client.post("/api/recommendations",json=recommendation).json() == {"ok":True}
    latest = seeded_client.get("/api/events").json()[-1]
    assert latest["event"] == "recommendation"
    assert latest["data"]["recommendation"]["id"] == recommendation["id"]
    recommendation["evidence_ids"] = ["nonexistent"]
    assert seeded_client.post("/api/recommendations",json=recommendation).status_code == 422
    recommendation["evidence_ids"] = []
    recommendation["recommended_option_id"] = "invalid"
    assert seeded_client.post("/api/recommendations",json=recommendation).status_code == 422


def test_cors_and_static_data(client):
    response = client.options("/api/control",headers={"Origin":"http://localhost:5173",
                                                      "Access-Control-Request-Method":"POST"})
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert len(client.get("/api/zones").json()["features"]) >= 12
    assert len(client.get("/api/buoys").json()) == 10
