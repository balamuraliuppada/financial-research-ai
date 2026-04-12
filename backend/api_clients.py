"""
api_clients.py
──────────────
Unified financial-data client layer.
Integrates: Yahoo Finance, Alpha Vantage, NewsAPI, ExchangeRate, FRED-like macro data.
Each client has circuit-breaker + rate-limiter + retry logic.
Fallback chains: yfinance → Alpha Vantage for prices.
"""

import os
import time
import logging
import requests
import yfinance as yf
import pandas as pd
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from dotenv import load_dotenv

from error_handling import (
    CircuitBreaker, RateLimiter, retry_with_backoff,
    APIRateLimitError, APITimeoutError, APIBadResponseError,
    DataNotAvailableError, health_monitor,
)

load_dotenv()
logger = logging.getLogger("finai.api_clients")

# ─── Circuit Breakers & Rate Limiters ─────────────────────────────────────────

_breakers = {
    "yfinance":       CircuitBreaker("yfinance",       failure_threshold=10, recovery_timeout=30),
    "alpha_vantage":  CircuitBreaker("alpha_vantage",   failure_threshold=5,  recovery_timeout=120),
    "newsapi":        CircuitBreaker("newsapi",         failure_threshold=5,  recovery_timeout=60),
    "exchangerate":   CircuitBreaker("exchangerate",    failure_threshold=5,  recovery_timeout=120),
    "fred":           CircuitBreaker("fred",            failure_threshold=5,  recovery_timeout=120),
}

_limiters = {
    "yfinance":       RateLimiter(max_tokens=60, refill_period=60),     # 60/min
    "alpha_vantage":  RateLimiter(max_tokens=5,  refill_period=60),     # 5/min (free tier)
    "newsapi":        RateLimiter(max_tokens=10, refill_period=60),     # conservative
    "exchangerate":   RateLimiter(max_tokens=10, refill_period=60),
    "fred":           RateLimiter(max_tokens=10, refill_period=60),
}

# Register with health monitor
for name in _breakers:
    health_monitor.register(name, _breakers[name], _limiters[name])

# ─── API Keys ─────────────────────────────────────────────────────────────────

ALPHA_VANTAGE_KEY = os.getenv("ALPHA_VANTAGE_API_KEY", "")
NEWSAPI_KEY = os.getenv("NEWSAPI_KEY", "7b74b92a008c43d7a0e8fc6f8712d2f2")


def _check_rate_limit(api_name: str):
    limiter = _limiters.get(api_name)
    if limiter and not limiter.acquire():
        raise APIRateLimitError(api_name)


def _timed_request(api_name: str, url: str, params: dict = None, timeout: float = 15) -> dict:
    """Make a GET request with timing, error handling, and circuit breaker integration."""
    _check_rate_limit(api_name)
    breaker = _breakers[api_name]
    if not breaker.can_execute():
        from error_handling import CircuitOpenError
        raise CircuitOpenError(api_name, breaker.get_status().get("reset_at", "unknown"))

    start = time.time()
    try:
        resp = requests.get(url, params=params, timeout=timeout)
        latency = (time.time() - start) * 1000
        health_monitor.record_latency(api_name, round(latency, 1))

        if resp.status_code == 429:
            breaker.record_failure()
            raise APIRateLimitError(api_name)
        if resp.status_code >= 400:
            breaker.record_failure()
            raise APIBadResponseError(api_name, resp.status_code, resp.text)

        data = resp.json()
        breaker.record_success()
        return data

    except requests.Timeout:
        breaker.record_failure()
        raise APITimeoutError(api_name, timeout)
    except requests.ConnectionError as e:
        breaker.record_failure()
        raise APIBadResponseError(api_name, 0, str(e))
    except (APIRateLimitError, APITimeoutError, APIBadResponseError):
        raise
    except Exception as e:
        breaker.record_failure()
        raise APIBadResponseError(api_name, 0, str(e))


# ═══════════════════════════════════════════════════════════════════════════════
# 1. YAHOO FINANCE CLIENT
# ═══════════════════════════════════════════════════════════════════════════════

class YFinanceClient:
    """Wrapper around yfinance with circuit breaker and error handling."""

    @staticmethod
    @retry_with_backoff(max_retries=2, base_delay=1, exceptions=(Exception,), circuit_breaker=_breakers["yfinance"])
    def get_price_history(symbol: str, period: str = "1mo", interval: str = None) -> pd.DataFrame:
        _check_rate_limit("yfinance")
        ticker = yf.Ticker(symbol)
        if period == "1d" and not interval:
            interval = "5m"
        kwargs = {"period": period}
        if interval:
            kwargs["interval"] = interval
        data = ticker.history(**kwargs)
        if data.empty:
            raise DataNotAvailableError(symbol, "price")
        return data

    @staticmethod
    @retry_with_backoff(max_retries=2, base_delay=1, exceptions=(Exception,), circuit_breaker=_breakers["yfinance"])
    def get_info(symbol: str) -> dict:
        _check_rate_limit("yfinance")
        ticker = yf.Ticker(symbol)
        info = ticker.info
        if not info or info.get("regularMarketPrice") is None:
            # Some symbols have limited info, still usable
            pass
        return info

    @staticmethod
    @retry_with_backoff(max_retries=1, base_delay=1, exceptions=(Exception,), circuit_breaker=_breakers["yfinance"])
    def get_options_chain(symbol: str, expiry: str = None) -> dict:
        """Fetch options chain for a symbol."""
        _check_rate_limit("yfinance")
        ticker = yf.Ticker(symbol)
        expirations = ticker.options
        if not expirations:
            raise DataNotAvailableError(symbol, "options")

        target_exp = expiry if expiry and expiry in expirations else expirations[0]
        chain = ticker.option_chain(target_exp)
        return {
            "expirations": list(expirations),
            "selected": target_exp,
            "calls": chain.calls.to_dict(orient="records") if not chain.calls.empty else [],
            "puts": chain.puts.to_dict(orient="records") if not chain.puts.empty else [],
        }

    @staticmethod
    def get_commodity(symbol: str, period: str = "3mo") -> pd.DataFrame:
        """Fetch commodity data using yfinance futures symbols."""
        COMMODITY_MAP = {
            "gold": "GC=F",
            "silver": "SI=F",
            "crude_oil": "CL=F",
            "natural_gas": "NG=F",
            "copper": "HG=F",
            "platinum": "PL=F",
        }
        yf_sym = COMMODITY_MAP.get(symbol.lower(), symbol)
        return YFinanceClient.get_price_history(yf_sym, period)

    @staticmethod
    def get_forex(pair: str, period: str = "3mo") -> pd.DataFrame:
        """Fetch forex data. pair format: 'USDINR', 'EURUSD', etc."""
        yf_sym = f"{pair}=X"
        return YFinanceClient.get_price_history(yf_sym, period)

    @staticmethod
    def get_treasury_yield(maturity: str = "10y", period: str = "1y") -> pd.DataFrame:
        """Fetch US Treasury yield data."""
        YIELD_MAP = {
            "2y": "^IRX" if maturity == "3m" else "2YY=F",
            "5y": "^FVX",
            "10y": "^TNX",
            "30y": "^TYX",
            "3m": "^IRX",
        }
        yf_sym = YIELD_MAP.get(maturity.lower(), "^TNX")
        try:
            return YFinanceClient.get_price_history(yf_sym, period)
        except DataNotAvailableError:
            # Fallback: use yfinance Ticker
            ticker = yf.Ticker(yf_sym)
            data = ticker.history(period=period)
            return data


# ═══════════════════════════════════════════════════════════════════════════════
# 2. ALPHA VANTAGE CLIENT
# ═══════════════════════════════════════════════════════════════════════════════

class AlphaVantageClient:
    """Alpha Vantage API client with circuit breaker and rate limiting."""

    BASE_URL = "https://www.alphavantage.co/query"

    @staticmethod
    def _is_available() -> bool:
        return bool(ALPHA_VANTAGE_KEY)

    @staticmethod
    @retry_with_backoff(max_retries=2, base_delay=2, exceptions=(Exception,), circuit_breaker=_breakers["alpha_vantage"])
    def get_daily(symbol: str, outputsize: str = "compact") -> pd.DataFrame:
        if not AlphaVantageClient._is_available():
            raise DataNotAvailableError(symbol, "alpha_vantage_daily")

        data = _timed_request("alpha_vantage", AlphaVantageClient.BASE_URL, {
            "function": "TIME_SERIES_DAILY",
            "symbol": symbol,
            "outputsize": outputsize,
            "apikey": ALPHA_VANTAGE_KEY,
        })

        ts_key = "Time Series (Daily)"
        if ts_key not in data:
            if "Note" in data:  # Rate limit message
                raise APIRateLimitError("alpha_vantage", 60)
            raise DataNotAvailableError(symbol, "daily_price")

        df = pd.DataFrame.from_dict(data[ts_key], orient="index")
        df.columns = ["Open", "High", "Low", "Close", "Volume"]
        df = df.astype(float)
        df.index = pd.to_datetime(df.index)
        df = df.sort_index()
        return df

    @staticmethod
    @retry_with_backoff(max_retries=2, base_delay=2, exceptions=(Exception,), circuit_breaker=_breakers["alpha_vantage"])
    def get_technical_indicator(symbol: str, indicator: str = "RSI", interval: str = "daily",
                                 time_period: int = 14, series_type: str = "close") -> pd.DataFrame:
        if not AlphaVantageClient._is_available():
            raise DataNotAvailableError(symbol, f"alpha_vantage_{indicator}")

        data = _timed_request("alpha_vantage", AlphaVantageClient.BASE_URL, {
            "function": indicator,
            "symbol": symbol,
            "interval": interval,
            "time_period": time_period,
            "series_type": series_type,
            "apikey": ALPHA_VANTAGE_KEY,
        })

        # Find the data key (varies per indicator)
        tech_key = None
        for k in data.keys():
            if "Technical Analysis" in k:
                tech_key = k
                break

        if not tech_key:
            raise DataNotAvailableError(symbol, indicator)

        df = pd.DataFrame.from_dict(data[tech_key], orient="index").astype(float)
        df.index = pd.to_datetime(df.index)
        df = df.sort_index()
        return df

    @staticmethod
    @retry_with_backoff(max_retries=1, base_delay=2, exceptions=(Exception,), circuit_breaker=_breakers["alpha_vantage"])
    def get_forex_rate(from_currency: str, to_currency: str) -> dict:
        if not AlphaVantageClient._is_available():
            raise DataNotAvailableError(f"{from_currency}/{to_currency}", "forex")

        data = _timed_request("alpha_vantage", AlphaVantageClient.BASE_URL, {
            "function": "CURRENCY_EXCHANGE_RATE",
            "from_currency": from_currency,
            "to_currency": to_currency,
            "apikey": ALPHA_VANTAGE_KEY,
        })

        rt = data.get("Realtime Currency Exchange Rate", {})
        if not rt:
            raise DataNotAvailableError(f"{from_currency}/{to_currency}", "forex")

        return {
            "from": from_currency,
            "to": to_currency,
            "rate": float(rt.get("5. Exchange Rate", 0)),
            "last_updated": rt.get("6. Last Refreshed", ""),
            "bid": float(rt.get("8. Bid Price", 0)),
            "ask": float(rt.get("9. Ask Price", 0)),
        }

    @staticmethod
    @retry_with_backoff(max_retries=1, base_delay=2, exceptions=(Exception,), circuit_breaker=_breakers["alpha_vantage"])
    def get_commodity_price(commodity: str = "WTI", interval: str = "monthly") -> pd.DataFrame:
        if not AlphaVantageClient._is_available():
            raise DataNotAvailableError(commodity, "commodity")

        data = _timed_request("alpha_vantage", AlphaVantageClient.BASE_URL, {
            "function": commodity,
            "interval": interval,
            "apikey": ALPHA_VANTAGE_KEY,
        })

        data_key = "data"
        if data_key not in data:
            raise DataNotAvailableError(commodity, "commodity")

        records = data[data_key]
        df = pd.DataFrame(records)
        df["date"] = pd.to_datetime(df["date"])
        df["value"] = pd.to_numeric(df["value"], errors="coerce")
        df = df.dropna(subset=["value"])
        df = df.set_index("date").sort_index()
        return df


# ═══════════════════════════════════════════════════════════════════════════════
# 3. NEWS API CLIENT
# ═══════════════════════════════════════════════════════════════════════════════

class NewsAPIClient:
    """NewsAPI client with circuit breaker."""

    BASE_URL = "https://newsapi.org/v2/everything"

    @staticmethod
    @retry_with_backoff(max_retries=2, base_delay=1, exceptions=(Exception,), circuit_breaker=_breakers["newsapi"])
    def get_news(query: str, page_size: int = 8, language: str = "en") -> dict:
        data = _timed_request("newsapi", NewsAPIClient.BASE_URL, {
            "q": query,
            "pageSize": page_size,
            "language": language,
            "apiKey": NEWSAPI_KEY,
        })

        if data.get("status") != "ok":
            raise APIBadResponseError("newsapi", 0, str(data))

        return {
            "total": data.get("totalResults", 0),
            "articles": data.get("articles", []),
        }


# ═══════════════════════════════════════════════════════════════════════════════
# 4. FREE EXCHANGE RATE API CLIENT
# ═══════════════════════════════════════════════════════════════════════════════

class ExchangeRateClient:
    """Free exchange rate API (no key required)."""

    BASE_URL = "https://open.er-api.com/v6/latest"

    @staticmethod
    @retry_with_backoff(max_retries=2, base_delay=1, exceptions=(Exception,), circuit_breaker=_breakers["exchangerate"])
    def get_rates(base: str = "USD") -> dict:
        data = _timed_request("exchangerate", f"{ExchangeRateClient.BASE_URL}/{base}")
        if data.get("result") != "success":
            raise APIBadResponseError("exchangerate", 0, str(data))
        return {
            "base": base,
            "rates": data.get("rates", {}),
            "last_updated": data.get("time_last_update_utc", ""),
        }


# ═══════════════════════════════════════════════════════════════════════════════
# 5. MACRO DATA (FRED-like, via Alpha Vantage)
# ═══════════════════════════════════════════════════════════════════════════════

class MacroDataClient:
    """
    Macro-economic indicators via Alpha Vantage economic functions
    and yfinance index data.
    """

    @staticmethod
    def get_treasury_yields() -> dict:
        """Get current US Treasury yields at different maturities."""
        yields = {}
        maturities = {"3m": "^IRX", "5y": "^FVX", "10y": "^TNX", "30y": "^TYX"}
        for label, sym in maturities.items():
            try:
                ticker = yf.Ticker(sym)
                data = ticker.history(period="5d")
                if not data.empty:
                    yields[label] = round(float(data["Close"].iloc[-1]), 3)
            except Exception:
                yields[label] = None
        return yields

    @staticmethod
    def get_yield_curve() -> list:
        """Get yield curve data points."""
        maturities = [
            ("1M", "^IRX"),
            ("3M", "^IRX"),
            ("6M", "^IRX"),
            ("1Y", "^IRX"),
            ("2Y", "2YY=F"),
            ("5Y", "^FVX"),
            ("10Y", "^TNX"),
            ("30Y", "^TYX"),
        ]
        curve = []
        for label, sym in maturities:
            try:
                ticker = yf.Ticker(sym)
                data = ticker.history(period="5d")
                if not data.empty:
                    curve.append({"maturity": label, "yield": round(float(data["Close"].iloc[-1]), 3)})
            except Exception:
                continue
        return curve

    @staticmethod
    def get_market_indices() -> dict:
        """Get major global indices."""
        indices = {
            "NIFTY_50": "^NSEI",
            "SENSEX": "^BSESN",
            "SP500": "^GSPC",
            "NASDAQ": "^IXIC",
            "DOW": "^DJI",
            "VIX": "^VIX",
            "FTSE": "^FTSE",
            "NIKKEI": "^N225",
        }
        result = {}
        for name, sym in indices.items():
            try:
                ticker = yf.Ticker(sym)
                data = ticker.history(period="2d")
                if not data.empty and len(data) >= 2:
                    close = float(data["Close"].iloc[-1])
                    prev = float(data["Close"].iloc[-2])
                    change = close - prev
                    pct = (change / prev) * 100
                    result[name] = {
                        "price": round(close, 2),
                        "change": round(change, 2),
                        "change_pct": round(pct, 2),
                    }
            except Exception:
                continue
        return result

    @staticmethod
    def get_macro_indicators() -> dict:
        """Get macro-economic indicators via Alpha Vantage if available."""
        indicators = {}

        if ALPHA_VANTAGE_KEY:
            functions = {
                "real_gdp": "REAL_GDP",
                "cpi": "CPI",
                "inflation": "INFLATION",
                "unemployment": "UNEMPLOYMENT",
                "federal_funds_rate": "FEDERAL_FUNDS_RATE",
            }
            for key, func in functions.items():
                try:
                    data = _timed_request("alpha_vantage", AlphaVantageClient.BASE_URL, {
                        "function": func,
                        "apikey": ALPHA_VANTAGE_KEY,
                    })
                    records = data.get("data", [])
                    if records:
                        latest = records[0]
                        indicators[key] = {
                            "value": float(latest.get("value", 0)),
                            "date": latest.get("date", ""),
                        }
                except Exception as e:
                    logger.warning(f"Could not fetch {key}: {e}")
                    indicators[key] = None

        return indicators


# ═══════════════════════════════════════════════════════════════════════════════
# FALLBACK CHAINS
# ═══════════════════════════════════════════════════════════════════════════════

def get_price_with_fallback(symbol: str, period: str = "1mo") -> pd.DataFrame:
    """Try yfinance first, then Alpha Vantage."""
    errors = []

    # Try yfinance
    try:
        return YFinanceClient.get_price_history(symbol, period)
    except Exception as e:
        errors.append(f"yfinance: {e}")
        logger.warning(f"yfinance failed for {symbol}: {e}")

    # Try Alpha Vantage (daily only)
    if ALPHA_VANTAGE_KEY:
        try:
            df = AlphaVantageClient.get_daily(symbol, "full" if period in ("1y", "5y") else "compact")
            # Filter by period
            days_map = {"1d": 1, "5d": 5, "1mo": 30, "3mo": 90, "6mo": 180, "1y": 365, "5y": 1825}
            days = days_map.get(period, 30)
            cutoff = datetime.now() - timedelta(days=days)
            return df[df.index >= cutoff]
        except Exception as e:
            errors.append(f"alpha_vantage: {e}")
            logger.warning(f"Alpha Vantage failed for {symbol}: {e}")

    raise DataNotAvailableError(symbol, f"price (tried: {'; '.join(errors)})")


def get_forex_with_fallback(pair: str) -> dict:
    """Try yfinance forex, then Alpha Vantage, then ExchangeRate API."""
    from_cur = pair[:3].upper()
    to_cur = pair[3:].upper()

    # Try yfinance
    try:
        df = YFinanceClient.get_forex(pair, "5d")
        if not df.empty:
            return {
                "from": from_cur, "to": to_cur,
                "rate": round(float(df["Close"].iloc[-1]), 4),
                "last_updated": str(df.index[-1]),
                "source": "yfinance",
            }
    except Exception:
        pass

    # Try Alpha Vantage
    if ALPHA_VANTAGE_KEY:
        try:
            result = AlphaVantageClient.get_forex_rate(from_cur, to_cur)
            result["source"] = "alpha_vantage"
            return result
        except Exception:
            pass

    # Try free exchange rate API
    try:
        rates = ExchangeRateClient.get_rates(from_cur)
        rate = rates["rates"].get(to_cur)
        if rate:
            return {
                "from": from_cur, "to": to_cur,
                "rate": round(float(rate), 4),
                "last_updated": rates["last_updated"],
                "source": "exchangerate",
            }
    except Exception:
        pass

    raise DataNotAvailableError(pair, "forex_rate")
