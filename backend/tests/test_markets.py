"""Markets listing, search, filtering, detail pages and watchlists."""
from conftest import get_csrf, instrument_id, login, register

from app.models import User, WatchlistItem


def test_markets_list_shows_instruments(client):
    body = client.get("/markets/").get_data(as_text=True)
    assert "AAPL" in body
    assert "BTC/USD" in body
    assert "not live market data" in body


def test_market_search(client):
    only_btc = client.get("/markets/?q=bitcoin").get_data(as_text=True)
    assert "BTC/USD" in only_btc
    assert "AAPL" not in only_btc

    by_symbol = client.get("/markets/?q=eth").get_data(as_text=True)
    assert "ETH/USD" in by_symbol


def test_market_asset_filter(client):
    body = client.get("/markets/?asset=Crypto").get_data(as_text=True)
    assert "BTC/USD" in body
    assert "AAPL" not in body


def test_instrument_detail(client):
    response = client.get("/markets/BTC/USD")
    assert response.status_code == 200
    assert "Bitcoin" in response.get_data(as_text=True)
    # The trade form is not offered to anonymous visitors.
    assert "Sign in to trade" in response.get_data(as_text=True)


def test_watchlist_add_and_remove(client, app):
    register(client, email="watcher@example.com")
    user = User.query.filter_by(email="watcher@example.com").first()
    iid = instrument_id(app, "AAPL")
    token = get_csrf(client, "/markets/")

    client.post(
        "/markets/watchlist",
        data={"csrf_token": token, "instrument_id": str(iid)},
        follow_redirects=True,
    )
    assert WatchlistItem.query.filter_by(user_id=user.id, instrument_id=iid).count() == 1
    assert "AAPL" in client.get("/dashboard").get_data(as_text=True)

    token = get_csrf(client, "/markets/")
    client.post(
        "/markets/watchlist",
        data={"csrf_token": token, "instrument_id": str(iid)},
        follow_redirects=True,
    )
    assert WatchlistItem.query.filter_by(user_id=user.id, instrument_id=iid).count() == 0


def test_api_instruments(client):
    response = client.get("/api/instruments")
    assert response.status_code == 200
    payload = response.get_json()
    assert len(payload["data"]) >= 10
    sample = payload["data"][0]
    assert {"symbol", "name", "asset_class", "price", "change_percent"} <= set(sample)
    assert "not live market data" in payload["disclaimer"]


def test_api_instrument_by_symbol_with_slash(client):
    response = client.get("/api/instruments/BTC/USD")
    assert response.status_code == 200
    assert response.get_json()["data"]["symbol"] == "BTC/USD"


def test_unknown_instrument_returns_404(client):
    assert client.get("/markets/NOPE").status_code == 404
