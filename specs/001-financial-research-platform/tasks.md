# Tasks: Financial Research AI Platform (Track B)

**Input**: Design documents from `specs/001-financial-research-platform/`
**Branch**: `001-financial-research-platform`
**Total tasks**: 46 | **Parallel opportunities**: 33 | **User stories**: 8

> **Context**: The core platform is ~85% complete. Tasks focus on the 5 remaining gaps
> (Redis caching, CI/CD, endpoint auth, LangSmith, submission deliverables)
> plus verification of each user story with basic test coverage.

---

## Phase 1: Setup

**Purpose**: Test infrastructure and developer environment baseline — required before CI/CD can run.

- [X] T001 Create `backend/tests/` directory with `backend/tests/__init__.py` (empty file)
- [X] T002 [P] Create `backend/tests/conftest.py` — define `client` fixture using `from fastapi.testclient import TestClient` importing `backend.main.app`; set `DATABASE_URL=sqlite:///./test.db` and `API_KEY=` as env overrides before import
- [X] T003 [P] Create `backend/.env.example` — copy structure from `backend/.env`, replace all secret values with placeholder strings (e.g. `GOOGLE_API_KEY=your-gemini-api-key-here`); include `LANGCHAIN_TRACING_V2=false`, `LANGCHAIN_API_KEY=`, `LANGCHAIN_PROJECT=financial-research-ai`, `API_KEY=` entries
- [X] T004 [P] Add `httpx` and `pytest` to `backend/requirements.txt` if not already present (needed for `TestClient`)

**Checkpoint**: `pytest backend/tests/ -v` runs without import errors.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Cross-cutting infrastructure gaps that block production readiness across all user stories.

⚠️ **CRITICAL**: Complete before any user story tasks that touch caching or auth.

- [X] T005 Add async Redis cache helpers to `backend/api_clients.py` — add `cache_get(key)` and `cache_set(key, value, ttl)` functions using `redis.asyncio` per the pattern in `specs/001-financial-research-platform/research.md`. Use `os.getenv("REDIS_URL", "redis://localhost:6379")`. Wrap both in `try/except` so a missing Redis silently falls through to a `None` return (cache miss).
- [X] T006 [P] Add global `X-API-Key` authentication dependency to `backend/main.py` — import `APIKeyHeader` from `fastapi.security.api_key`, read `API_KEY = os.getenv("API_KEY", "")`, define `verify_api_key` async dependency (skip check when `API_KEY` is empty), pass to `FastAPI(dependencies=[Depends(verify_api_key)])`. Exempt `GET /api/health` and `/docs` by overriding with `dependencies=[]` on those routes.
- [X] T007 [P] Add LangSmith tracing env vars to `backend/.env.example` (already covered in T003) and update `backend/agent.py` startup to log a warning when `LANGCHAIN_TRACING_V2` is not set, so tracing omission is visible in server logs.
- [X] T008 Create `.github/workflows/ci.yml` — two parallel jobs: `backend-test` (Python 3.12, `pip install -r backend/requirements.txt pytest httpx`, `pytest backend/tests/ -v`, env: `DATABASE_URL=sqlite:///./test.db API_KEY=`) and `frontend-test` (Node 18, `cd frontend && npm ci && npm test -- --watchAll=false --passWithNoTests`). Trigger on `push` to `main` and `pull_request`.

**Checkpoint**: `pytest backend/tests/ -v` passes. `.github/workflows/ci.yml` is valid YAML. Backend starts with `API_KEY=` set (auth disabled). Backend starts with `API_KEY=secret` set and returns 403 on unauthenticated requests.

---

## Phase 3: User Story 1 — Live Indian Stock Analysis (Priority: P1) 🎯 MVP

**Goal**: Complete stock price endpoint with Redis caching and verify the full analysis pipeline.

**Independent Test**: `GET /api/stocks/TCS.NS/price?period=1mo` returns current price, RSI, MA20, MA50, Bollinger Bands, and OHLCV candles. Switching period to `1d` returns 5-minute interval data.

- [X] T009 [US1] Add Redis cache check/set to `GET /api/stocks/{symbol}/price` in `backend/main.py` — before calling yfinance, call `cache_get(f"finai:price:{symbol}:{period}")` and return cached result if present; after computing response dict, call `cache_set(key, result, ttl=300)`
- [X] T010 [P] [US1] Add Redis cache check/set to `GET /api/stocks/{symbol}/fundamentals` in `backend/main.py` — cache key `finai:fundamentals:{symbol}`, TTL 1800 seconds
- [X] T011 [P] [US1] Create `backend/tests/test_stocks.py` — test `GET /api/stocks/list` returns HTTP 200 with a non-empty list; test `GET /api/stocks/TCS.NS/price?period=1mo` returns 200 and response contains keys `current_price`, `rsi`, `candles`
- [X] T012 [P] [US1] Verify `frontend/src/pages/Dashboard.jsx` handles `current_price: null` gracefully (shows "—" instead of crashing) when the price endpoint returns a null value for a thinly-traded stock

**Checkpoint**: `GET /api/stocks/TCS.NS/price` returns full payload. Second identical request within 5 minutes is served from Redis (verify via logs). `test_stocks.py` passes.

---

## Phase 4: User Story 2 — AI Research Assistant (Priority: P1)

**Goal**: Verify the LangGraph agent is reachable, handles missing API key gracefully, and LangSmith tracing activates when configured.

**Independent Test**: `POST /api/agent {"query": "What is the RSI for INFY.NS?"}` returns a response containing a numeric RSI value without asking for clarification.

- [X] T013 [US2] Create `backend/tests/test_agent.py` — test `POST /api/agent` with `GOOGLE_API_KEY` missing returns HTTP 503 with a clear error message (not a 500 traceback); mock `run_financial_agent` to raise `ValueError("GOOGLE_API_KEY not set")` for this case
- [X] T014 [P] [US2] Verify `backend/agent.py` `run_financial_agent()` returns a plain string and never raises an unhandled exception — wrap the last `response["messages"][-1].content` extraction in a `try/except` and return an error string on failure instead of propagating
- [X] T015 [P] [US2] Verify LangSmith tracing is active in production: confirm `backend/.env.example` contains `LANGCHAIN_TRACING_V2=false` (with comment to enable in prod), `LANGCHAIN_API_KEY=`, and `LANGCHAIN_PROJECT=financial-research-ai`; add a note to `specs/001-financial-research-platform/quickstart.md` Section 2 that setting `LANGCHAIN_TRACING_V2=true` in Render env vars activates tracing and traces are viewable at `smith.langchain.com`

**Checkpoint**: `POST /api/agent` with a valid key returns a string response. `POST /api/agent` without `GOOGLE_API_KEY` returns `{"detail": "..."}` with status 503.

---

## Phase 5: User Story 3 — Portfolio Optimization (Priority: P2)

**Goal**: Verify MPT optimization endpoint produces correct output and the Efficient Frontier renders in the UI.

**Independent Test**: `POST /api/optimize` with `["TCS.NS","INFY.NS","RELIANCE.NS"]` returns weights summing to 1.0, annual metrics, and a `frontier` array of at least 50 points.

- [X] T016 [US3] Create `backend/tests/test_optimizer.py` — test `POST /api/optimize` with `{"symbols": ["TCS.NS", "INFY.NS", "RELIANCE.NS"], "period": "1y", "model": "max_sharpe"}` returns 200, `weights` values sum to 1.0 (±0.001), `metrics` contains `sharpe_ratio`, and `len(frontier) >= 100` (practical proxy for FR-009's 1,000-portfolio requirement)
- [X] T017 [P] [US3] Verify `backend/portfolio_optimizer.py` `run_optimization()` handles a single-symbol input gracefully — add a guard at the top that raises `ValueError("At least 2 symbols required for optimization")` when `len(symbols) < 2`, and ensure `backend/main.py` catches this and returns HTTP 400
- [X] T018 [P] [US3] Verify `frontend/src/pages/Optimizer.jsx` renders the Efficient Frontier `ScatterChart` when the API response includes a `frontier` array — confirm the `frontier` data is mapped to `{x: vol, y: ret}` for Recharts `ScatterChart`

**Checkpoint**: `test_optimizer.py` passes. Single-symbol request returns HTTP 400. Optimizer page renders scatter chart.

---

## Phase 6: User Story 4 — Algorithmic Trading Signals (Priority: P2)

**Goal**: Complete signals endpoint with Redis caching and verify composite score output.

**Independent Test**: `GET /api/signals/SBIN.NS` returns a `composite` field (BUY/SELL/HOLD), a `confidence` float, and an `indicators` object with at least 6 keys.

- [X] T019 [US4] Add Redis cache check/set to `GET /api/signals/{symbol}` in `backend/main.py` — cache key `finai:signals:{symbol}`, TTL 600 seconds; wrap in `try/except` so cache failure does not break the endpoint
- [X] T020 [P] [US4] Create `backend/tests/test_signals.py` — test `GET /api/signals/TCS.NS` returns 200 and response contains keys `composite`, `confidence`, and `indicators` with at least 6 entries
- [X] T021 [P] [US4] Verify `backend/algo_signals.py` `generate_signals()` returns `{"composite": "HOLD", "confidence": 0, "indicators": {}}` rather than raising an exception when the symbol has fewer than 30 days of history

**Checkpoint**: `test_signals.py` passes. Signals endpoint serves from cache on repeated requests.

---

## Phase 7: User Story 5 — Options Pricing & Strategy Payoff (Priority: P2)

**Goal**: Verify Black-Scholes output matches known values and strategy payoff renders correctly.

**Independent Test**: `POST /api/options/price` with `S=100, K=100, T=1, r=0.05, sigma=0.2, option_type=call` returns price ≈ 10.45 (Black-Scholes closed-form result).

- [X] T022 [US5] Create `backend/tests/test_options.py` — test `POST /api/options/price` with `{"S": 100, "K": 100, "T": 1.0, "r": 0.05, "sigma": 0.2, "option_type": "call"}` returns 200 and `black_scholes.price` is between 10.40 and 10.50; test `option_type=put` returns price ≈ 5.57
- [X] T023 [P] [US5] Verify `backend/options_pricing.py` `black_scholes()` returns `{"price": max(S-K,0), ...}` when `T <= 0` without raising `ZeroDivisionError` — confirm existing guard is in place; if not, add `if T <= 0: return intrinsic_value_dict`
- [X] T024a [P] [US5] Backend: extend `backend/tests/test_options.py` — test `POST /api/options/strategy` with `{"strategy": "straddle", "S": 100, "r": 0.05, "sigma": 0.2}` returns 200 and `payoff` array contains at least 50 price point entries
- [X] T024b [P] [US5] Frontend: verify `frontend/src/pages/Options.jsx` strategy payoff chart uses a `LineChart` or `AreaChart` with `price` on the X-axis and `pnl` on the Y-axis — inspect JSX and confirm Recharts component mapping

**Checkpoint**: `test_options.py` passes for both call and put. Straddle strategy payoff chart renders in UI.

---

## Phase 8: User Story 6 — Multi-Asset & Macro Dashboard (Priority: P3)

**Goal**: Verify all multi-asset sections load and add caching for the market overview.

**Independent Test**: `GET /api/multi-asset/commodities` returns at least 5 entries. `GET /api/multi-asset/yield-curve` returns yields for 3M, 5Y, 10Y, 30Y maturities.

- [X] T025 [US6] Add Redis cache check/set to `GET /api/market/overview` in `backend/main.py` — cache key `finai:market:overview`, TTL 120 seconds
- [X] T026 [P] [US6] Verify `backend/multi_asset.py` `get_all_commodities()` returns partial results when one commodity ticker fails (e.g. `GC=F` unavailable) — confirm each commodity is fetched independently in a try/except so one failure does not abort the entire response
- [X] T027 [P] [US6] Verify `frontend/src/pages/MultiAsset.jsx` shows a "Data unavailable" placeholder row (not a blank page) when a commodity or forex API call fails — the component should handle `null` price values in the response array

**Checkpoint**: Multi-asset page loads with at least 4 commodity rows and a yield curve chart. A single failed commodity does not blank the page.

---

## Phase 9: User Story 7 — Real-Time Price & Technical Alerts (Priority: P3)

**Goal**: Verify the WebSocket alert push works end-to-end and notification persistence is correct.

**Independent Test**: Create a `PRICE_ABOVE` alert with a threshold below the current price, wait one alert check cycle (≤60 s), confirm a notification appears in `GET /api/notifications` with `is_read: false`.

- [X] T028 [US7] Create `backend/tests/test_alerts.py` — test `POST /api/alerts` creates an alert (returns 201 or 200 with `id`); test `GET /api/alerts` returns the created alert; test `DELETE /api/alerts/{id}` removes it; test `GET /api/notifications/unread-count` returns `{"count": 0}` on a fresh DB; with `API_KEY=test-secret` env override, test `GET /api/alerts` **without** `X-API-Key` header returns 403 (covers C3)
- [X] T029 [P] [US7] Verify `backend/alerts.py` `AlertEngine.check_alerts()` records a `Notification` row in the DB when an alert triggers — confirm `SessionLocal` is opened and committed inside `check_alerts()`, not just `ws_manager.broadcast()`
- [X] T030 [P] [US7] Verify `frontend/src/pages/Alerts.jsx` connects to `ws://localhost:8000/ws/alerts` on mount and shows a toast notification when a `alert_triggered` WebSocket message is received — confirm the `useEffect` WebSocket setup and `onmessage` handler are present

**Checkpoint**: `test_alerts.py` passes. Triggered alert appears in `/api/notifications`. WebSocket push visible in browser console.

---

## Phase 10: User Story 8 — Portfolio & Watchlist Management (Priority: P3)

**Goal**: Verify data persists across restarts and P&L calculations are correct.

**Independent Test**: Add INFY.NS to portfolio via `POST /api/portfolio`, restart the backend, call `GET /api/portfolio` — the holding is still present.

- [X] T031 [US8] Create `backend/tests/test_portfolio.py` — test `POST /api/portfolio` adds a holding; test `GET /api/portfolio` returns it; test `DELETE /api/portfolio/INFY.NS` removes it; test `POST /api/watchlist` and `GET /api/watchlist` round-trip
- [X] T032 [P] [US8] Verify `backend/database.py` and `backend/models.py` use the same absolute SQLite path — confirm both resolve to `os.path.join(os.path.dirname(os.path.dirname(__file__)), "financial_ai.db")`; if `database.py` uses a relative path, fix it to use the absolute form (see `startup-notes.md`)
- [X] T033 [P] [US8] Verify `frontend/src/pages/Portfolio.jsx` displays unrealised P&L as `(current_price - buy_price) * quantity` rounded to 2 decimal places in INR, and shows green/red colour based on sign

**Checkpoint**: `test_portfolio.py` passes. Portfolio data survives a `uvicorn` restart. P&L displays correctly in UI.

---

## Phase 11: Polish & Cross-Cutting Concerns

**Purpose**: Submission readiness — final integration, documentation, and security hardening.

- [X] T034 Add `financial_ai.db` and `*.db` to `.gitignore` if not already excluded — confirm no SQLite file is committed to the repository
- [X] T035 [P] Verify `start.sh` starts the backend using the Python executable found by `which python3` or `PYTHON_CMD` rather than a bare `uvicorn` command (see `startup-notes.md`) — update if needed
- [X] T036 [P] Add financial disclaimer footer to `frontend/src/components/Sidebar.jsx` (bottom of the sidebar nav, visible on all pages): _"For informational purposes only. Not investment advice."_ as required by the Track B curriculum
- [X] T037 [P] Run `GET /api/health` against a locally running instance and verify all registered API circuit breakers show `status: healthy`; fix any 500 errors on this endpoint
- [X] T038 [P] Verify all 11 frontend pages (`Dashboard`, `Portfolio`, `Watchlist`, `Optimizer`, `Options`, `Signals`, `MultiAsset`, `Fundamentals`, `Alerts`, `Assistant`, `Profile`) load without React console errors — open browser DevTools and check the console on each page
- [X] T039 [P] Create `backend/tests/test_health.py` — test `GET /api/health` returns HTTP 200; this is the minimum test needed for the CI pipeline to have a passing baseline
- [X] T040 [P] Verify `backend/.env` and `*.db` are listed in `.gitignore` — already fixed by analysis remediation; run `git status` to confirm neither `.env` nor `financial_ai.db` is tracked
- [X] T041 [P] Add batch signals test to `backend/tests/test_signals.py` — test `POST /api/signals/batch` with `{"symbols": ["TCS.NS", "INFY.NS", "SBIN.NS"]}` returns 200 and an array of 3 signal summaries each containing `symbol`, `composite`, and `confidence` keys (covers FR-013, C1)
- [X] T042 [P] Add correlation matrix test to `backend/tests/test_multi_asset.py` — test `GET /api/multi-asset/correlation?assets=gold,crude_oil` returns 200 and response contains a matrix object where each value is between -1.0 and 1.0 (covers FR-019, C2)
- [X] T043 [P] Add NaN/Infinity regression test to `backend/tests/test_stocks.py` — test `GET /api/stocks/list` response body serializes to valid JSON with no `NaN` or `Infinity` string literals (covers FR-029, C5); use `json.dumps(response.json())` and assert `"NaN" not in body and "Infinity" not in body`
- [X] T044 [P] Document manual performance benchmarks in `specs/001-financial-research-platform/quickstart.md` Section 5 — record observed p50 response times for `GET /api/stocks/TCS.NS/price`, `POST /api/agent`, `POST /api/optimize`, `GET /api/signals/TCS.NS` against SC-001–SC-004 targets (covers C4)

**Checkpoint**: `pytest backend/tests/ -v` passes all tests. CI pipeline green on push to `main`. All 11 pages load cleanly. `start.sh` launches both services correctly.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately
- **Phase 2 (Foundational)**: Depends on Phase 1 — T005/T006 BLOCK all caching and auth tasks
- **Phase 3–10 (User Stories)**: All depend on Phase 2 completion; can proceed in parallel once Phase 2 is done
- **Phase 11 (Polish)**: Depends on Phase 3–10 completion

### User Story Dependencies

| Story                | Phase | Blocking Dependency  | Independent? |
| -------------------- | ----- | -------------------- | ------------ |
| US1 — Stock Analysis | 3     | T005 (Redis helpers) | ✅ Yes       |
| US2 — AI Agent       | 4     | T007 (LangSmith env) | ✅ Yes       |
| US3 — Portfolio Opt. | 5     | None                 | ✅ Yes       |
| US4 — Signals        | 6     | T005 (Redis helpers) | ✅ Yes       |
| US5 — Options        | 7     | None                 | ✅ Yes       |
| US6 — Multi-Asset    | 8     | T005 (Redis helpers) | ✅ Yes       |
| US7 — Alerts         | 9     | None                 | ✅ Yes       |
| US8 — Portfolio      | 10    | None                 | ✅ Yes       |

### Parallel Opportunities

All tasks marked `[P]` within the same phase can run in parallel.

**Phase 1 parallel set**: T002, T003, T004 — run together after T001
**Phase 2 parallel set**: T006, T007, T008 — run together after T005
**Phase 3 parallel set**: T010, T011, T012 — run after T009
**Phase 4 parallel set**: T014, T015 — run after T013
**Phase 5 parallel set**: T017, T018 — run after T016
**Phase 6 parallel set**: T020, T021 — run after T019
**Phase 7 parallel set**: T023, T024 — run after T022
**Phase 8 parallel set**: T026, T027 — run after T025
**Phase 9 parallel set**: T029, T030 — run after T028
**Phase 10 parallel set**: T032, T033 — run after T031
**Phase 11 parallel set**: T035–T040 — run after T034

---

## Parallel Example: User Story 1 (Stock Analysis)

```
Phase 1 (setup):
  T001 (sequential) → T002, T003, T004 (parallel)

Phase 2 (foundational):
  T005 (sequential) → T006, T007, T008 (parallel)

Phase 3 (US1):
  T009 (sequential) → T010, T011, T012 (parallel)
```

---

## Implementation Strategy

**MVP Scope** (minimum for a passing submission): Phase 1 + Phase 2 + Phase 3 (US1) + T039 (health test) + T008 (CI/CD)

**Full Scope** (maximum grade): All phases through Phase 11

**Suggested order for a solo developer**:

1. Phase 1 + 2 together (~2 hours) — unlocks everything
2. Phase 3 + 6 together (US1 + US4 — Redis caching on two hot endpoints, ~1 hour)
3. Phase 9 + 10 (US7 + US8 — alert tests + portfolio persistence fix, ~1 hour)
4. Phase 4–8 (remaining user story tests, ~2 hours)
5. Phase 11 (polish + disclaimer, ~30 min)

**Total estimated effort**: ~7 hours of implementation for full scope.

---

## Task Count Summary

| Phase                       | Tasks  | Parallel | User Story |
| --------------------------- | ------ | -------- | ---------- |
| Phase 1: Setup              | 4      | 3        | —          |
| Phase 2: Foundational       | 4      | 3        | —          |
| Phase 3: US1 Stock Analysis | 4      | 3        | US1        |
| Phase 4: US2 AI Agent       | 3      | 2        | US2        |
| Phase 5: US3 Portfolio Opt. | 3      | 2        | US3        |
| Phase 6: US4 Signals        | 3      | 2        | US4        |
| Phase 7: US5 Options        | 4      | 3        | US5        |
| Phase 8: US6 Multi-Asset    | 3      | 2        | US6        |
| Phase 9: US7 Alerts         | 3      | 2        | US7        |
| Phase 10: US8 Portfolio     | 3      | 2        | US8        |
| Phase 11: Polish            | 11     | 10       | —          |
| **Total**                   | **46** | **33**   | —          |
