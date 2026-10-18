import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from backend.app.main import create_app


def test_websocket_and_rest_share_exact_origins(monkeypatch):
    public = "https://harborguard-cyan.vercel.app"
    local = "http://127.0.0.1:5180"
    monkeypatch.setenv("ALLOWED_ORIGINS", f" {public}, {local} ")
    with TestClient(create_app(run_loop=False, debug_truth=False, storage_path=":memory:")) as client:
        assert client.app.state.allowed_origins == (public, local)
        for origin in (public, local):
            response = client.get("/api/health", headers={"Origin": origin})
            assert response.headers["access-control-allow-origin"] == origin
            with client.websocket_connect("/ws", headers={"Origin": origin}) as socket:
                assert socket.receive_json()["type"] == "state"
        for origin in ("https://unlisted.vercel.app", public + ".invalid", "null", ""):
            with pytest.raises(WebSocketDisconnect) as failure:
                with client.websocket_connect("/ws", headers={"Origin": origin}):
                    pytest.fail("Unlisted browser origin accepted")
            assert failure.value.code == 1008
        # Agent's native WebSocket client has no browser Origin header.
        with client.websocket_connect("/ws") as socket:
            assert socket.receive_json()["type"] == "state"
        assert len(client.app.state.engine.bus.connections) == 0
