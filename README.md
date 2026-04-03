# Financial Research AI

Full-stack Indian stock market research platform with:

- React frontend dashboard
- FastAPI backend API
- SQLite persistence for portfolio, watchlist, and profile
- AI assistant for market queries

## Highlights

- Live NSE/BSE stock tracking (Yahoo Finance)
- Technical indicators: RSI, MA20, MA50, Bollinger Bands
- Stock comparison charts
- Fundamentals and sector comparison views
- Portfolio and watchlist management
- News sentiment analysis (TextBlob)
- Profile management with persistent settings
- AI assistant endpoint for financial queries
- Production-ready fixes for NaN/Infinity JSON values
- Render deployment support (frontend + backend services)

## Tech Stack

- Frontend: React, Axios, React Router, Recharts
- Backend: FastAPI, Uvicorn, Pandas, yfinance, LangChain/LangGraph
- Database: SQLite
- Deployment: Render (Static Site + Web Service)

## Project Structure

```text
.
|- backend/
|  |- main.py
|  |- database.py
|  |- fundamentals.py
|  |- agent.py
|  |- tools.py
|  |- logger.py
|  |- requirements.txt
|- frontend/
|  |- package.json
|  |- src/
|  |  |- api/index.js
|  |  |- pages/
|  |  |- components/
|- app.py
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

- `GOOGLE_API_KEY` (if AI agent features depend on Gemini in your setup)

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
- `/api/portfolio`
- `/api/watchlist`
- `/api/profile`
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
  - `GOOGLE_API_KEY=...` (if needed)

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

### 404 on `/market/status`, `/stocks/list`, etc.

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

## Notes

- The repository still contains `app.py` from the older Streamlit flow; active production UI is in `frontend/`.
- Backend includes JSON sanitization for NaN/Infinity to prevent serialization crashes.
