# API Contract: Financial Research AI Platform

**Type**: REST + WebSocket
**Base URL (local)**: `http://localhost:8000/api`
**Base URL (production)**: `https://<backend>.onrender.com/api`
**Auto-generated docs**: `GET /docs` (Swagger UI) · `GET /redoc`
**Auth**: `X-API-Key: <value>` header required in production (env `API_KEY`). Omit in local dev when `API_KEY` is unset.

---

## Health & Status

### `GET /api/health`

Returns health status of all registered API circuit breakers.
No auth required.

**Response 200**

```json
{
  "status": "healthy",
  "apis": {
    "yfinance": { "status": "healthy", "failure_count": 0, "latency_ms": 142 },
    "alpha_vantage": {
      "status": "healthy",
      "failure_count": 0,
      "latency_ms": 0
    },
    "newsapi": { "status": "healthy", "failure_count": 0, "latency_ms": 0 }
  }
}
```

### `GET /api/market/status`

Indian market open/closed status in IST.

**Response 200**

```json
{
  "is_open": false,
  "current_ist": "16 May 2026  04:30 PM IST",
  "open_time": "09:15 AM IST",
  "close_time": "03:30 PM IST",
  "day": "Saturday"
}
```

### `GET /api/market/overview`

Global indices snapshot (Nifty50, Sensex, S&P 500, Nasdaq, VIX).

**Response 200**

```json
{
  "indices": {
    "nifty50": {
      "symbol": "^NSEI",
      "name": "NIFTY 50",
      "price": 24500.0,
      "change_pct": 0.42
    }
  }
}
```

---

## Stocks

### `GET /api/stocks/list`

Full list of supported Indian stocks.

**Response 200** — array of:

```json
[{ "symbol": "TCS.NS", "name": "Tata Consultancy Services", "sector": "IT" }]
```

### `GET /api/stocks/sectors`

**Response 200** `{ "sectors": ["IT", "Banking", "FMCG", ...] }`

### `GET /api/stocks/{symbol}/price`

OHLCV candles + technical indicators for a symbol.

**Path param**: `symbol` — NSE ticker (e.g. `TCS.NS`)
**Query param**: `period` — `1d` | `1wk` | `1mo` | `3mo` | `6mo` | `1y` (default `1mo`)

**Response 200**

```json
{
  "symbol": "TCS.NS",
  "name": "Tata Consultancy Services",
  "sector": "IT",
  "current_price": 4200.5,
  "change": 55.25,
  "change_pct": 1.33,
  "period_high": 4250.0,
  "period_low": 3900.0,
  "volume": 1234567,
  "market_cap": "₹15.3L Cr",
  "rsi": 58.4,
  "ma20": 4150.0,
  "candles": [
    {
      "Date": "2026-05-16",
      "Open": 4150.0,
      "High": 4210.0,
      "Low": 4140.0,
      "Close": 4200.5,
      "Volume": 123456,
      "MA20": 4150.0,
      "MA50": 4080.0,
      "RSI": 58.4,
      "BB_upper": 4280.0,
      "BB_lower": 4020.0,
      "BB_mid": 4150.0
    }
  ]
}
```

**Response 404** — symbol not found or no data
**Response 400** — unknown symbol

### `GET /api/stocks/{symbol}/fundamentals`

P/E ratio, EPS, revenue growth, debt-to-equity, etc.

**Response 200**

```json
{
  "symbol": "TCS.NS",
  "pe_ratio": 28.5,
  "eps": 148.0,
  "revenue_growth": 0.08,
  "debt_to_equity": 0.03,
  "current_ratio": 2.8,
  "roe": 0.42,
  "sector": "IT"
}
```

### `GET /api/stocks/{symbol}/compare?compare={symbol2}&period={period}`

Normalised (base=100) price series for two symbols side-by-side.

### `GET /api/stocks/{symbol}/news`

Latest news articles with TextBlob sentiment scores.

**Response 200**

```json
{
  "articles": [
    {
      "title": "TCS beats Q4 estimates",
      "description": "...",
      "url": "https://...",
      "source": "Economic Times",
      "publishedAt": "2026-05-15T10:30:00Z",
      "sentiment": 0.42
    }
  ],
  "sentiment": 0.31
}
```

### `GET /api/sector/{sector}/comparison`

Fundamental metrics for all stocks in a sector.

---

## Portfolio

### `GET /api/portfolio`

All portfolio holdings.

**Response 200** — array of holdings (symbol, name, quantity, buy_price, current_price, pnl, pnl_pct)

### `POST /api/portfolio`

Add a holding.

**Body**

```json
{
  "symbol": "TCS.NS",
  "name": "Tata Consultancy Services",
  "quantity": 10,
  "buy_price": 4000.0
}
```

### `DELETE /api/portfolio/{symbol}`

Remove a holding.

---

## Watchlist

### `GET /api/watchlist`

### `POST /api/watchlist` — `{ "symbol": "INFY.NS", "note": "optional note" }`

### `DELETE /api/watchlist/{symbol}`

### `PATCH /api/watchlist/{symbol}/note` — `{ "note": "updated note" }`

---

## Alerts & Notifications

### `GET /api/alerts`

All alerts for the current user.

### `POST /api/alerts`

Create an alert.

**Body**

```json
{
  "symbol": "TCS.NS",
  "alert_type": "price_above",
  "threshold": 4500.0,
  "message": "TCS above ₹4,500"
}
```

**AlertType values**: `price_above`, `price_below`, `rsi_overbought`, `rsi_oversold`, `volume_spike`, `ma_crossover`, `bollinger_breakout`, `percent_change`

### `DELETE /api/alerts/{alert_id}`

### `PATCH /api/alerts/{alert_id}/toggle` — enable / disable

### `GET /api/notifications`

All notifications (most recent first).

### `PATCH /api/notifications/{id}/read`

### `GET /api/notifications/unread-count`

**Response** `{ "count": 3 }`

### `WebSocket /ws/alerts`

Persistent connection. Server pushes JSON on every alert trigger:

```json
{
  "type": "alert_triggered",
  "symbol": "TCS.NS",
  "alert_type": "price_above",
  "threshold": 4500.0,
  "current_price": 4512.0,
  "message": "TCS above ₹4,500",
  "timestamp": "2026-05-16T11:00:00Z"
}
```

---

## Portfolio Optimization

### `POST /api/optimize`

Run MPT optimization.

**Body**

```json
{
  "symbols": ["TCS.NS", "INFY.NS", "RELIANCE.NS", "HDFCBANK.NS"],
  "period": "1y",
  "risk_free_rate": 0.065,
  "model": "max_sharpe"
}
```

**`model` values**: `max_sharpe` | `min_volatility` | `risk_parity` | `equal_weight`

**Response 200**

```json
{
  "weights": {
    "TCS.NS": 0.35,
    "INFY.NS": 0.25,
    "RELIANCE.NS": 0.25,
    "HDFCBANK.NS": 0.15
  },
  "metrics": {
    "annual_return": 0.182,
    "annual_volatility": 0.145,
    "sharpe_ratio": 1.22,
    "var_95": -0.031,
    "cvar_95": -0.048
  },
  "frontier": [{ "return": 0.1, "volatility": 0.11, "sharpe": 0.77 }]
}
```

---

## Algorithmic Signals

### `GET /api/signals/{symbol}`

Composite signal for one symbol.

**Response 200**

```json
{
  "symbol": "TCS.NS",
  "composite": "BUY",
  "confidence": 72.4,
  "indicators": {
    "rsi": { "value": 42.1, "signal": "BUY", "weight": 0.15 },
    "macd": { "value": 0.8, "signal": "BUY", "weight": 0.15 },
    "stoch": { "k": 38.0, "d": 41.0, "signal": "HOLD", "weight": 0.1 },
    "adx": { "value": 28.5, "signal": "BUY", "weight": 0.1 },
    "supertrend": { "direction": "up", "signal": "BUY", "weight": 0.15 },
    "bollinger": { "position": "lower_band", "signal": "BUY", "weight": 0.1 },
    "ema_cross": { "signal": "BUY", "weight": 0.1 },
    "obv": { "signal": "HOLD", "weight": 0.1 },
    "vwap": { "value": 4180.0, "signal": "BUY", "weight": 0.05 }
  }
}
```

### `POST /api/signals/batch`

**Body** `{ "symbols": ["TCS.NS", "INFY.NS", "SBIN.NS"] }`
**Response 200** — array of signal summaries

---

## Options Pricing

### `POST /api/options/price`

Black-Scholes + Binomial Tree pricing.

**Body**

```json
{
  "S": 4200.0,
  "K": 4200.0,
  "T": 0.0822,
  "r": 0.065,
  "sigma": 0.25,
  "option_type": "call"
}
```

(`T` in years — e.g. 30 days ÷ 365 = 0.0822)

**Response 200**

```json
{
  "black_scholes": {
    "price": 198.42,
    "delta": 0.5142,
    "gamma": 0.0018,
    "theta": -1.842,
    "vega": 6.621,
    "rho": 3.412
  },
  "binomial_tree": { "price": 199.11 },
  "implied_volatility": 0.25
}
```

### `POST /api/options/strategy`

Multi-leg strategy payoff diagram.

**Body**

```json
{
  "strategy": "straddle",
  "S": 4200.0,
  "r": 0.065,
  "sigma": 0.25,
  "legs": [
    { "type": "call", "K": 4200, "T": 0.0822, "position": "long", "qty": 1 },
    { "type": "put", "K": 4200, "T": 0.0822, "position": "long", "qty": 1 }
  ]
}
```

**`strategy` values**: `straddle` | `strangle` | `iron_condor` | `bull_spread` | `bear_spread` | `butterfly`

**Response 200** — `{ "payoff": [{ "price": 3800, "pnl": -350.0 }, ...] }`

### `GET /api/options/strategies`

Returns template definitions for all named strategies.

---

## Multi-Asset & Macro

### `GET /api/multi-asset/treasuries`

### `GET /api/multi-asset/yield-curve`

### `GET /api/multi-asset/commodities`

### `GET /api/multi-asset/commodity/{name}/history?period=1mo`

### `GET /api/multi-asset/forex`

### `GET /api/multi-asset/forex/{pair}/history?period=1mo`

### `GET /api/multi-asset/correlation?assets=gold,crude_oil,RELIANCE.NS`

### `GET /api/multi-asset/performance`

---

## AI Agent

### `POST /api/agent`

Submit a natural-language financial query.

**Body** `{ "query": "Compare TCS and Infosys fundamentals" }`

**Response 200**

```json
{
  "response": "Based on current data:\n\n**TCS** (TCS.NS): P/E 28.5, EPS ₹148...\n**Infosys** (INFY.NS): P/E 24.1, EPS ₹63...",
  "tools_used": ["get_fundamental_analysis", "get_stock_price"]
}
```

**Response 503** — GOOGLE_API_KEY missing
**Response 504** — Agent timeout (> 35 s)

---

## User Profile

### `GET /api/profile`

### `PUT /api/profile`

**Body**

```json
{
  "name": "Investor",
  "email": "user@example.com",
  "risk_profile": "Moderate",
  "investment_goal": "Wealth Creation",
  "experience": "Intermediate",
  "preferred_sectors": ["IT", "Banking"]
}
```

---

## Error Format

All error responses follow:

```json
{
  "error": true,
  "code": "RATE_LIMIT",
  "message": "yfinance rate limit exceeded. Retry after 60s",
  "details": { "api": "yfinance", "retry_after": 60 },
  "timestamp": "2026-05-16T11:00:00Z"
}
```

**Standard HTTP status codes**: 400 Bad Request · 403 Forbidden (invalid API key) · 404 Not Found · 422 Validation Error · 429 Rate Limited · 500 Internal Server Error · 503 Service Unavailable · 504 Gateway Timeout
