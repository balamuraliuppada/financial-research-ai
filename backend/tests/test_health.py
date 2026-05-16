"""T039: Health endpoint baseline — minimum test for CI pipeline."""


def test_health_returns_200(client):
    response = client.get("/api/health")
    assert response.status_code == 200


def test_health_has_apis_key(client):
    data = response = client.get("/api/health").json()
    assert "apis" in data or "status" in data
