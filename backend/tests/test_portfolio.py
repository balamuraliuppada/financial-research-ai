"""T031: Portfolio and watchlist CRUD persistence tests."""


def test_portfolio_get_returns_list(client):
    response = client.get("/api/portfolio")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_portfolio_add_and_retrieve(client):
    """T031: POST adds, GET retrieves."""
    client.delete("/api/portfolio/WIPRO.NS")  # clean slate
    add_resp = client.post("/api/portfolio", json={"symbol": "WIPRO.NS"})
    assert add_resp.status_code == 200
    items = client.get("/api/portfolio").json()
    symbols = [i["symbol"] for i in items]
    assert "WIPRO.NS" in symbols


def test_portfolio_delete(client):
    """T031: DELETE removes holding."""
    client.post("/api/portfolio", json={"symbol": "WIPRO.NS"})
    del_resp = client.delete("/api/portfolio/WIPRO.NS")
    assert del_resp.status_code == 200


def test_watchlist_add_and_retrieve(client):
    """T031: Watchlist add and get round-trip."""
    client.delete("/api/watchlist/WIPRO.NS")
    add_resp = client.post("/api/watchlist", json={
        "symbol": "WIPRO.NS",
        "name": "Wipro Ltd",
        "note": "test note",
    })
    assert add_resp.status_code == 200
    items = client.get("/api/watchlist").json()
    symbols = [i["symbol"] for i in items]
    assert "WIPRO.NS" in symbols
    client.delete("/api/watchlist/WIPRO.NS")


def test_watchlist_note_update(client):
    """T031: Note patch persists."""
    client.post("/api/watchlist", json={"symbol": "WIPRO.NS", "name": "Wipro"})
    patch_resp = client.patch("/api/watchlist/WIPRO.NS/note", json={"note": "updated"})
    assert patch_resp.status_code == 200
    client.delete("/api/watchlist/WIPRO.NS")
