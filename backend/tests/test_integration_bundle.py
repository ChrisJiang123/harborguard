"""Keep the frontend handoff complete and compatible with the frozen routes."""
import json
from io import BytesIO
from pathlib import Path

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


def test_committed_B_mock_and_openapi_are_current():
    openapi, generated = build_bundle()
    directory = config.ROOT / "backend/fixtures/integration"
    committed = json.loads((directory / "backend.json").read_text(encoding="utf-8"))
    assert committed == generated
    assert json.loads((config.ROOT / "docs/integration/openapi.json").read_text(encoding="utf-8")) == openapi
    assert create_app(run_loop=False).openapi() == openapi
    for url in committed["mock_images"].values():
        image = directory / url
        with Image.open(BytesIO(image.read_bytes())) as png:
            assert png.format == "PNG" and png.size == (640, 640)


def test_export_cannot_touch_configured_live_database_or_frontend(tmp_path, monkeypatch):
    from backend.tools.integration_bundle import export

    database = tmp_path / "live.sqlite3"
    database.write_bytes(b"existing demo database sentinel")
    monkeypatch.setenv("HARBORGUARD_DB", str(database))
    frontend = tmp_path / "frontend/public/mock/backend.json"
    frontend.parent.mkdir(parents=True)
    frontend.write_text("A-owned sentinel", encoding="utf-8")
    paths = [p.relative_to(tmp_path).as_posix() for p in map(Path, export(tmp_path))]
    assert database.read_bytes() == b"existing demo database sentinel"
    assert frontend.read_text(encoding="utf-8") == "A-owned sentinel"
    assert set(paths) == {"docs/integration/openapi.json", "backend/fixtures/integration/backend.json",
                          "backend/fixtures/integration/sonar/det-1.png"}
    assert not database.with_suffix(".sqlite3.lock").exists()


def test_structured_reject_and_approve_examples_are_ordered_and_distinct():
    _, bundle = build_bundle()
    events = bundle["decision_examples"]
    assert [event["data"]["action"] for event in events] == ["reject", "approve"]
    assert events[0]["seq"] < events[1]["seq"]
    assert events[0]["t"] == events[1]["t"]
    for event in events:
        EventMsg.model_validate(event)
