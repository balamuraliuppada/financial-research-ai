"""T022 / T024a: Options pricing endpoint tests — known-value assertions."""


def test_options_price_call_returns_200(client):
    """T022: Black-Scholes call price endpoint returns 200."""
    response = client.post("/api/options/price", json={
        "spot": 100.0,
        "strike": 100.0,
        "expiry_years": 1.0,
        "rate": 0.05,
        "volatility": 0.2,
        "option_type": "call",
        "model": "black_scholes",
    })
    assert response.status_code == 200


def test_options_call_price_known_value(client):
    """T022: ATM call price must be ≈ 10.45 (Black-Scholes closed form)."""
    data = client.post("/api/options/price", json={
        "spot": 100.0,
        "strike": 100.0,
        "expiry_years": 1.0,
        "rate": 0.05,
        "volatility": 0.2,
        "option_type": "call",
        "model": "black_scholes",
    }).json()
    price = data.get("price", data.get("call_price"))
    assert price is not None, "No price in response"
    assert 10.40 <= price <= 10.50, f"Call price {price} outside expected range [10.40, 10.50]"


def test_options_put_price_known_value(client):
    """T022: ATM put price must be ≈ 5.57 (put-call parity)."""
    data = client.post("/api/options/price", json={
        "spot": 100.0,
        "strike": 100.0,
        "expiry_years": 1.0,
        "rate": 0.05,
        "volatility": 0.2,
        "option_type": "put",
        "model": "black_scholes",
    }).json()
    price = data.get("price", data.get("put_price"))
    assert price is not None, "No price in response"
    assert 5.50 <= price <= 5.65, f"Put price {price} outside expected range [5.50, 5.65]"


def test_options_has_greeks(client):
    """T022: Response must contain all 5 Greeks."""
    data = client.post("/api/options/price", json={
        "spot": 100.0,
        "strike": 100.0,
        "expiry_years": 1.0,
        "rate": 0.05,
        "volatility": 0.2,
        "option_type": "call",
        "model": "black_scholes",
    }).json()
    for greek in ("delta", "gamma", "theta", "vega", "rho"):
        assert greek in data, f"Greek '{greek}' missing from response"


def test_options_strategy_straddle_returns_payoff(client):
    """T024a: Straddle strategy payoff array has >= 50 points."""
    legs = [
        {"option_type": "call", "strike": 100.0, "expiry_years": 0.25, "rate": 0.05,
         "volatility": 0.2, "position": "long", "quantity": 1, "premium": 5.0},
        {"option_type": "put",  "strike": 100.0, "expiry_years": 0.25, "rate": 0.05,
         "volatility": 0.2, "position": "long", "quantity": 1, "premium": 4.0},
    ]
    response = client.post("/api/options/strategy", json={"legs": legs})
    assert response.status_code == 200
    data = response.json()
    payoff = data.get("payoff", data.get("payoffs", []))
    assert len(payoff) >= 50, f"Payoff has only {len(payoff)} points"
