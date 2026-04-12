# Financial Research AI

Full-stack Indian stock market research platform with:

- React frontend dashboard
- FastAPI backend API
- SQLAlchemy persistence (PostgreSQL/SQLite compatible) for portfolio, watchlist, and custom metrics
- AI assistant for advanced market queries

## Highlights

- **Live Market Tracking**: Real-time NSE/BSE stock tracking using a resilient, circuit-breaking unified API (Yahoo Finance & Alpha Vantage).
- **Portfolio Optimization**: Modern Portfolio Theory (MPT) integration with Efficient Frontier rendering, Risk Parity, and Markowitz allocation models.
- **Algorithmic Trading Signals**: Composite scoring engine processing 9 technical indicators (RSI, MACD, VWAP, Supertrend, etc.) into unified confidence metrics.
- **Multi-Asset Framework**: Cross-asset analysis covering US Treasury Yield Curves, Commodities (Gold/Oil), Forex pairs, and asset correlation matrices.
- **Options Pricing & Strategies**: Derivatives analysis using Black-Scholes and Binomial Tree models to compute Greeks and model Payoff P&L for multi-leg strategies (e.g. Iron Condor, Straddle).
- **Real-Time Market Alerts**: Background evaluation engine for price breakouts, volume spikes, and technical crossover events with native notification support.
- **AI Assistant**: LangGraph-powered AI endpoint enriched with tools to natively query portfolio optimization, options data, macro indicators, and technical signals conversationally.
- **Production-Ready**: Robust error handling, NaN/Infinity JSON serialization fixes, and exponential backend retries.

## Tech Stack

- **Frontend**: React, Axios, React Router, Recharts
- **Backend**: FastAPI, Uvicorn, Pandas, yfinance, aiohttp, scipy, numpy, SQLAlchemy, LangChain/LangGraph
- **Database**: SQLite (local) / PostgreSQL (production ready)
- **Deployment**: Render (Static Site + Web Service)

## Project Structure

```text
.
|- backend/
|  |- main.py
|  |- models.py
|  |- api_clients.py
|  |- error_handling.py
|  |- portfolio_optimizer.py
|  |- alerts.py
|  |- multi_asset.py
|  |- options_pricing.py
|  |- algo_signals.py
|  |- agent.py
|  |- tools.py
|  |- logger.py
|  |- requirements.txt
|- frontend/
|  |- package.json
|  |- src/
|  |  |- api/index.js
|  |  |- pages/
|  |  |  |- Dashboard.jsx
|  |  |  |- Optimizer.jsx
|  |  |  |- Alerts.jsx
|  |  |  |- MultiAsset.jsx
|  |  |  |- Options.jsx
|  |  |  |- Signals.jsx
|  |  |- components/
|- start.sh
|- README.md
```

## Environment Variables

### Frontend (Render Static Site)

- `REACT_APP_API_BASE`
  - Example: `https://your-backend-service.onrender.com/api`
  - Important: include `/api` at the end.

### Backend (Render Web Service)

- `FRONTEND_ORIGIN`
  - Example: `https://your-frontend-service.onrender.com`
  - Used for CORS allow-list.

- `GOOGLE_API_KEY` 
  - Required for the Gemini-powered AI agent features.
  
- `ALPHA_VANTAGE_API_KEY` (Optional)
  - Used as an alternative/fallback data source.

- `DATABASE_URL` (Optional)
  - Connection string for PostgreSQL in production (defaults to local SQLite).

## Local Development

### Option 1: One-command startup (recommended)

```bash
bash start.sh
```

This script installs dependencies and starts:

- Backend: `http://localhost:8000`
- Frontend: `http://localhost:3000` (or next free port)
- API docs: `http://localhost:8000/docs`

### Option 2: Run services separately

Backend:

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Frontend:

```bash
cd frontend
npm install
npm start
```

## API Base Path

All backend routes are exposed under `/api`, for example:

- `/api/market/status`
- `/api/stocks/list`
- `/api/stocks/{symbol}/price`
- `/api/portfolio/optimize`
- `/api/alerts`
- `/api/options/price`
- `/api/signals/{symbol}`
- `/api/agent/chat`

## Render Deployment

Deploy as two separate services.

### 1) Backend (Web Service)

- Root directory: `backend`
- Build command:

```bash
pip install -r requirements.txt
```

- Start command:

```bash
uvicorn main:app --host 0.0.0.0 --port $PORT
```

- Environment variables:
  - `FRONTEND_ORIGIN=https://your-frontend-service.onrender.com`
  - `GOOGLE_API_KEY=...`
  - `DATABASE_URL=...`

### 2) Frontend (Static Site)

- Root directory: `frontend`
- Build command:

```bash
npm install ; npm run build
```

- Publish directory: `build`
- Environment variables:
  - `REACT_APP_API_BASE=https://your-backend-service.onrender.com/api`

## Common Troubleshooting

### 404 on API endpoints

Cause: frontend API base is missing `/api`.

Fix:

- Set `REACT_APP_API_BASE` to `https://<backend>.onrender.com/api`
- Redeploy frontend

### CORS errors

Fix:

- Set backend `FRONTEND_ORIGIN` to exact frontend URL
- Redeploy backend

### Empty dashboard data after deploy

Check:

- Frontend env var value is correct
- Frontend was redeployed after env change
- Backend service is healthy and responds at `/api/market/status`
