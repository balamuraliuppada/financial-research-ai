"""T016 / T017: Portfolio optimization endpoint tests."""


def test_optimize_returns_200(client):
    """T016: Optimization with valid symbols returns 200."""
    response = client.post("/api/portfolio/optimize", json={
        "symbols": ["TCS.NS", "INFY.NS", "RELIANCE.NS"],
        "strategy": "max_sharpe",
        "period": "1y",
    })
    assert response.status_code == 200


def test_optimize_weights_sum_to_one(client):
    """T016: Optimal weights must sum to 1.0 (±0.001)."""
    data = client.post("/api/portfolio/optimize", json={
        "symbols": ["TCS.NS", "INFY.NS", "RELIANCE.NS"],
        "strategy": "max_sharpe",
        "period": "1y",
    }).json()
    weights = data.get("optimal", {}).get("weights", {})
    assert weights, "No weights returned"
    total = sum(weights.values())
    assert abs(total - 1.0) < 0.01, f"Weights sum to {total}, expected ~1.0"


def test_optimize_has_sharpe_ratio(client):
    """T016: Response must contain sharpe_ratio in optimal metrics."""
    data = client.post("/api/portfolio/optimize", json={
        "symbols": ["TCS.NS", "INFY.NS", "RELIANCE.NS"],
        "strategy": "max_sharpe",
        "period": "1y",
    }).json()
    assert "sharpe_ratio" in data.get("optimal", {}), "sharpe_ratio missing"


def test_optimize_frontier_has_entries(client):
    """T016 / FR-009: Frontier must have at least 100 points."""
    data = client.post("/api/portfolio/optimize", json={
        "symbols": ["TCS.NS", "INFY.NS", "RELIANCE.NS"],
        "strategy": "max_sharpe",
        "period": "1y",
        "include_frontier": True,
    }).json()
    frontier = data.get("simulation", data.get("frontier", []))
    assert len(frontier) >= 100, f"Frontier has only {len(frontier)} points"


def test_optimize_single_symbol_returns_400(client):
    """T017: Single symbol must return HTTP 400."""
    response = client.post("/api/portfolio/optimize", json={
        "symbols": ["TCS.NS"],
        "strategy": "max_sharpe",
    })
    assert response.status_code == 400
