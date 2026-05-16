"""T028 / C3: Alert CRUD tests and auth 403 verification."""
import os


def test_unread_count_returns_200(client):
    response = client.get("/api/notifications/unread-count")
    assert response.status_code == 200
    assert "count" in response.json()


def test_alerts_list_returns_200(client):
    response = client.get("/api/alerts")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_create_alert(client):
    """T028: Create alert returns id."""
    response = client.post("/api/alerts", json={
        "symbol": "TCS.NS",
        "alert_type": "price_above",
        "threshold": 9999.0,
        "condition": "test alert",
    })
    assert response.status_code == 200
    data = response.json()
    assert "id" in data


def test_delete_alert(client):
    """T028: Delete alert removes it."""
    create_resp = client.post("/api/alerts", json={
        "symbol": "INFY.NS",
        "alert_type": "price_below",
        "threshold": 1.0,
    })
    alert_id = create_resp.json()["id"]
    del_resp = client.delete(f"/api/alerts/{alert_id}")
    assert del_resp.status_code == 200


def test_auth_rejects_without_key(auth_client):
    """C3: When API_KEY is set, requests without X-API-Key header return 403."""
    # auth_client fixture sets API_KEY=test-secret but sends no header by default
    response = auth_client.get("/api/alerts")
    assert response.status_code == 403


def test_auth_accepts_with_correct_key(auth_client):
    """C3: Correct X-API-Key header grants access."""
    response = auth_client.get("/api/alerts", headers={"X-API-Key": "test-secret"})
    assert response.status_code == 200
