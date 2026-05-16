# Developer Quickstart: Financial Research AI Platform

**Stack**: FastAPI (Python 3.12) + React 18 · SQLite / PostgreSQL · Redis (Upstash)
**Branch**: `001-financial-research-platform`

---

## Prerequisites

| Tool         | Required version | Check command      |
| ------------ | ---------------- | ------------------ |
| Python       | 3.10+            | `python --version` |
| Node.js      | 18+              | `node --version`   |
| Git          | Any              | `git --version`    |
| Conda / venv | Any              | `conda --version`  |

---

## 1. Clone and set up environment

```bash
git clone <repo-url>
cd financial-research-ai
git checkout 001-financial-research-platform
```

---

## 2. Configure environment variables

Copy the example and fill in your keys:

```bash
cp backend/.env.example backend/.env
```

Edit `backend/.env`:

```env
# Required
GOOGLE_API_KEY=your-gemini-api-key

# Optional — fallback stock data source
ALPHA_VANTAGE_API_KEY=your-alpha-vantage-key

# Optional — news sentiment
NEWSAPI_KEY=7b74b92a008c43d7a0e8fc6f8712d2f2

# Optional — Redis caching (Upstash URL format)
REDIS_URL=rediss://default:<password>@<host>.upstash.io:6379

# Optional — production database (SQLite used when unset)
DATABASE_URL=

# Optional — LangSmith tracing
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your-langsmith-key
LANGCHAIN_PROJECT=financial-research-ai

# Optional — endpoint auth (empty = auth disabled in local dev)
API_KEY=

# Required in production — CORS allow-list
FRONTEND_ORIGIN=http://localhost:3000
```

> **Free-tier API keys**:
>
> - Gemini: [aistudio.google.com](https://aistudio.google.com) → Get API key (free)
> - Alpha Vantage: [alphavantage.co](https://www.alphavantage.co/support/#api-key) → free tier (5 req/min)
> - NewsAPI: [newsapi.org](https://newsapi.org/register) → free tier (100 req/day)
> - Upstash Redis: [console.upstash.com](https://console.upstash.com) → free tier (10,000 req/day)
> - LangSmith: [smith.langchain.com](https://smith.langchain.com) → free tier

---

## 3. One-command startup (recommended)

```bash
bash start.sh
```

This installs all dependencies and starts:

- **Backend**: `http://localhost:8000` (FastAPI + Uvicorn)
- **Frontend**: `http://localhost:3000` (React dev server)
- **API docs**: `http://localhost:8000/docs` (Swagger UI)

---

## 4. Manual startup (alternative)

### Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm start
```

---

## 5. Verify the setup

Open `http://localhost:3000` — you should see the Dashboard.

Quick smoke tests:

```bash
# Health check
curl http://localhost:8000/api/health

# Stock price
curl http://localhost:8000/api/stocks/TCS.NS/price

# Market status
curl http://localhost:8000/api/market/status
```

Expected: all return JSON with `200 OK`.

---

## 6. Run the test suite

```bash
# Backend
cd backend
pip install pytest httpx
pytest tests/ -v

# Frontend
cd frontend
npm test -- --watchAll=false
```

---

## 7. Key workflows for development

### Adding a new backend endpoint

1. Add the route in `backend/main.py`
2. If it calls an external API, add the client method in `api_clients.py` with rate limiter + circuit breaker
3. If it returns computed data, add the logic in the appropriate module (`portfolio_optimizer.py`, `algo_signals.py`, etc.)
4. Add a cache wrapper if the endpoint is called frequently (see `research.md` — Redis pattern)
5. Document the endpoint in `specs/001-financial-research-platform/contracts/api.md`

### Adding a new frontend page

1. Create `frontend/src/pages/NewPage.jsx`
2. Add the API call in `frontend/src/api/index.js`
3. Register the route in `frontend/src/App.jsx`
4. Add the nav link in `frontend/src/components/Sidebar.jsx`

### Running the AI agent locally

Requires `GOOGLE_API_KEY` to be set. Test via:

```bash
curl -X POST http://localhost:8000/api/agent \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the current price of TCS?"}'
```

---

## 8. Production deployment (Render)

### Backend (Web Service)

- **Build command**: `pip install -r backend/requirements.txt`
- **Start command**: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
- **Environment variables**: Set all vars from Section 2. Set `API_KEY` to a random secret. Set `FRONTEND_ORIGIN` to your Render static site URL.

### Frontend (Static Site)

- **Build command**: `cd frontend && npm ci && npm run build`
- **Publish directory**: `frontend/build`
- **Environment variable**: `REACT_APP_API_BASE=https://<your-backend>.onrender.com/api`

---

## 9. Common issues

| Symptom                         | Cause                                                    | Fix                                                                                           |
| ------------------------------- | -------------------------------------------------------- | --------------------------------------------------------------------------------------------- |
| `No such table: stock_searches` | `database.py` and `main.py` using different SQLite paths | Ensure both use `os.path.join(os.path.dirname(os.path.dirname(__file__)), 'financial_ai.db')` |
| Frontend shows no data          | `REACT_APP_API_BASE` not set                             | Set env var and rebuild                                                                       |
| Agent returns "API key not set" | `GOOGLE_API_KEY` missing in `.env`                       | Add the key and restart                                                                       |
| Port 3000 already in use        | Another process on 3000                                  | `start.sh` auto-finds the next free port                                                      |
| Redis connection refused        | `REDIS_URL` not set, Redis not running                   | Either start Redis locally or use Upstash URL                                                 |
