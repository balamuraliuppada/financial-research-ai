"""
FastAPI Backend — Financial Research AI
Connects React frontend to all existing Python modules.
"""

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import yfinance as yf
import pandas as pd
import math
import json
import asyncio
import sys
import os

# ── Add parent so we can import our existing modules ──────────────────────────
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from database import (
    create_table, save_search,
    add_to_portfolio, remove_from_portfolio, get_portfolio,
    add_to_watchlist, remove_from_watchlist, get_watchlist, update_watchlist_note,
)
from fundamentals import (
    get_fundamentals, get_sector_comparison, get_sector,
    is_market_open, format_inr, ALL_SECTORS, INDIAN_STOCKS, get_stocks_by_sector,
)
from agent import run_financial_agent
from logger import log_api_call, log_api_error

# ── Profile DB (SQLite, same file) ────────────────────────────────────────────
import sqlite3

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "financial_ai.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_profile_table():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_profile (
            id INTEGER PRIMARY KEY,
            name TEXT DEFAULT 'Investor',
            email TEXT DEFAULT '',
            phone TEXT DEFAULT '',
            risk_profile TEXT DEFAULT 'Moderate',
            investment_goal TEXT DEFAULT 'Wealth Creation',
            experience TEXT DEFAULT 'Intermediate',
            preferred_sectors TEXT DEFAULT '[]',
            avatar_color TEXT DEFAULT '#00c896',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        INSERT OR IGNORE INTO user_profile (id) VALUES (1)
    """)
    conn.commit()
    conn.close()

app = FastAPI(title="Financial Research AI", version="2.0")

FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "").rstrip("/")
ALLOW_ORIGINS = ["http://localhost:3000", "http://127.0.0.1:3000"]
if FRONTEND_ORIGIN:
    ALLOW_ORIGINS.append(FRONTEND_ORIGIN)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOW_ORIGINS,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?$|https://.*\.onrender\.com$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup():
    create_table()
    init_profile_table()


def json_safe(value):
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    return value


def safe_round(value, digits=2):
    cleaned = json_safe(value)
    if cleaned is None:
        return None
    return round(float(cleaned), digits)


def sanitize_records(df):
    return [
        {k: json_safe(v) for k, v in row.items()}
        for row in df.to_dict(orient="records")
    ]

# ═══════════════════════════════════════════════════════════════════════════════
# MARKET STATUS
# ═══════════════════════════════════════════════════════════════════════════════
@app.get("/api/market/status")
def market_status():
    return is_market_open()

# ═══════════════════════════════════════════════════════════════════════════════
# STOCKS
# ═══════════════════════════════════════════════════════════════════════════════
@app.get("/api/stocks/list")
def stocks_list():
    return [
        {"symbol": sym, "name": name, "sector": sector}
        for sym, (name, sector) in INDIAN_STOCKS.items()
    ]

@app.get("/api/stocks/sectors")
def sectors():
    return {"sectors": ALL_SECTORS}


def validate_stock_symbol(symbol: str):
    sym = symbol.upper().strip()
    if sym not in INDIAN_STOCKS:
        raise HTTPException(status_code=400, detail=f"Unknown stock symbol: {sym}")
    return sym

@app.get("/api/stocks/{symbol}/price")
def stock_price(symbol: str, period: str = "1mo"):
    try:
        ticker = yf.Ticker(symbol)
        log_api_call(symbol, period)
        if period == "1d":
            data = ticker.history(period="1d", interval="5m")
        else:
            data = ticker.history(period=period)

        if data.empty:
            raise HTTPException(status_code=404, detail="No data found")

        # Technical indicators
        data["MA20"] = data["Close"].rolling(window=20).mean()
        data["MA50"] = data["Close"].rolling(window=50).mean()
        delta = data["Close"].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        data["RSI"] = 100 - (100 / (1 + rs))

        # Bollinger Bands
        data["BB_mid"] = data["Close"].rolling(20).mean()
        data["BB_std"] = data["Close"].rolling(20).std()
        data["BB_upper"] = data["BB_mid"] + 2 * data["BB_std"]
        data["BB_lower"] = data["BB_mid"] - 2 * data["BB_std"]

        data = data.reset_index()
        data["Date"] = data["Datetime"].astype(str) if "Datetime" in data.columns else data["Date"].astype(str)

        cols = ["Date","Open","High","Low","Close","Volume","MA20","MA50","RSI","BB_upper","BB_lower","BB_mid"]
        result = sanitize_records(data[[c for c in cols if c in data.columns]])

        info = ticker.info
        save_search(symbol, period)

        current = safe_round(data["Close"].iloc[-1], 2)
        prev = safe_round(data["Close"].iloc[-2], 2) if len(data) > 1 else current
        change = safe_round(current - prev, 2) if current is not None and prev is not None else None
        pct = safe_round((change / prev) * 100, 2) if change is not None and prev else None

        return {
            "symbol": symbol,
            "name": info.get("longName", symbol),
            "sector": get_sector(symbol),
            "current_price": current,
            "change": change,
            "change_pct": pct,
            "period_high": safe_round(data["High"].max(), 2),
            "period_low": safe_round(data["Low"].min(), 2),
            "volume": json_safe(info.get("volume", 0)),
            "market_cap": format_inr(info.get("marketCap")),
            "rsi": safe_round(data["RSI"].iloc[-1], 2),
            "ma20": safe_round(data["MA20"].iloc[-1], 2),
            "candles": result,
        }
    except HTTPException:
        raise
    except Exception as e:
        log_api_error(e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stocks/{symbol}/fundamentals")
def stock_fundamentals(symbol: str):
    data = get_fundamentals(symbol)
    if "Error" in data:
        raise HTTPException(status_code=500, detail=data["Error"])
    return data


@app.get("/api/stocks/{symbol}/compare")
def compare_stocks(symbol: str, compare: str, period: str = "1mo"):
    """Return normalised price series for two stocks."""
    def fetch(sym):
        t = yf.Ticker(sym)
        d = t.history(period="1d", interval="5m") if period == "1d" else t.history(period=period)
        d = d.reset_index()
        d["Date"] = d["Datetime"].astype(str) if "Datetime" in d.columns else d["Date"].astype(str)
        base = float(d["Close"].iloc[0])
        d["Normalised"] = (d["Close"] / base * 100).round(2)
        return d[["Date","Close","Normalised"]].to_dict(orient="records")

    return {
        "stock1": {"symbol": symbol, "name": INDIAN_STOCKS.get(symbol,  (symbol,""))[0],  "data": fetch(symbol)},
        "stock2": {"symbol": compare, "name": INDIAN_STOCKS.get(compare, (compare,""))[0], "data": fetch(compare)},
    }


@app.get("/api/sector/{sector}/comparison")
def sector_comparison(sector: str):
    df = get_sector_comparison(sector)
    if df.empty:
        return {"rows": []}
    df = df.reset_index()
    return {"rows": df.fillna("N/A").to_dict(orient="records")}


@app.get("/api/stocks/{symbol}/news")
def stock_news(symbol: str):
    import requests as req
    from textblob import TextBlob
    name = INDIAN_STOCKS.get(symbol, (symbol,""))[0]
    url = f"https://newsapi.org/v2/everything?q={name}&pageSize=8&apiKey=7b74b92a008c43d7a0e8fc6f8712d2f2"
    try:
        resp = req.get(url, timeout=8).json()
        if resp.get("status") != "ok":
            return {"articles": [], "sentiment": 0}
        articles = resp.get("articles", [])
        result = []
        sentiments = []
        for art in articles:
            title = art.get("title","")
            desc  = art.get("description","")
            s = TextBlob(title).sentiment.polarity
            sentiments.append(s)
            result.append({
                "title": title,
                "description": desc,
                "url": art.get("url",""),
                "source": art.get("source",{}).get("name",""),
                "publishedAt": art.get("publishedAt",""),
                "sentiment": round(s, 2),
            })
        avg = round(sum(sentiments)/len(sentiments), 2) if sentiments else 0
        return {"articles": result, "sentiment": avg}
    except Exception as e:
        return {"articles": [], "sentiment": 0, "error": str(e)}


# ═══════════════════════════════════════════════════════════════════════════════
# PORTFOLIO
# ═══════════════════════════════════════════════════════════════════════════════
class PortfolioItem(BaseModel):
    symbol: str

@app.get("/api/portfolio")
def portfolio_get():
    symbols = get_portfolio()
    result = []
    for sym in symbols:
        try:
            t = yf.Ticker(sym)
            d = t.history(period="2d")
            if not d.empty and len(d) >= 2:
                cp  = round(float(d["Close"].iloc[-1]), 2)
                pp  = round(float(d["Close"].iloc[-2]), 2)
                chg = round(cp - pp, 2)
                pct = round((chg/pp)*100, 2)
            elif not d.empty:
                cp, pp, chg, pct = round(float(d["Close"].iloc[-1]),2), 0, 0, 0
            else:
                cp = pp = chg = pct = 0
            result.append({
                "symbol": sym,
                "name": INDIAN_STOCKS.get(sym, (sym,""))[0],
                "sector": get_sector(sym),
                "price": cp,
                "change": chg,
                "change_pct": pct,
            })
        except:
            result.append({"symbol": sym, "name": sym, "sector": get_sector(sym), "price": 0, "change": 0, "change_pct": 0})
    return result

@app.post("/api/portfolio")
def portfolio_add(item: PortfolioItem):
    sym = validate_stock_symbol(item.symbol)
    add_to_portfolio(sym)
    return {"ok": True}

@app.delete("/api/portfolio/{symbol}")
def portfolio_remove(symbol: str):
    remove_from_portfolio(symbol.upper())
    return {"ok": True}


# ═══════════════════════════════════════════════════════════════════════════════
# WATCHLIST
# ═══════════════════════════════════════════════════════════════════════════════
class WatchlistItem(BaseModel):
    symbol: str
    name: Optional[str] = ""
    sector: Optional[str] = ""
    note: Optional[str] = ""

class NoteUpdate(BaseModel):
    note: str

@app.get("/api/watchlist")
def watchlist_get():
    items = get_watchlist()
    result = []
    for item in items:
        sym = item["symbol"]
        try:
            t = yf.Ticker(sym)
            d = t.history(period="2d")
            if not d.empty and len(d) >= 2:
                cp  = round(float(d["Close"].iloc[-1]), 2)
                pp  = round(float(d["Close"].iloc[-2]), 2)
                chg = round(cp - pp, 2)
                pct = round((chg/pp)*100, 2)
            elif not d.empty:
                cp, chg, pct = round(float(d["Close"].iloc[-1]),2), 0, 0
            else:
                cp = chg = pct = 0
        except:
            cp = chg = pct = 0
        result.append({**item, "price": cp, "change": chg, "change_pct": pct})
    return result

@app.post("/api/watchlist")
def watchlist_add(item: WatchlistItem):
    sym = validate_stock_symbol(item.symbol)
    name = item.name or INDIAN_STOCKS.get(sym, (sym,""))[0]
    sector = item.sector or get_sector(sym)
    add_to_watchlist(sym, name=name, sector=sector, note=item.note or "")
    return {"ok": True}

@app.delete("/api/watchlist/{symbol}")
def watchlist_remove(symbol: str):
    remove_from_watchlist(symbol.upper())
    return {"ok": True}

@app.patch("/api/watchlist/{symbol}/note")
def watchlist_note(symbol: str, body: NoteUpdate):
    update_watchlist_note(symbol.upper(), body.note)
    return {"ok": True}


# ═══════════════════════════════════════════════════════════════════════════════
# PROFILE
# ═══════════════════════════════════════════════════════════════════════════════
class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    risk_profile: Optional[str] = None
    investment_goal: Optional[str] = None
    experience: Optional[str] = None
    preferred_sectors: Optional[list] = None
    avatar_color: Optional[str] = None

@app.get("/api/profile")
def profile_get():
    conn = get_db()
    row = conn.execute("SELECT * FROM user_profile WHERE id=1").fetchone()
    conn.close()
    if not row:
        return {}
    d = dict(row)
    d["preferred_sectors"] = json.loads(d.get("preferred_sectors") or "[]")
    return d

@app.put("/api/profile")
def profile_update(body: ProfileUpdate):
    conn = get_db()
    data = body.dict(exclude_none=True)
    if "preferred_sectors" in data:
        data["preferred_sectors"] = json.dumps(data["preferred_sectors"])
    if not data:
        conn.close()
        return {"ok": True}
    sets = ", ".join(f"{k}=?" for k in data)
    vals = list(data.values()) + [1]
    conn.execute(f"UPDATE user_profile SET {sets} WHERE id=?", vals)
    conn.commit()
    conn.close()
    return {"ok": True}

@app.get("/api/profile/stats")
def profile_stats():
    portfolio = get_portfolio()
    watchlist = get_watchlist()
    conn = get_db()
    create_table()
    try:
        searches = conn.execute("SELECT COUNT(*) as c FROM stock_searches").fetchone()
    except sqlite3.OperationalError:
        searches = {"c": 0}
    conn.close()
    return {
        "portfolio_count": len(portfolio),
        "watchlist_count": len(watchlist),
        "total_searches": searches["c"] if searches else 0,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# AI AGENT
# ═══════════════════════════════════════════════════════════════════════════════
class ChatMessage(BaseModel):
    message: str

@app.post("/api/agent/chat")
def agent_chat(body: ChatMessage):
    try:
        response = run_financial_agent(body.message)
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
