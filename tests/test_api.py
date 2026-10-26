"""Health and routing checks for the production FastAPI application."""

from fastapi.testclient import TestClient

from src.api.server import app


def test_health_endpoints_and_docs_redirect():
    client = TestClient(app)
    assert client.get("/health").json()["status"] == "ok"
    assert client.get("/health/live").json()["status"] == "live"
    assert client.get("/health/ready").json()["status"] == "ready"
    response = client.get("/", follow_redirects=False)
    assert response.status_code in [302, 307]
    assert "/docs" in response.headers["location"]
