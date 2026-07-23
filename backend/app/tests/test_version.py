from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_get_version() -> None:
    response = client.get("/version")
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "BriefPilot"
    assert "version" in body
