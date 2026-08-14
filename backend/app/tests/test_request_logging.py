"""Verifies M24's request-logging middleware (main.py::log_requests)
actually emits a structured log line with the right fields -- not just that
requests still succeed with it installed."""

import structlog
from fastapi.testclient import TestClient

from app.main import app


def test_a_request_emits_one_structured_http_request_log_entry() -> None:
    with structlog.testing.capture_logs() as logs:
        response = TestClient(app).get("/health")

    assert response.status_code == 200
    entries = [entry for entry in logs if entry.get("event") == "http_request"]
    assert len(entries) == 1
    entry = entries[0]
    assert entry["method"] == "GET"
    assert entry["path"] == "/health"
    assert entry["status_code"] == 200
    assert isinstance(entry["duration_ms"], float)


def test_the_log_never_contains_the_response_body_content() -> None:
    with structlog.testing.capture_logs() as logs:
        TestClient(app).get("/health")

    entries = [entry for entry in logs if entry.get("event") == "http_request"]
    logged_values = " ".join(str(v) for entry in entries for v in entry.values())
    # The /health response body is {"status": "ok"} -- the middleware logs
    # metadata about the request, never response content.
    assert "ok" not in logged_values
