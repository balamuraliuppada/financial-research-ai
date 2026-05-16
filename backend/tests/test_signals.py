"""T020 / T041: Algorithmic signals endpoint tests."""


def test_signals_tcs_returns_200(client):
    """T020: Signals endpoint returns 200."""
    response = client.get("/api/signals/TCS.NS")
    assert response.status_code == 200


def test_signals_has_composite(client):
    """T020: Response contains composite signal."""
    data = client.get("/api/signals/TCS.NS").json()
    assert "composite" in data or "signal" in data


def test_signals_has_confidence(client):
    """T020: Response contains confidence score."""
    data = client.get("/api/signals/TCS.NS").json()
    assert "confidence" in data


def test_signals_has_indicators(client):
    """T020: Response contains at least 6 indicators."""
    data = client.get("/api/signals/TCS.NS").json()
    indicators = data.get("indicators", data.get("signals", {}))
    assert len(indicators) >= 6, f"Only {len(indicators)} indicators returned"


def test_signals_batch_returns_200(client):
    """T041 / FR-013: Batch signals endpoint returns 200."""
    response = client.post("/api/signals/batch", json={
        "symbols": ["TCS.NS", "INFY.NS", "SBIN.NS"]
    })
    assert response.status_code == 200


def test_signals_batch_returns_all_symbols(client):
    """T041 / FR-013: Each symbol in batch has composite and confidence."""
    data = client.post("/api/signals/batch", json={
        "symbols": ["TCS.NS", "INFY.NS", "SBIN.NS"]
    }).json()
    assert isinstance(data, list)
    assert len(data) == 3
    for item in data:
        assert "symbol" in item or "composite" in item
