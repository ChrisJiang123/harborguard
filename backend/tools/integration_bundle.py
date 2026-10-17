"""Export existing OpenAPI and executable HTTP examples for frontend integration.

Synthetic business state comes from v1 samples, not a running scenario. Agent
and sonar are explicit fixtures; REST uses real routes and Pydantic validation.
Uses an isolated in-memory DB, never HARBORGUARD_DB or frontend output paths.
"""
import argparse
import asyncio
import copy
import json
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

import httpx
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw

from backend.app import config
from backend.app.main import create_app
from backend.tools.make_samples import samples


def fixture_png():
    """Layout illustration matching the sample box, not a sonar observation."""
    image = Image.new("RGB", (640, 640), (36, 36, 36))
    draw = ImageDraw.Draw(image)
    draw.rectangle([200, 250, 300, 300], fill=(180, 180, 180), outline="lime", width=2)
    buffer = BytesIO()
    image.save(buffer, format="PNG", compress_level=1)
    return buffer.getvalue()


class FixtureClassifier:
    last_error = "Explicit contract fixture; inference not exercised"

    def warmup(self):
        return {"model": "stub", "ms": 0.0}


def build_bundle():
    state, catalogue = samples()
    with patch("backend.app.perception.classifier.SonarClassifier", FixtureClassifier), TestClient(
        create_app(run_loop=False, debug_truth=False, storage_path=":memory:")
    ) as client:
        game = client.app.state.engine
        game.start("a", 10)
        game.world.t = state["t"]
        game._tracks = copy.deepcopy(state["tracks"])
        game.decision.alerts.update({a["id"]: copy.deepcopy(a) for a in state["alerts"]})
        for event in catalogue:
            name, data = event["event"], copy.deepcopy(event["data"])
            if name == "options_ready":
                game.decision.options[data["alert_id"]] = data
            elif name == "detection":
                detection = data["detection"]
                game.decision.detections[detection["id"]] = detection
                game.decision.images[detection["id"]] = fixture_png()
            elif name == "recommendation":
                game.recommendations[data["recommendation"]["alert_id"]] = data["recommendation"]
            if name in {"alert_raised", "detection", "options_ready", "recommendation"}:
                game.emit(name, data)

        asyncio.run(client.app.state.agent_client.aclose())
        client.app.state.agent_client = httpx.AsyncClient(transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json={
                "answer": "这是联调 Mock 回答；请由操作员审核当前方案。", "model": "template",
            })
        ))
        examples = []

        def capture(method, route, path=None, body=None):
            kwargs = {"json": body} if body is not None else {}
            response = client.request(method, path or route, **kwargs)
            response.raise_for_status()
            item = {"method": method, "route": route, "path": path or route,
                    "status": response.status_code}
            if body is not None:
                item["request"] = body
            if response.headers["content-type"].startswith("image/png"):
                item.update(content_type="image/png", asset_url="sonar/det-1.png")
            else:
                item["response"] = response.json()
            examples.append(item)
            return response

        capture("GET", "/api/health")
        snapshot = capture("GET", "/api/state").json()
        events = capture("GET", "/api/events", "/api/events?since_seq=0").json()
        for route in ("zones", "assets", "buoys", "metrics"):
            capture("GET", f"/api/{route}")
        for route, parameter, identifier in (
            ("tracks", "track_id", "T1"), ("alerts", "alert_id", "A1"),
            ("detections", "det_id", "det-1"), ("options", "alert_id", "A1"),
        ):
            capture("GET", f"/api/{route}/{{{parameter}}}", f"/api/{route}/{identifier}")
        capture("GET", "/api/sonar/{det_id}.png", "/api/sonar/det-1.png")
        capture("GET", "/api/log", "/api/log?limit=100")
        recommendation = next(e["data"]["recommendation"] for e in catalogue
                              if e["event"] == "recommendation")
        for path, body in (
            ("/api/recommendations", recommendation),
            ("/api/agent/ask", {"question": "当前风险如何？", "track_id": "T1"}),
            ("/api/decision", {"alert_id": "A1", "option_id": "opt-1",
                               "action": "reject", "operator": "demo"}),
            ("/api/decision", {"alert_id": "A1", "option_id": "opt-1",
                               "action": "approve", "operator": "demo"}),
            ("/api/log", {"level": "info", "source": "agent", "text": "联调 Mock 日志"}),
            ("/api/mode", {"mode": "disaster"}),
            ("/api/inject", {"type": "buoy_down", "target": "B4"}),
            ("/api/control", {"action": "pause"}),
        ):
            capture("POST", path, body=body)
        capture("POST", "/api/scenario/{scenario_id}/start", "/api/scenario/b/start", {"speed": 10})
        # Freeze structured reject/approve examples before the scenario reset.
        decisions = [event for event in game.bus.since(0) if event["event"] == "decision"]
        errors = []
        for method, path, body in (
            ("GET", "/api/tracks/missing", None),
            ("POST", "/api/decision", {"alert_id": "stale", "option_id": "stale",
                                       "action": "approve", "operator": "demo"}),
            ("POST", "/api/control", {"action": "speed"}),
        ):
            response = client.request(method, path, **({"json": body} if body else {}))
            assert response.status_code in (404, 409, 422)
            errors.append({"method": method, "path": path, "status": response.status_code,
                           "request": body, "response": response.json()})
        return client.app.openapi(), {
            "description": "联调静态合成样例，业务态、声呐图和 Agent 回答是显式 fixture；"
                           "REST 经真实路由/Pydantic 验证，不代表仿真、识别或浏览器联调通过。"
                           "state/events 是同一快照；event_catalogue 是独立事件目录，不按序播放。"
                           "这些固定 ID 不可直接用于新的实时场景审批。",
            "state": snapshot, "events": events, "event_catalogue": catalogue,
            "decision_examples": decisions,
            "rest": examples, "errors": errors,
            "mock_images": {"/api/sonar/det-1.png": "sonar/det-1.png"},
        }


def export(root: Path):
    openapi, bundle = build_bundle()
    outputs = ((root / "docs/integration/openapi.json", openapi),
               (root / "backend/fixtures/integration/backend.json", bundle))
    for path, payload in outputs:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    image_path = root / "backend/fixtures/integration/sonar/det-1.png"
    image_path.parent.mkdir(parents=True, exist_ok=True)
    image_path.write_bytes(fixture_png())
    return [str(path) for path, _ in outputs] + [str(image_path)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=config.ROOT, help="Output root; defaults to repository")
    args = parser.parse_args()
    print(json.dumps(export(args.root), ensure_ascii=False))


if __name__ == "__main__":
    main()
