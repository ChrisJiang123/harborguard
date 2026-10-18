"""Deployment origins must reach the CORS middleware without a wildcard."""
import pytest
from fastapi.testclient import TestClient

from backend.app.main import _cors_origins, create_app


def test_default_local_origins(monkeypatch):
    monkeypatch.delenv("ALLOWED_ORIGINS", raising=False)
    assert _cors_origins() == ["http://localhost:5173", "http://127.0.0.1:5173"]


@pytest.mark.parametrize("origin,allowed", [
    ("https://harborguard-preview.vercel.app", True),
    ("http://localhost:5173", True),
    ("https://unlisted.vercel.app", False),
])
def test_configured_origin_preflight(monkeypatch, origin, allowed):
    monkeypatch.setenv("ALLOWED_ORIGINS", " https://harborguard-preview.vercel.app/ , ,http://localhost:5173 ")
    origins = _cors_origins()
    assert origins == ["https://harborguard-preview.vercel.app", "http://localhost:5173"]
    # No lifespan/model startup or Agent requests are needed for CORS preflight.
    client = TestClient(create_app(run_loop=False))
    response = client.options("/api/agent/ask", headers={
        "Origin": origin,
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "content-type",
    })
    assert response.status_code == (200 if allowed else 400)
    assert response.headers.get("access-control-allow-origin") == (origin if allowed else None)
