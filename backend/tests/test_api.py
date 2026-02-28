# backend/tests/test_api.py
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_status_not_found():
    response = client.get("/api/status/nonexistent")
    assert response.status_code == 404


def test_result_not_found():
    response = client.get("/api/result/nonexistent")
    assert response.status_code == 404
