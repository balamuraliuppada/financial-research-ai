# Research: Financial Research AI Platform (Track B)

**Phase**: 0 — Gap Resolution
**Date**: 2026-05-16
**Feeds into**: [plan.md](plan.md) soft-gate violations (caching, CI/CD, auth, monitoring)

---

## Research Question 1: Active Redis Caching in FastAPI

### Gap

`REDIS_URL` is set in `.env` and `redis` is in `requirements.txt`, but `api_clients.py` makes zero cache reads or writes. FR-024 requires caching of high-frequency endpoints.

### Decision

Use `redis.asyncio` from the `redis` package (already installed) with a simple async helper in `api_clients.py`. Cache stock price responses for 5 minutes and signals for 10 minutes. Use `json.dumps/loads` since responses are already dicts.

### Pattern

```python
import redis.asyncio as aioredis, json, os

_redis = None
async def get_redis():
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))
    return _redis

async def cache_get(key: str):
    r = await get_redis()
    val = await r.get(key)
    return json.loads(val) if val else None

async def cache_set(key: str, value: dict, ttl: int = 300):
    r = await get_redis()
    await r.setex(key, ttl, json.dumps(value))
```

Cache key convention: `finai:{endpoint}:{symbol}:{period}` — e.g. `finai:price:TCS.NS:1mo`

**Endpoints to cache**:
| Endpoint | Cache key | TTL |
|---|---|---|
| `GET /api/stocks/{symbol}/price` | `finai:price:{symbol}:{period}` | 5 min |
| `GET /api/stocks/{symbol}/fundamentals` | `finai:fundamentals:{symbol}` | 30 min |
| `GET /api/signals/{symbol}` | `finai:signals:{symbol}` | 10 min |
| `GET /api/market/overview` | `finai:market:overview` | 2 min |

### Rationale

The existing `api_clients.py` rate limiters prevent API spam but don't eliminate redundant calls when two users request the same stock within seconds. Redis TTL-based caching eliminates the majority of external API calls in a demo environment. Upstash Redis (already configured) supports HTTP-based TLS connections, so no VPC setup is needed.

### Alternatives Considered

- **In-memory dict cache**: Simpler but lost on worker restart; doesn't work across multiple Render workers.
- **functools.lru_cache**: Synchronous only, not compatible with async FastAPI endpoints.

---

## Research Question 2: GitHub Actions CI/CD for FastAPI + React Monorepo

### Gap

No `.github/workflows/` directory exists. FR-028 requires an automated quality pipeline on every push.

### Decision

A single `ci.yml` workflow with two jobs: `backend-test` (pytest) and `frontend-test` (npm test). Both jobs run in parallel on `push` to `main` and on all pull requests.

### Workflow structure

```yaml
name: CI
on:
  push:
    branches: [main]
  pull_request:

jobs:
  backend-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install -r backend/requirements.txt
      - run: pip install pytest httpx
      - run: pytest backend/tests/ -v
        env:
          GOOGLE_API_KEY: ${{ secrets.GOOGLE_API_KEY }}
          REDIS_URL: redis://localhost:6379
          DATABASE_URL: sqlite:///./test.db

  frontend-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: "18" }
      - run: cd frontend && npm ci
      - run: cd frontend && npm test -- --watchAll=false --passWithNoTests
```

**Minimum test coverage required**:

- `backend/tests/test_health.py` — `GET /api/health` returns 200
- `backend/tests/test_stocks.py` — `GET /api/stocks/list` returns non-empty list
- `backend/tests/test_options.py` — Black-Scholes call price for known inputs is within ±0.01

### Rationale

Minimal but functional pipeline satisfies FR-028 and the Track B CI/CD checklist item. `--passWithNoTests` allows the pipeline to succeed while frontend tests are incrementally added.

### Alternatives Considered

- **Pre-commit hooks only**: Local-only, does not satisfy "pipeline on every push" requirement.
- **Full coverage gates (80%+)**: Appropriate for production but excessive for a course project with a submission deadline.

---

## Research Question 3: Endpoint Authentication

### Gap

All 45 backend endpoints are unauthenticated. FR-026 requires access control.

### Decision

Implement a FastAPI `Security` dependency that checks an `X-API-Key` header against an `API_KEY` environment variable. Apply as a global dependency on `app` so all routes are covered with zero per-route changes. Exclude `/api/health` and `/docs` from the requirement.

### Pattern

```python
from fastapi import Security, HTTPException
from fastapi.security.api_key import APIKeyHeader

API_KEY = os.getenv("API_KEY", "")
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def verify_api_key(key: str = Security(api_key_header)):
    if API_KEY and key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")

app = FastAPI(dependencies=[Depends(verify_api_key)])
```

When `API_KEY` is empty (local dev default), the check is skipped — no impact on local development workflow. In production (Render), `API_KEY` is set as a secret environment variable.

### Rationale

A shared API key is the lowest-friction approach for a course demo. It prevents public crawling of the Render deployment, satisfies FR-026, and requires adding exactly one env var. JWT is overkill without a user login flow.

### Alternatives Considered

- **JWT / OAuth2**: Requires a login endpoint, token refresh, and user table. Disproportionate for a single-developer demo.
- **No auth (status quo)**: Fails FR-026 and the PDF's "financial data security best practices" requirement.
- **IP allowlisting**: Not portable across development environments.

---

## Research Question 4: LangSmith Monitoring

### Gap

No observability on AI agent calls. PDF recommends LangSmith for Track B.

### Decision

LangChain auto-instruments when two environment variables are present — zero code changes required:

```bash
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=<langsmith-api-key>
LANGCHAIN_PROJECT=financial-research-ai
```

Add these to `.env` (local) and Render environment variables (production).

### Rationale

LangSmith tracing activates through environment variables alone. Every `agent_executor.invoke(...)` call in `agent.py` will automatically emit traces. This satisfies the monitoring requirement with no code changes.

### Alternatives Considered

- **Custom logging middleware**: More portable but requires implementing trace aggregation manually.
- **Prometheus + Grafana**: Production-grade but excessive for course submission.

---

## Research Question 5: FinBERT Sentiment (Bonus Enhancement)

### Decision

**Defer — not a launch blocker.**

TextBlob polarity scoring is already functional and satisfies the baseline sentiment requirement. FinBERT (`ProsusAI/finbert` via HuggingFace transformers) would require adding `torch` and `transformers` to `requirements.txt` (~2 GB), which would:

- Break the Render free-tier build (512 MB RAM limit)
- Significantly increase cold-start time

**If pursued as bonus**: Add an optional `USE_FINBERT=true` env flag that activates the transformer pipeline only when explicitly enabled. The default remains TextBlob.

### Rationale

The curriculum says "sophisticated sentiment analysis using transformer models" but this is a graded enhancement, not a required deliverable. The risk to deployment stability is higher than the grade uplift.

---

## Summary of Resolved Decisions

| Question       | Decision                                                           | Effort  |
| -------------- | ------------------------------------------------------------------ | ------- |
| Redis caching  | `redis.asyncio` helper in `api_clients.py`, TTL per endpoint type  | ~1 hour |
| GitHub Actions | `ci.yml` with parallel backend + frontend jobs, 3 seed tests       | ~30 min |
| Endpoint auth  | FastAPI global `APIKeyHeader` dependency, env-var guarded          | ~20 min |
| LangSmith      | Environment variables only, zero code changes                      | ~5 min  |
| FinBERT        | Deferred — TextBlob remains default, optional flag if time permits | —       |
