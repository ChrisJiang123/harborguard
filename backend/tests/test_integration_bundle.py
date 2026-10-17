"""Keep the frontend handoff complete and compatible with the frozen routes."""
import json
from io import BytesIO

from PIL import Image

from backend.app import config
from backend.app.main import create_app
from backend.app.models import EventMsg, StateMsg
from backend.tools.integration_bundle import build_bundle


def test_bundle_covers_every_rest_operation_and_preserves_live_schema():
    openapi, bundle = build_bundle()
    expected = {(method.upper(), path) for path, methods in openapi["paths"].items()
                for method in methods if method in {"get", "post"}}
    actual = {(item["method"], item["route"]) for item in bundle["rest"]}
    assert actual == expected
    assert len(actual) == 21
    StateMsg.model_validate(bundle["state"])
    for event in bundle["events"] + bundle["event_catalogue"]:
        EventMsg.model_validate(event)
    assert all(event["seq"] <= bundle["state"]["seq"] for event in bundle["events"])
    assert {item["status"] for item in bundle["errors"]} == {404, 409, 422}
    track = next(track for track in bundle["state"]["tracks"] if track["id"] == "T1")
    assert track["detection_id"] == "det-1"
    assert any(event["data"].get("detection", {}).get("id") == track["detection_id"]
               for event in bundle["events"])


def test_committed_frontend_mock_and_openapi_are_current():
    openapi, generated = build_bundle()
    committed = json.loads((config.ROOT / "frontend/public/mock/backend.json").read_text(encoding="utf-8"))
    assert committed == generated
    assert json.loads((config.ROOT / "docs/integration/openapi.json").read_text(encoding="utf-8")) == openapi
    assert create_app(run_loop=False).openapi() == openapi
    for url in committed["mock_images"].values():
        image = config.ROOT / "frontend/public" / url.lstrip("/")
        with Image.open(BytesIO(image.read_bytes())) as png:
            assert png.format == "PNG" and png.size == (640, 640)
