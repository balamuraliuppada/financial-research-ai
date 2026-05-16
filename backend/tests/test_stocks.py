"""T011 / T043: Stock endpoints and NaN safety regression tests."""
import json


def test_stocks_list_returns_200(client):
    response = client.get("/api/stocks/list")
    assert response.status_code == 200


def test_stocks_list_non_empty(client):
    data = client.get("/api/stocks/list").json()
    assert isinstance(data, list)
    assert len(data) > 0


def test_stocks_list_has_required_keys(client):
    items = client.get("/api/stocks/list").json()
    for item in items[:3]:
        assert "symbol" in item
        assert "name" in item
        assert "sector" in item


def test_stock_price_tcs(client):
    """T011: price endpoint returns expected keys."""
    response = client.get("/api/stocks/TCS.NS/price", params={"period": "1mo"})
    assert response.status_code == 200
    data = response.json()
    assert "current_price" in data
    assert "rsi" in data
    assert "candles" in data
    assert isinstance(data["candles"], list)


def test_stocks_list_no_nan_in_response(client):
    """T043: FR-029 regression — no NaN or Infinity in serialized response."""
    response = client.get("/api/stocks/list")
    assert response.status_code == 200
    body = response.text
    assert "NaN" not in body
    assert "Infinity" not in body
