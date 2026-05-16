# Data Model: Financial Research AI Platform

**Phase**: 1 — Design
**Date**: 2026-05-16
**Source file**: `backend/models.py` (SQLAlchemy ORM)

---

## Entity Overview

```
User (1) ─────────────────────┐
                               ├── Portfolio (N)
                               ├── WatchlistItem (N)
                               ├── Alert (N) ──── Notification (N)
                               └── UserProfile (1)
```

---

## Entities

### User

> Lightweight identity record. Currently auto-created as a single user (id=1) — no login flow.

| Column       | Type        | Constraints       | Notes               |
| ------------ | ----------- | ----------------- | ------------------- |
| `id`         | Integer     | PK, autoincrement |                     |
| `username`   | String(50)  | UNIQUE, NOT NULL  | Default: "investor" |
| `email`      | String(100) | UNIQUE            | Optional            |
| `created_at` | DateTime    | NOT NULL          | UTC, server default |

---

### UserProfile

> Rich investor profile with risk and goal settings. One-to-one with User.

| Column              | Type        | Constraints  | Notes                                   |
| ------------------- | ----------- | ------------ | --------------------------------------- |
| `id`                | Integer     | PK           |                                         |
| `user_id`           | Integer     | FK → User.id |                                         |
| `name`              | String(100) |              | Display name                            |
| `email`             | String(100) |              |                                         |
| `phone`             | String(20)  |              |                                         |
| `risk_profile`      | String(20)  |              | Conservative / Moderate / Aggressive    |
| `investment_goal`   | String(50)  |              | Wealth Creation / Income / Preservation |
| `experience`        | String(20)  |              | Beginner / Intermediate / Expert        |
| `preferred_sectors` | Text        |              | JSON array of sector names              |
| `avatar_color`      | String(10)  |              | Hex color for UI avatar                 |
| `created_at`        | DateTime    |              | UTC                                     |

> Stored in `user_profile` table via legacy SQLite connection in `main.py`. Migrated to SQLAlchemy in the production path.

---

### Portfolio (SQLAlchemy `Portfolio` model)

> Tracks individual stock holdings with buy-price for P&L calculation.

| Column          | Type             | Constraints       | Notes                               |
| --------------- | ---------------- | ----------------- | ----------------------------------- |
| `id`            | Integer          | PK, autoincrement |                                     |
| `symbol`        | String(20)       | NOT NULL          | NSE ticker e.g. `TCS.NS`            |
| `name`          | String(100)      |                   | Human-readable name                 |
| `quantity`      | Float            | NOT NULL          | Number of shares held               |
| `buy_price`     | Float            | NOT NULL          | Average buy price in INR            |
| `current_price` | Float            |                   | Cached last-known price             |
| `sector`        | String(50)       |                   | From fundamentals lookup            |
| `asset_class`   | Enum(AssetClass) |                   | EQUITY / COMMODITY / FOREX / OPTION |
| `added_at`      | DateTime         |                   | UTC                                 |

**Derived (computed at query time)**:

- `current_value = quantity × current_price`
- `unrealised_pnl = (current_price − buy_price) × quantity`
- `pnl_pct = ((current_price − buy_price) / buy_price) × 100`

---

### WatchlistItem (legacy table `watchlist`)

> Saved symbols with optional notes. No buy-price tracking.

| Column     | Type        | Constraints       | Notes           |
| ---------- | ----------- | ----------------- | --------------- |
| `id`       | Integer     | PK, autoincrement |                 |
| `symbol`   | String(20)  | NOT NULL          | NSE ticker      |
| `name`     | String(100) |                   |                 |
| `sector`   | String(50)  |                   |                 |
| `note`     | Text        |                   | User annotation |
| `added_at` | DateTime    |                   | UTC             |

---

### Alert

> Configurable market condition trigger.

| Column         | Type              | Constraints       | Notes                         |
| -------------- | ----------------- | ----------------- | ----------------------------- |
| `id`           | Integer           | PK, autoincrement |                               |
| `symbol`       | String(20)        | NOT NULL          | NSE ticker                    |
| `alert_type`   | Enum(AlertType)   | NOT NULL          | See AlertType enum            |
| `threshold`    | Float             | NOT NULL          | Trigger value                 |
| `status`       | Enum(AlertStatus) | NOT NULL          | ACTIVE / TRIGGERED / DISABLED |
| `message`      | Text              |                   | Human-readable description    |
| `triggered_at` | DateTime          |                   | UTC timestamp when fired      |
| `created_at`   | DateTime          |                   | UTC                           |

**AlertType values**:

- `PRICE_ABOVE` — price crosses above threshold
- `PRICE_BELOW` — price drops below threshold
- `RSI_OVERBOUGHT` — RSI > threshold (typically 70)
- `RSI_OVERSOLD` — RSI < threshold (typically 30)
- `VOLUME_SPIKE` — volume exceeds threshold × average volume
- `MA_CROSSOVER` — short MA crosses long MA
- `BOLLINGER_BREAKOUT` — price exits Bollinger Band
- `PERCENT_CHANGE` — % intraday change exceeds threshold

**AlertStatus values**: `ACTIVE` → `TRIGGERED` → `DISABLED` (can be reset to ACTIVE)

---

### Notification

> Immutable record of each alert trigger event. Supports read/unread state.

| Column            | Type       | Constraints             | Notes                              |
| ----------------- | ---------- | ----------------------- | ---------------------------------- |
| `id`              | Integer    | PK, autoincrement       |                                    |
| `alert_id`        | Integer    | FK → Alert.id           |                                    |
| `symbol`          | String(20) | NOT NULL                | Denormalized for fast queries      |
| `message`         | Text       | NOT NULL                | Human-readable trigger description |
| `alert_type`      | String(30) |                         | Denormalized                       |
| `threshold`       | Float      |                         | Denormalized                       |
| `triggered_price` | Float      |                         | Actual price at trigger time       |
| `is_read`         | Boolean    | NOT NULL, default False |                                    |
| `created_at`      | DateTime   |                         | UTC                                |

---

### Transaction (SQLAlchemy `Transaction` model)

> Audit log of portfolio buy/sell events.

| Column             | Type                  | Constraints       | Notes                         |
| ------------------ | --------------------- | ----------------- | ----------------------------- |
| `id`               | Integer               | PK                |                               |
| `portfolio_id`     | Integer               | FK → Portfolio.id |                               |
| `transaction_type` | Enum(TransactionType) |                   | BUY / SELL / DIVIDEND         |
| `quantity`         | Float                 |                   |                               |
| `price`            | Float                 |                   | Price per unit at transaction |
| `total_value`      | Float                 |                   |                               |
| `timestamp`        | DateTime              |                   | UTC                           |
| `notes`            | Text                  |                   |                               |

---

## State Transitions

### Alert Status

```
[ACTIVE] ──── condition met ────► [TRIGGERED]
   ▲                                    │
   └──────── reset by user ─────────────┘
   │
[DISABLED] ◄──── toggled off by user
```

---

## Indexes

| Table          | Index Column(s)         | Reason                                        |
| -------------- | ----------------------- | --------------------------------------------- |
| `portfolio`    | `symbol`                | Fast lookup by ticker                         |
| `alert`        | `symbol`, `status`      | Alert engine queries active alerts per symbol |
| `notification` | `is_read`, `created_at` | Unread count + recent-first ordering          |
| `watchlist`    | `symbol`                | Duplicate check on add                        |

---

## Non-Persisted Computation Models

These are transient — computed on demand, never stored:

| Model                | Produced by                              | Key fields                                                         |
| -------------------- | ---------------------------------------- | ------------------------------------------------------------------ |
| `OptimizationResult` | `portfolio_optimizer.run_optimization()` | weights, frontier_points, metrics (return, vol, sharpe, VaR, CVaR) |
| `OptionPriceResult`  | `options_pricing.black_scholes()`        | price, delta, gamma, theta, vega, rho                              |
| `SignalResult`       | `algo_signals.generate_signals()`        | indicators[], composite_signal, confidence_pct                     |
| `MultiAssetSnapshot` | `multi_asset.*`                          | yields[], commodities[], forex[], indices[]                        |
