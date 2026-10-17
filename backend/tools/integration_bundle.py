"""Export existing OpenAPI and executable HTTP examples for frontend integration.

Synthetic fixtures come from the existing v1 samples. Only the Agent answer is
mocked; every REST request passes through the real FastAPI routes and validators.
No server, external model, credential, or internet connection is required.
"""
import argparse
import asyncio
import copy
import json
from pathlib import Path

import httpx
from fastapi.testclient import TestClient

from backend.app import config
from backend.app.main import create_app
from backend.tools.make_samples import samples


def build_bundle():
    state, catalogue = samples()
    with TestClient(create_app(run_loop=False, debug_truth=False)) as client:
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
                image = config.ROOT / "frontend/public/replay_assets/a/det-1.png"
                game.decision.images[detection["id"]] = image.read_bytes()
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
                item.update(content_type="image/png", asset_url="/replay_assets/a/det-1.png")
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
                               "action": "approve", "operator": "demo"}),
            ("/api/log", {"level": "info", "source": "agent", "text": "联调 Mock 日志"}),
            ("/api/mode", {"mode": "disaster"}),
            ("/api/inject", {"type": "buoy_down", "target": "B4"}),
            ("/api/control", {"action": "pause"}),
        ):
            capture("POST", path, body=body)
        capture("POST", "/api/scenario/{scenario_id}/start", "/api/scenario/b/start", {"speed": 10})
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
            "description": "联调静态合成样例。所有 REST 示例经真实路由验证；Agent 回答为 Mock。"
                           "state/events 是同一快照；event_catalogue 是独立事件目录，不按序播放。"
                           "这些固定 ID 不可直接用于新的实时场景审批。",
            "state": snapshot, "events": events, "event_catalogue": catalogue,
            "rest": examples, "errors": errors,
            "mock_images": {"/api/sonar/det-1.png": "/replay_assets/a/det-1.png"},
        }


def export(root: Path):
    openapi, bundle = build_bundle()
    outputs = ((root / "docs/integration/openapi.json", openapi),
               (root / "frontend/public/mock/backend.json", bundle))
    for path, payload in outputs:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return [str(path) for path, _ in outputs]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=config.ROOT, help="Output root; defaults to repository")
    args = parser.parse_args()
    print(json.dumps(export(args.root), ensure_ascii=False))


if __name__ == "__main__":
    main()
