"""
multi_asset.py
──────────────
Multi-asset class analysis:
  - Equities (already handled via yfinance + fundamentals.py)
  - Fixed Income: US Treasury yields, yield curve analysis
  - Commodities: Gold, Silver, Crude Oil, Natural Gas, Copper
  - Forex: Major currency pairs
  - Cross-asset correlation and comparative performance
"""

import yfinance as yf
import numpy as np
import pandas as pd
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger("finai.multi_asset")


# ─── Asset Definitions ───────────────────────────────────────────────────────

COMMODITIES = {
    "gold":        {"symbol": "GC=F",  "name": "Gold",         "unit": "USD/oz"},
    "silver":      {"symbol": "SI=F",  "name": "Silver",       "unit": "USD/oz"},
    "crude_oil":   {"symbol": "CL=F",  "name": "Crude Oil WTI","unit": "USD/bbl"},
    "natural_gas": {"symbol": "NG=F",  "name": "Natural Gas",  "unit": "USD/MMBtu"},
    "copper":      {"symbol": "HG=F",  "name": "Copper",       "unit": "USD/lb"},
    "platinum":    {"symbol": "PL=F",  "name": "Platinum",     "unit": "USD/oz"},
}

FOREX_PAIRS = {
    "USDINR": {"symbol": "USDINR=X", "name": "USD/INR"},
    "EURUSD": {"symbol": "EURUSD=X", "name": "EUR/USD"},
    "GBPUSD": {"symbol": "GBPUSD=X", "name": "GBP/USD"},
    "USDJPY": {"symbol": "USDJPY=X", "name": "USD/JPY"},
    "AUDUSD": {"symbol": "AUDUSD=X", "name": "AUD/USD"},
    "USDCAD": {"symbol": "USDCAD=X", "name": "USD/CAD"},
    "USDCHF": {"symbol": "USDCHF=X", "name": "USD/CHF"},
    "EURGBP": {"symbol": "EURGBP=X", "name": "EUR/GBP"},
}

TREASURY_YIELDS = {
    "us_3m":  {"symbol": "^IRX",  "name": "US 3-Month T-Bill",   "maturity": "3M"},
    "us_5y":  {"symbol": "^FVX",  "name": "US 5-Year T-Note",    "maturity": "5Y"},
    "us_10y": {"symbol": "^TNX",  "name": "US 10-Year T-Note",   "maturity": "10Y"},
    "us_30y": {"symbol": "^TYX",  "name": "US 30-Year T-Bond",   "maturity": "30Y"},
}

INDICES = {
    "nifty50":  {"symbol": "^NSEI",  "name": "NIFTY 50"},
    "sensex":   {"symbol": "^BSESN", "name": "SENSEX"},
    "sp500":    {"symbol": "^GSPC",  "name": "S&P 500"},
    "nasdaq":   {"symbol": "^IXIC",  "name": "NASDAQ"},
    "vix":      {"symbol": "^VIX",   "name": "VIX (Volatility)"},
}


# ─── Fixed Income ────────────────────────────────────────────────────────────

def get_treasury_yields() -> List[Dict]:
    """Get current US Treasury yields."""
    results = []
    for key, info in TREASURY_YIELDS.items():
        try:
            ticker = yf.Ticker(info["symbol"])
            data = ticker.history(period="5d")
            if not data.empty:
                current = float(data["Close"].iloc[-1])
                prev = float(data["Close"].iloc[-2]) if len(data) >= 2 else current
                change = round(current - prev, 3)
                results.append({
                    "id": key,
                    "name": info["name"],
                    "maturity": info["maturity"],
                    "yield_pct": round(current, 3),
                    "change": change,
                    "symbol": info["symbol"],
                })
        except Exception as e:
            logger.warning(f"Could not fetch {key}: {e}")
    return results


def get_yield_curve() -> Dict:
    """
    Build yield curve and detect shape (normal/inverted/flat).
    """
    maturities_months = {
        "3M": ("^IRX", 3),
        "5Y": ("^FVX", 60),
        "10Y": ("^TNX", 120),
        "30Y": ("^TYX", 360),
    }

    points = []
    for label, (sym, months) in maturities_months.items():
        try:
            ticker = yf.Ticker(sym)
            data = ticker.history(period="5d")
            if not data.empty:
                y = round(float(data["Close"].iloc[-1]), 3)
                points.append({"maturity": label, "months": months, "yield_pct": y})
        except Exception:
            continue

    # Determine shape
    shape = "unknown"
    if len(points) >= 3:
        yields = [p["yield_pct"] for p in sorted(points, key=lambda x: x["months"])]
        if yields[-1] > yields[0] + 0.2:
            shape = "normal"
        elif yields[-1] < yields[0] - 0.2:
            shape = "inverted"
        else:
            shape = "flat"

    return {
        "points": points,
        "shape": shape,
        "description": {
            "normal": "Short-term rates lower than long-term — healthy economic outlook",
            "inverted": "Short-term rates higher — potential recession signal",
            "flat": "Similar rates across maturities — economic uncertainty",
            "unknown": "Insufficient data",
        }.get(shape, ""),
        "as_of": datetime.utcnow().isoformat(),
    }


def get_yield_history(maturity: str = "10y", period: str = "1y") -> List[Dict]:
    """Get historical yield data for a specific maturity."""
    sym_map = {"3m": "^IRX", "5y": "^FVX", "10y": "^TNX", "30y": "^TYX"}
    sym = sym_map.get(maturity.lower(), "^TNX")

    try:
        ticker = yf.Ticker(sym)
        data = ticker.history(period=period)
        if data.empty:
            return []
        data = data.reset_index()
        return [
            {
                "date": str(row["Date"].date()) if hasattr(row["Date"], "date") else str(row["Date"]),
                "yield_pct": round(float(row["Close"]), 3),
            }
            for _, row in data.iterrows()
        ]
    except Exception as e:
        logger.warning(f"Yield history error: {e}")
        return []


# ─── Commodities ──────────────────────────────────────────────────────────────

def get_all_commodities(period: str = "1mo") -> List[Dict]:
    """Get current prices and changes for all tracked commodities."""
    results = []
    for key, info in COMMODITIES.items():
        try:
            ticker = yf.Ticker(info["symbol"])
            data = ticker.history(period="5d")
            if not data.empty:
                current = round(float(data["Close"].iloc[-1]), 2)
                prev = round(float(data["Close"].iloc[-2]), 2) if len(data) >= 2 else current
                change = round(current - prev, 2)
                pct = round((change / prev) * 100, 2) if prev != 0 else 0
                results.append({
                    "id": key,
                    "name": info["name"],
                    "symbol": info["symbol"],
                    "price": current,
                    "change": change,
                    "change_pct": pct,
                    "unit": info["unit"],
                })
        except Exception as e:
            logger.warning(f"Commodity error ({key}): {e}")
    return results


def get_commodity_history(commodity: str, period: str = "3mo") -> List[Dict]:
    """Get historical price data for a commodity."""
    info = COMMODITIES.get(commodity.lower())
    if not info:
        return []

    try:
        ticker = yf.Ticker(info["symbol"])
        data = ticker.history(period=period).reset_index()
        return [
            {
                "date": str(row["Date"].date()) if hasattr(row["Date"], "date") else str(row["Date"]),
                "open": round(float(row["Open"]), 2),
                "high": round(float(row["High"]), 2),
                "low": round(float(row["Low"]), 2),
                "close": round(float(row["Close"]), 2),
                "volume": int(row["Volume"]) if pd.notna(row["Volume"]) else 0,
            }
            for _, row in data.iterrows()
        ]
    except Exception as e:
        logger.warning(f"Commodity history error: {e}")
        return []


# ─── Forex ────────────────────────────────────────────────────────────────────

def get_all_forex_rates() -> List[Dict]:
    """Get current rates for all tracked forex pairs."""
    results = []
    for pair_id, info in FOREX_PAIRS.items():
        try:
            ticker = yf.Ticker(info["symbol"])
            data = ticker.history(period="5d")
            if not data.empty:
                current = round(float(data["Close"].iloc[-1]), 4)
                prev = round(float(data["Close"].iloc[-2]), 4) if len(data) >= 2 else current
                change = round(current - prev, 4)
                pct = round((change / prev) * 100, 2) if prev != 0 else 0

                # High/Low
                high = round(float(data["High"].max()), 4)
                low = round(float(data["Low"].min()), 4)

                results.append({
                    "pair": pair_id,
                    "name": info["name"],
                    "symbol": info["symbol"],
                    "rate": current,
                    "change": change,
                    "change_pct": pct,
                    "high": high,
                    "low": low,
                })
        except Exception as e:
            logger.warning(f"Forex error ({pair_id}): {e}")
    return results


def get_forex_history(pair: str, period: str = "3mo") -> List[Dict]:
    """Get historical data for a forex pair."""
    info = FOREX_PAIRS.get(pair.upper())
    if not info:
        # Try constructing the symbol
        sym = f"{pair.upper()}=X"
    else:
        sym = info["symbol"]

    try:
        ticker = yf.Ticker(sym)
        data = ticker.history(period=period).reset_index()
        return [
            {
                "date": str(row["Date"].date()) if hasattr(row["Date"], "date") else str(row["Date"]),
                "rate": round(float(row["Close"]), 4),
                "high": round(float(row["High"]), 4),
                "low": round(float(row["Low"]), 4),
            }
            for _, row in data.iterrows()
        ]
    except Exception as e:
        logger.warning(f"Forex history error: {e}")
        return []


# ─── Cross-Asset Analysis ────────────────────────────────────────────────────

def get_cross_asset_correlation(period: str = "1y") -> Dict:
    """
    Compute cross-asset correlation matrix.
    Uses representative instruments from each asset class.
    """
    assets = {
        "NIFTY 50": "^NSEI",
        "S&P 500": "^GSPC",
        "Gold": "GC=F",
        "Crude Oil": "CL=F",
        "US 10Y Yield": "^TNX",
        "USD/INR": "USDINR=X",
        "VIX": "^VIX",
    }

    prices = pd.DataFrame()
    valid_labels = []

    for label, sym in assets.items():
        try:
            ticker = yf.Ticker(sym)
            data = ticker.history(period=period)
            if not data.empty and len(data) > 20:
                prices[label] = data["Close"]
                valid_labels.append(label)
        except Exception:
            continue

    if len(valid_labels) < 3:
        return {"labels": [], "matrix": [], "error": "Insufficient data"}

    prices = prices.fillna(method="ffill").dropna()
    returns = prices.pct_change().dropna()
    corr = returns.corr()

    return {
        "labels": valid_labels,
        "matrix": corr.round(4).values.tolist(),
        "period": period,
        "data_points": len(returns),
    }


def get_asset_class_performance(period: str = "1y") -> List[Dict]:
    """
    Compare performance across asset classes (normalized, rebased to 100).
    """
    assets = {
        "Indian Equities (NIFTY)": "^NSEI",
        "US Equities (S&P 500)": "^GSPC",
        "Gold": "GC=F",
        "Silver": "SI=F",
        "Crude Oil": "CL=F",
        "USD/INR": "USDINR=X",
    }

    results = []
    for label, sym in assets.items():
        try:
            ticker = yf.Ticker(sym)
            data = ticker.history(period=period)
            if not data.empty and len(data) > 5:
                base = float(data["Close"].iloc[0])
                current = float(data["Close"].iloc[-1])
                pct_return = round(((current - base) / base) * 100, 2)

                # Normalize to 100
                normalized = (data["Close"] / base * 100).round(2)
                series = []
                for idx, val in normalized.items():
                    date_str = str(idx.date()) if hasattr(idx, "date") else str(idx)
                    series.append({"date": date_str, "value": float(val)})

                results.append({
                    "label": label,
                    "symbol": sym,
                    "total_return_pct": pct_return,
                    "current": round(current, 2),
                    "series": series[::max(1, len(series)//100)],  # Max ~100 points
                })
        except Exception as e:
            logger.warning(f"Performance error ({label}): {e}")

    # Sort by return
    results.sort(key=lambda x: x["total_return_pct"], reverse=True)
    return results


def get_market_overview() -> Dict:
    """Quick market overview across all asset classes."""
    overview = {
        "indices": [],
        "commodities": [],
        "forex": [],
        "bonds": [],
    }

    # Indices
    for key, info in INDICES.items():
        try:
            ticker = yf.Ticker(info["symbol"])
            data = ticker.history(period="2d")
            if not data.empty:
                current = round(float(data["Close"].iloc[-1]), 2)
                prev = round(float(data["Close"].iloc[-2]), 2) if len(data) >= 2 else current
                change = round(current - prev, 2)
                pct = round((change / prev) * 100, 2) if prev else 0
                overview["indices"].append({
                    "id": key, "name": info["name"],
                    "value": current, "change": change, "change_pct": pct,
                })
        except Exception:
            continue

    # Top commodities
    for key in ["gold", "crude_oil", "silver"]:
        info = COMMODITIES[key]
        try:
            ticker = yf.Ticker(info["symbol"])
            data = ticker.history(period="2d")
            if not data.empty:
                current = round(float(data["Close"].iloc[-1]), 2)
                prev = round(float(data["Close"].iloc[-2]), 2) if len(data) >= 2 else current
                change = round(current - prev, 2)
                pct = round((change / prev) * 100, 2) if prev else 0
                overview["commodities"].append({
                    "id": key, "name": info["name"],
                    "value": current, "change": change, "change_pct": pct,
                    "unit": info["unit"],
                })
        except Exception:
            continue

    # Key forex
    for pair in ["USDINR", "EURUSD"]:
        info = FOREX_PAIRS[pair]
        try:
            ticker = yf.Ticker(info["symbol"])
            data = ticker.history(period="2d")
            if not data.empty:
                current = round(float(data["Close"].iloc[-1]), 4)
                prev = round(float(data["Close"].iloc[-2]), 4) if len(data) >= 2 else current
                change = round(current - prev, 4)
                pct = round((change / prev) * 100, 2) if prev else 0
                overview["forex"].append({
                    "pair": pair, "name": info["name"],
                    "rate": current, "change": change, "change_pct": pct,
                })
        except Exception:
            continue

    # 10Y yield
    try:
        ticker = yf.Ticker("^TNX")
        data = ticker.history(period="2d")
        if not data.empty:
            current = round(float(data["Close"].iloc[-1]), 3)
            prev = round(float(data["Close"].iloc[-2]), 3) if len(data) >= 2 else current
            overview["bonds"].append({
                "name": "US 10Y Treasury Yield",
                "yield_pct": current,
                "change": round(current - prev, 3),
            })
    except Exception:
        pass

    return overview
