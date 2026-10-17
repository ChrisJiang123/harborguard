import pytest
from fastapi.testclient import TestClient

from backend.app.main import create_app


@pytest.fixture
def client():
    with TestClient(create_app(run_loop=False, debug_truth=False, storage_path=":memory:")) as test_client:
        yield test_client


@pytest.fixture
def seeded_client(client):
    from backend.app.perception.classifier import SonarClassifier
    from backend.tools.make_samples import samples

    state, events = samples()
    game = client.app.state.engine
    game.start("a", 10)
    game._tracks = state["tracks"]
    alert = state["alerts"][0]
    game.decision.alerts[alert["id"]] = alert
    for msg in events:
        if msg["event"] == "options_ready":
            game.decision.options[alert["id"]] = msg["data"]
        if msg["event"] == "detection":
            detection = msg["data"]["detection"]
            game.decision.detections[detection["id"]] = detection
            game.decision.images[detection["id"]] = SonarClassifier().classify([],42)["image"]
        game.emit(msg["event"],msg["data"])
    return client
