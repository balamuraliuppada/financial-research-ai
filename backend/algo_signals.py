"""
algo_signals.py
───────────────
Algorithmic trading signal engine.
Signal categories:
  - Momentum: RSI, MACD, Stochastic
  - Trend: EMA crossovers, ADX, Supertrend
  - Volatility: Bollinger Bands, ATR
  - Volume: OBV, VWAP
  - Pattern: Head & Shoulders, Double Top/Bottom (simplified)
  - Composite Score: weighted aggregate → BUY / SELL / HOLD with confidence
"""

import numpy as np
import pandas as pd
import yfinance as yf
from typing import Dict, List, Optional
import logging

logger = logging.getLogger("finai.signals")


# ─── Technical Indicator Computation ──────────────────────────────────────────

def compute_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))


def compute_macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Dict:
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return {"macd": macd_line, "signal": signal_line, "histogram": histogram}


def compute_stochastic(data: pd.DataFrame, k_period: int = 14, d_period: int = 3) -> Dict:
    low_min = data["Low"].rolling(window=k_period).min()
    high_max = data["High"].rolling(window=k_period).max()
    k = 100 * ((data["Close"] - low_min) / (high_max - low_min))
    d = k.rolling(window=d_period).mean()
    return {"k": k, "d": d}


def compute_adx(data: pd.DataFrame, period: int = 14) -> pd.Series:
    high = data["High"]
    low = data["Low"]
    close = data["Close"]

    plus_dm = high.diff()
    minus_dm = -low.diff()
    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0)

    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    atr = tr.rolling(window=period).mean()
    plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr)
    minus_di = 100 * (minus_dm.rolling(window=period).mean() / atr)

    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
    adx = dx.rolling(window=period).mean()
    return adx


def compute_bollinger(close: pd.Series, period: int = 20, std_dev: int = 2) -> Dict:
    sma = close.rolling(window=period).mean()
    std = close.rolling(window=period).std()
    upper = sma + std_dev * std
    lower = sma - std_dev * std
    bandwidth = ((upper - lower) / sma * 100)
    pct_b = (close - lower) / (upper - lower)
    return {"upper": upper, "lower": lower, "mid": sma, "bandwidth": bandwidth, "pct_b": pct_b}


def compute_atr(data: pd.DataFrame, period: int = 14) -> pd.Series:
    high = data["High"]
    low = data["Low"]
    close = data["Close"]
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()


def compute_obv(data: pd.DataFrame) -> pd.Series:
    obv = pd.Series(0, index=data.index, dtype=float)
    for i in range(1, len(data)):
        if data["Close"].iloc[i] > data["Close"].iloc[i - 1]:
            obv.iloc[i] = obv.iloc[i - 1] + data["Volume"].iloc[i]
        elif data["Close"].iloc[i] < data["Close"].iloc[i - 1]:
            obv.iloc[i] = obv.iloc[i - 1] - data["Volume"].iloc[i]
        else:
            obv.iloc[i] = obv.iloc[i - 1]
    return obv


def compute_vwap(data: pd.DataFrame) -> pd.Series:
    typical_price = (data["High"] + data["Low"] + data["Close"]) / 3
    return (typical_price * data["Volume"]).cumsum() / data["Volume"].cumsum()


def compute_supertrend(data: pd.DataFrame, period: int = 10, multiplier: float = 3.0) -> Dict:
    atr = compute_atr(data, period)
    hl2 = (data["High"] + data["Low"]) / 2
    upper_band = hl2 + multiplier * atr
    lower_band = hl2 - multiplier * atr

    supertrend = pd.Series(0.0, index=data.index)
    direction = pd.Series(1, index=data.index)  # 1=up, -1=down

    for i in range(1, len(data)):
        if data["Close"].iloc[i] > upper_band.iloc[i - 1]:
            direction.iloc[i] = 1
        elif data["Close"].iloc[i] < lower_band.iloc[i - 1]:
            direction.iloc[i] = -1
        else:
            direction.iloc[i] = direction.iloc[i - 1]

        if direction.iloc[i] == 1:
            supertrend.iloc[i] = lower_band.iloc[i]
        else:
            supertrend.iloc[i] = upper_band.iloc[i]

    return {"supertrend": supertrend, "direction": direction}


# ─── Signal Generation ───────────────────────────────────────────────────────

def _signal_rsi(close: pd.Series) -> Dict:
    rsi = compute_rsi(close)
    val = float(rsi.iloc[-1])
    if val > 70:
        return {"name": "RSI", "signal": "SELL", "value": round(val, 2), "strength": min((val - 70) / 30, 1), "reason": f"RSI {val:.1f} — overbought"}
    elif val < 30:
        return {"name": "RSI", "signal": "BUY", "value": round(val, 2), "strength": min((30 - val) / 30, 1), "reason": f"RSI {val:.1f} — oversold"}
    else:
        return {"name": "RSI", "signal": "HOLD", "value": round(val, 2), "strength": 0, "reason": f"RSI {val:.1f} — neutral zone"}


def _signal_macd(close: pd.Series) -> Dict:
    macd = compute_macd(close)
    macd_val = float(macd["macd"].iloc[-1])
    signal_val = float(macd["signal"].iloc[-1])
    hist = float(macd["histogram"].iloc[-1])
    prev_hist = float(macd["histogram"].iloc[-2]) if len(macd["histogram"]) > 1 else 0

    if macd_val > signal_val and prev_hist <= 0 < hist:
        return {"name": "MACD", "signal": "BUY", "value": round(hist, 4), "strength": 0.8, "reason": "MACD bullish crossover"}
    elif macd_val < signal_val and prev_hist >= 0 > hist:
        return {"name": "MACD", "signal": "SELL", "value": round(hist, 4), "strength": 0.8, "reason": "MACD bearish crossover"}
    elif hist > 0:
        return {"name": "MACD", "signal": "BUY", "value": round(hist, 4), "strength": 0.3, "reason": "MACD histogram positive"}
    elif hist < 0:
        return {"name": "MACD", "signal": "SELL", "value": round(hist, 4), "strength": 0.3, "reason": "MACD histogram negative"}
    return {"name": "MACD", "signal": "HOLD", "value": round(hist, 4), "strength": 0, "reason": "MACD neutral"}


def _signal_stochastic(data: pd.DataFrame) -> Dict:
    stoch = compute_stochastic(data)
    k = float(stoch["k"].iloc[-1])
    d = float(stoch["d"].iloc[-1])

    if k < 20 and d < 20:
        return {"name": "Stochastic", "signal": "BUY", "value": round(k, 2), "strength": 0.7, "reason": f"Stochastic K={k:.1f}, D={d:.1f} — oversold"}
    elif k > 80 and d > 80:
        return {"name": "Stochastic", "signal": "SELL", "value": round(k, 2), "strength": 0.7, "reason": f"Stochastic K={k:.1f}, D={d:.1f} — overbought"}
    return {"name": "Stochastic", "signal": "HOLD", "value": round(k, 2), "strength": 0, "reason": f"Stochastic K={k:.1f} — neutral"}


def _signal_ema_crossover(close: pd.Series) -> Dict:
    ema9 = close.ewm(span=9, adjust=False).mean()
    ema21 = close.ewm(span=21, adjust=False).mean()
    ema50 = close.ewm(span=50, adjust=False).mean()

    e9 = float(ema9.iloc[-1])
    e21 = float(ema21.iloc[-1])
    e50 = float(ema50.iloc[-1])

    if e9 > e21 > e50:
        return {"name": "EMA Crossover", "signal": "BUY", "value": round(e9, 2), "strength": 0.7, "reason": "EMA 9 > 21 > 50 — strong uptrend"}
    elif e9 < e21 < e50:
        return {"name": "EMA Crossover", "signal": "SELL", "value": round(e9, 2), "strength": 0.7, "reason": "EMA 9 < 21 < 50 — strong downtrend"}
    return {"name": "EMA Crossover", "signal": "HOLD", "value": round(e9, 2), "strength": 0.2, "reason": "EMA alignment mixed — no clear trend"}


def _signal_adx(data: pd.DataFrame) -> Dict:
    adx = compute_adx(data)
    val = float(adx.iloc[-1]) if not pd.isna(adx.iloc[-1]) else 0

    if val > 25:
        # Strong trend — determine direction from price action
        price_change = float(data["Close"].iloc[-1] - data["Close"].iloc[-5])
        if price_change > 0:
            return {"name": "ADX", "signal": "BUY", "value": round(val, 2), "strength": min(val / 50, 1), "reason": f"ADX {val:.1f} — strong uptrend"}
        else:
            return {"name": "ADX", "signal": "SELL", "value": round(val, 2), "strength": min(val / 50, 1), "reason": f"ADX {val:.1f} — strong downtrend"}
    return {"name": "ADX", "signal": "HOLD", "value": round(val, 2), "strength": 0, "reason": f"ADX {val:.1f} — weak trend"}


def _signal_bollinger(close: pd.Series) -> Dict:
    bb = compute_bollinger(close)
    price = float(close.iloc[-1])
    upper = float(bb["upper"].iloc[-1])
    lower = float(bb["lower"].iloc[-1])
    pct_b = float(bb["pct_b"].iloc[-1])
    bw = float(bb["bandwidth"].iloc[-1])

    if price > upper:
        return {"name": "Bollinger Bands", "signal": "SELL", "value": round(pct_b, 3), "strength": 0.6, "reason": f"Price above upper band — %B={pct_b:.2f}"}
    elif price < lower:
        return {"name": "Bollinger Bands", "signal": "BUY", "value": round(pct_b, 3), "strength": 0.6, "reason": f"Price below lower band — %B={pct_b:.2f}"}

    # Squeeze detection
    if bw < 5:
        return {"name": "Bollinger Bands", "signal": "HOLD", "value": round(bw, 2), "strength": 0.4, "reason": f"Bollinger squeeze (BW={bw:.1f}%) — breakout imminent"}

    return {"name": "Bollinger Bands", "signal": "HOLD", "value": round(pct_b, 3), "strength": 0, "reason": f"Price within bands — %B={pct_b:.2f}"}


def _signal_obv(data: pd.DataFrame) -> Dict:
    obv = compute_obv(data)
    obv_sma = obv.rolling(20).mean()
    current_obv = float(obv.iloc[-1])
    sma_obv = float(obv_sma.iloc[-1]) if not pd.isna(obv_sma.iloc[-1]) else current_obv

    if current_obv > sma_obv * 1.05:
        return {"name": "OBV", "signal": "BUY", "value": round(current_obv, 0), "strength": 0.4, "reason": "OBV above 20-day average — accumulation"}
    elif current_obv < sma_obv * 0.95:
        return {"name": "OBV", "signal": "SELL", "value": round(current_obv, 0), "strength": 0.4, "reason": "OBV below 20-day average — distribution"}
    return {"name": "OBV", "signal": "HOLD", "value": round(current_obv, 0), "strength": 0, "reason": "OBV stable"}


def _signal_supertrend(data: pd.DataFrame) -> Dict:
    st = compute_supertrend(data)
    direction = int(st["direction"].iloc[-1])
    prev_dir = int(st["direction"].iloc[-2]) if len(st["direction"]) > 1 else direction

    if direction == 1 and prev_dir == -1:
        return {"name": "Supertrend", "signal": "BUY", "value": direction, "strength": 0.8, "reason": "Supertrend flipped bullish ↑"}
    elif direction == -1 and prev_dir == 1:
        return {"name": "Supertrend", "signal": "SELL", "value": direction, "strength": 0.8, "reason": "Supertrend flipped bearish ↓"}
    elif direction == 1:
        return {"name": "Supertrend", "signal": "BUY", "value": direction, "strength": 0.4, "reason": "Supertrend bullish"}
    else:
        return {"name": "Supertrend", "signal": "SELL", "value": direction, "strength": 0.4, "reason": "Supertrend bearish"}


def _signal_vwap(data: pd.DataFrame) -> Dict:
    vwap = compute_vwap(data)
    price = float(data["Close"].iloc[-1])
    vwap_val = float(vwap.iloc[-1])

    if price > vwap_val * 1.01:
        return {"name": "VWAP", "signal": "BUY", "value": round(vwap_val, 2), "strength": 0.3, "reason": f"Price above VWAP (₹{vwap_val:.2f}) — bullish"}
    elif price < vwap_val * 0.99:
        return {"name": "VWAP", "signal": "SELL", "value": round(vwap_val, 2), "strength": 0.3, "reason": f"Price below VWAP (₹{vwap_val:.2f}) — bearish"}
    return {"name": "VWAP", "signal": "HOLD", "value": round(vwap_val, 2), "strength": 0, "reason": "Price near VWAP — neutral"}


# ─── Composite Signal Engine ─────────────────────────────────────────────────

SIGNAL_WEIGHTS = {
    "RSI": 0.12,
    "MACD": 0.15,
    "Stochastic": 0.08,
    "EMA Crossover": 0.12,
    "ADX": 0.10,
    "Bollinger Bands": 0.10,
    "OBV": 0.08,
    "Supertrend": 0.15,
    "VWAP": 0.10,
}


def generate_signals(symbol: str, period: str = "6mo") -> Dict:
    """
    Generate all trading signals for a symbol and compute composite score.
    Returns individual signals + weighted composite.
    """
    try:
        ticker = yf.Ticker(symbol)
        data = ticker.history(period=period)
        if data.empty or len(data) < 50:
            return {"error": f"Insufficient data for {symbol} (need 50+ days)"}

        close = data["Close"]

        # Generate individual signals
        signals = []
        signal_funcs = [
            lambda: _signal_rsi(close),
            lambda: _signal_macd(close),
            lambda: _signal_stochastic(data),
            lambda: _signal_ema_crossover(close),
            lambda: _signal_adx(data),
            lambda: _signal_bollinger(close),
            lambda: _signal_obv(data),
            lambda: _signal_supertrend(data),
            lambda: _signal_vwap(data),
        ]

        for func in signal_funcs:
            try:
                sig = func()
                signals.append(sig)
            except Exception as e:
                logger.warning(f"Signal error for {symbol}: {e}")

        # Compute composite score
        # BUY = +1, SELL = -1, HOLD = 0, weighted by strength and signal weight
        weighted_score = 0
        total_weight = 0
        buy_count = 0
        sell_count = 0
        hold_count = 0

        for sig in signals:
            w = SIGNAL_WEIGHTS.get(sig["name"], 0.1)
            strength = sig.get("strength", 0.5)
            if sig["signal"] == "BUY":
                weighted_score += w * strength
                buy_count += 1
            elif sig["signal"] == "SELL":
                weighted_score -= w * strength
                sell_count += 1
            else:
                hold_count += 1
            total_weight += w

        # Normalize to -1 to +1
        if total_weight > 0:
            composite = weighted_score / total_weight
        else:
            composite = 0

        # Determine overall signal
        if composite > 0.25:
            overall = "STRONG BUY" if composite > 0.5 else "BUY"
        elif composite < -0.25:
            overall = "STRONG SELL" if composite < -0.5 else "SELL"
        else:
            overall = "HOLD"

        confidence = round(abs(composite) * 100, 1)

        # Current price info
        current_price = round(float(close.iloc[-1]), 2)
        prev_price = round(float(close.iloc[-2]), 2) if len(close) > 1 else current_price

        return {
            "symbol": symbol,
            "current_price": current_price,
            "price_change": round(current_price - prev_price, 2),
            "price_change_pct": round(((current_price - prev_price) / prev_price) * 100, 2) if prev_price else 0,
            "signals": signals,
            "composite": {
                "score": round(composite, 4),
                "signal": overall,
                "confidence": confidence,
                "buy_signals": buy_count,
                "sell_signals": sell_count,
                "hold_signals": hold_count,
            },
            "summary": f"{overall} ({confidence}% confidence) • {buy_count} buy / {sell_count} sell / {hold_count} hold signals",
        }

    except Exception as e:
        logger.error(f"Signal generation error for {symbol}: {e}")
        return {"error": str(e)}


def get_signal_summary(symbol: str) -> Dict:
    """Quick summary — just the composite signal."""
    result = generate_signals(symbol)
    if "error" in result:
        return result
    return {
        "symbol": symbol,
        "signal": result["composite"]["signal"],
        "confidence": result["composite"]["confidence"],
        "score": result["composite"]["score"],
        "price": result["current_price"],
    }


def batch_signals(symbols: List[str]) -> List[Dict]:
    """Generate signal summaries for multiple symbols."""
    results = []
    for sym in symbols:
        try:
            results.append(get_signal_summary(sym))
        except Exception as e:
            results.append({"symbol": sym, "error": str(e)})
    return results
