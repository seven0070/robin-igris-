"""Voice bridge health endpoint."""

from fastapi.testclient import TestClient

from robin_igris.voice_server import app


def test_health():
    client = TestClient(app)
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["ok"] is True
