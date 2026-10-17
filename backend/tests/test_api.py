import asyncio
import time

import httpx
from fastapi.testclient import TestClient

from backend.app.main import create_app
from backend.app.models import EventMsg, StateMsg


def test_incomplete_model_metrics_are_null_instead_of_a_server_error(client,tmp_path,monkeypatch):
    from backend.app import config

    for kind in ("yolo","lora"):
        (tmp_path/"ml"/kind).mkdir(parents=True)
    (tmp_path/"ml/yolo/metrics.json").write_text('{"precision":NaN}',encoding="utf-8")
    (tmp_path/"ml/lora/metrics.json").write_text('{"loss":0.1}',encoding="utf-8")
    monkeypatch.setattr(config,"ROOT",tmp_path)
    response = client.get("/api/metrics")
    assert response.status_code == 200
    assert response.json() == {"yolo":None,"lora":{"loss":0.1}}


def test_controls_faults_and_reset(client):
    assert client.post("/api/control",json={"action":"resume"}).status_code == 409
    assert client.post("/api/scenario/a/start",json={"speed":4}).json() == {"ok":True}
    game = client.app.state.engine
    game.step(.4)
    assert game.world.t == .4
    client.post("/api/control",json={"action":"pause"})
    game.step(1)
    assert game.world.t == .4
    client.post("/api/control",json={"action":"resume"})
    client.post("/api/control",json={"action":"speed","value":10})
    assert game.world.speed == 10
    for kind,target in (("buoy_down","B4"),("network_down",None),("noise_up",None)):
        assert client.post("/api/inject",json={"type":kind,"target":target}).status_code == 200
    state = client.get("/api/state").json()
    assert state["network"] == "offline"
    assert next(b for b in state["buoys"] if b["id"] == "B4")["status"] == "down"
    assert game.world.noise_up
    for kind,target in (("buoy_up","B4"),("network_up",None),("noise_down",None)):
        assert client.post("/api/inject",json={"type":kind,"target":target}).status_code == 200
    client.post("/api/mode",json={"mode":"disaster"})
    assert all(z["state"] == "unsurveyed" for z in client.get("/api/state").json()["zones"])
    client.post("/api/log",json={"level":"warn","source":"agent","text":"test"})
    assert client.get("/api/log?limit=1").json()[0]["text"] == "test"
    client.post("/api/control",json={"action":"reset"})
    state = client.get("/api/state").json()
    assert state["scenario"] is None and state["t"] == 0 and state["tracks"] == []
    assert state["network"] == "online" and state["mode"] == "security"
    assert all(b["status"] == "ok" for b in state["buoys"])


def test_agent_proxy_success_failure_timeout(client):
    async def success(request):
        return httpx.Response(200,json={"answer":"received","model":"template"})

    async def refused(request):
        raise httpx.ConnectError("refused",request=request)

    async def timeout(request):
        raise httpx.ReadTimeout("timeout",request=request)

    for handler,status in ((success,200),(refused,502),(timeout,504)):
        previous = client.app.state.agent_client
        asyncio.run(previous.aclose())
        client.app.state.agent_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        response = client.post("/api/agent/ask",json={"question":"status?","track_id":None})
        assert response.status_code == status
        if status != 200:
            assert "Agent" in response.json()["detail"]
        assert client.get("/api/health").json() == {"ok":True}


def test_decision_endpoint_requires_valid_human_approval(seeded_client):
    game = seeded_client.app.state.engine
    choice = {"alert_id":"A1","option_id":"opt-1","action":"reject","operator":"demo"}
    assert seeded_client.post("/api/decision",json=choice).json() == {"ok":True}
    assert not any(zone["state"] == "restricted" for zone in game.decision.zone_statuses.values())
    assert seeded_client.post("/api/decision",json={**choice,"option_id":"missing"}).status_code == 409
    choice["action"] = "approve"
    assert seeded_client.post("/api/decision",json=choice).json() == {"ok":True}
    state = seeded_client.get("/api/state").json()
    assert next(z for z in state["zones"] if z["id"] == "berth_container_1")["state"] == "restricted"
    seeded_client.post("/api/control",json={"action":"reset"})
    assert seeded_client.post("/api/decision",json=choice).status_code == 409


def test_websocket_rate_sequence_and_disconnect_cleanup():
    with TestClient(create_app()) as client:
        with client.websocket_connect("/ws") as ws:
            sequence, received = [], []
            for _ in range(7):
                msg = ws.receive_json()
                StateMsg.model_validate(msg)
                sequence.append(msg["seq"])
                received.append(time.monotonic())
            assert all(a < b for a,b in zip(sequence,sequence[1:],strict=False))
            # Initial snapshot is immediate; following snapshots are 5Hz.
            average = (received[-1]-received[1])/5
            assert .14 < average < .35, average
        assert len(client.app.state.engine.bus.connections) == 0


def test_websocket_event_forwarding(client):
    with client.websocket_connect("/ws") as ws:
        StateMsg.model_validate(ws.receive_json())
        client.post("/api/inject",json={"type":"network_down"})
        msg = ws.receive_json()
        EventMsg.model_validate(msg)
        assert msg["event"] == "network_changed" and msg["data"]["network"] == "offline"
