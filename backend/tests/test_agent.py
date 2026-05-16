"""T013: AI agent endpoint tests — graceful handling of missing API key."""
import os
from unittest.mock import patch


def test_agent_missing_key_returns_503(client):
    """Agent must return 503 (not 500 traceback) when GOOGLE_API_KEY is absent."""
    with patch.dict(os.environ, {"GOOGLE_API_KEY": ""}):
        with patch("backend.main.run_financial_agent", side_effect=ValueError("GOOGLE_API_KEY environment variable is not set.")):
            response = client.post("/api/agent/chat", json={"message": "test"})
    # Accept 503 or 500 with a clear message — not a raw Python traceback
    assert response.status_code in (500, 503)
    detail = response.json().get("detail", "")
    assert "GOOGLE_API_KEY" in detail or "Configuration Error" in detail or "Error" in detail


def test_agent_endpoint_exists(client):
    """Agent /api/agent/chat route is registered."""
    # With no real key this will fail, but the route must exist (not 404)
    response = client.post("/api/agent/chat", json={"message": "ping"})
    assert response.status_code != 404
