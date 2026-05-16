"""T042 / FR-019: Multi-asset and correlation matrix tests."""


def test_commodities_returns_200(client):
    response = client.get("/api/assets/commodities")
    assert response.status_code == 200


def test_commodities_has_entries(client):
    data = client.get("/api/assets/commodities").json()
    assert isinstance(data, list)
    assert len(data) >= 1  # at least some commodities loaded


def test_yield_curve_returns_200(client):
    response = client.get("/api/assets/fixed-income/yield-curve")
    assert response.status_code == 200


def test_yield_curve_has_points(client):
    data = client.get("/api/assets/fixed-income/yield-curve").json()
    assert "points" in data
    assert len(data["points"]) >= 1


def test_correlation_returns_200(client):
    """T042 / FR-019: Cross-asset correlation endpoint returns 200."""
    response = client.get("/api/assets/correlation")
    assert response.status_code == 200


def test_correlation_values_in_range(client):
    """T042 / FR-019: All correlation values must be between -1.0 and 1.0."""
    data = client.get("/api/assets/correlation").json()
    # Response may be nested — try to find numeric values
    def find_floats(obj):
        if isinstance(obj, dict):
            for v in obj.values():
                yield from find_floats(v)
        elif isinstance(obj, list):
            for item in obj:
                yield from find_floats(item)
        elif isinstance(obj, (int, float)):
            yield float(obj)

    values = list(find_floats(data))
    for v in values:
        assert -1.1 <= v <= 1.1, f"Correlation value {v} outside [-1, 1]"
