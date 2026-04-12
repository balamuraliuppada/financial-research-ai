"""
alerts.py
─────────
Real-time market alert engine & notification system.
Supports: price thresholds, RSI levels, volume spikes, MA crossovers, Bollinger breakouts.
Background checker + WebSocket push.
"""

import asyncio
import json
import logging
import yfinance as yf
import pandas as pd
from datetime import datetime
from typing import List, Dict, Set, Optional
from models import (
    SessionLocal, Alert, Notification, AlertStatus, AlertType,
)

logger = logging.getLogger("finai.alerts")


# ─── WebSocket Connection Manager ────────────────────────────────────────────

class ConnectionManager:
    """Manages active WebSocket connections for real-time alert pushes."""

    def __init__(self):
        self.active_connections: list = []

    async def connect(self, websocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total: {len(self.active_connections)}")

    def disconnect(self, websocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        """Send a message to all connected clients."""
        dead = []
        for conn in self.active_connections:
            try:
                await conn.send_json(message)
            except Exception:
                dead.append(conn)
        for conn in dead:
            self.disconnect(conn)

    async def send_personal(self, websocket, message: dict):
        try:
            await websocket.send_json(message)
        except Exception:
            self.disconnect(websocket)


ws_manager = ConnectionManager()


# ─── Alert Evaluation Functions ───────────────────────────────────────────────

def _get_current_price(symbol: str) -> Optional[float]:
    try:
        ticker = yf.Ticker(symbol)
        data = ticker.history(period="1d", interval="1m")
        if not data.empty:
            return float(data["Close"].iloc[-1])
        data = ticker.history(period="2d")
        if not data.empty:
            return float(data["Close"].iloc[-1])
    except Exception as e:
        logger.warning(f"Could not fetch price for {symbol}: {e}")
    return None


def _get_rsi(symbol: str, period: int = 14) -> Optional[float]:
    try:
        ticker = yf.Ticker(symbol)
        data = ticker.history(period="3mo")
        if data.empty or len(data) < period + 1:
            return None
        delta = data["Close"].diff()
        gain = delta.where(delta > 0, 0).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return float(rsi.iloc[-1])
    except Exception:
        return None


def _get_volume_ratio(symbol: str) -> Optional[float]:
    """Current volume / 20-day average volume."""
    try:
        ticker = yf.Ticker(symbol)
        data = ticker.history(period="1mo")
        if data.empty or len(data) < 5:
            return None
        avg_vol = data["Volume"].iloc[:-1].rolling(20).mean().iloc[-1]
        current_vol = float(data["Volume"].iloc[-1])
        if avg_vol > 0:
            return current_vol / avg_vol
    except Exception:
        return None
    return None


def _check_ma_crossover(symbol: str) -> Optional[str]:
    """Check for MA crossover signals. Returns 'bullish', 'bearish', or None."""
    try:
        ticker = yf.Ticker(symbol)
        data = ticker.history(period="6mo")
        if data.empty or len(data) < 50:
            return None
        ma20 = data["Close"].rolling(20).mean()
        ma50 = data["Close"].rolling(50).mean()
        # Golden cross: short MA crosses above long MA
        if ma20.iloc[-1] > ma50.iloc[-1] and ma20.iloc[-2] <= ma50.iloc[-2]:
            return "bullish"
        # Death cross: short MA crosses below long MA
        if ma20.iloc[-1] < ma50.iloc[-1] and ma20.iloc[-2] >= ma50.iloc[-2]:
            return "bearish"
    except Exception:
        pass
    return None


def _check_bollinger_breakout(symbol: str) -> Optional[str]:
    """Check if price breaks above upper or below lower Bollinger Band."""
    try:
        ticker = yf.Ticker(symbol)
        data = ticker.history(period="3mo")
        if data.empty or len(data) < 20:
            return None
        sma = data["Close"].rolling(20).mean()
        std = data["Close"].rolling(20).std()
        upper = sma + 2 * std
        lower = sma - 2 * std
        price = float(data["Close"].iloc[-1])
        if price > float(upper.iloc[-1]):
            return "above_upper"
        if price < float(lower.iloc[-1]):
            return "below_lower"
    except Exception:
        pass
    return None


# ─── Alert Evaluator ─────────────────────────────────────────────────────────

def evaluate_alert(alert: Alert) -> Optional[Dict]:
    """
    Evaluate a single alert against current market data.
    Returns a trigger dict if the condition is met, else None.
    """
    symbol = alert.symbol
    alert_type = alert.alert_type
    threshold = alert.threshold

    if alert_type == "price_above":
        price = _get_current_price(symbol)
        if price is not None and threshold is not None and price >= threshold:
            return {
                "triggered_value": price,
                "message": f"🔔 {symbol} price ₹{price:.2f} crossed above ₹{threshold:.2f}",
            }

    elif alert_type == "price_below":
        price = _get_current_price(symbol)
        if price is not None and threshold is not None and price <= threshold:
            return {
                "triggered_value": price,
                "message": f"🔔 {symbol} price ₹{price:.2f} dropped below ₹{threshold:.2f}",
            }

    elif alert_type == "rsi_overbought":
        rsi = _get_rsi(symbol)
        rsi_thresh = threshold or 70
        if rsi is not None and rsi >= rsi_thresh:
            return {
                "triggered_value": rsi,
                "message": f"⚠️ {symbol} RSI is {rsi:.1f} — overbought (above {rsi_thresh})",
            }

    elif alert_type == "rsi_oversold":
        rsi = _get_rsi(symbol)
        rsi_thresh = threshold or 30
        if rsi is not None and rsi <= rsi_thresh:
            return {
                "triggered_value": rsi,
                "message": f"📉 {symbol} RSI is {rsi:.1f} — oversold (below {rsi_thresh})",
            }

    elif alert_type == "volume_spike":
        ratio = _get_volume_ratio(symbol)
        spike_thresh = threshold or 2.0  # 2x average
        if ratio is not None and ratio >= spike_thresh:
            return {
                "triggered_value": ratio,
                "message": f"📊 {symbol} volume spike! {ratio:.1f}x average volume",
            }

    elif alert_type == "ma_crossover":
        signal = _check_ma_crossover(symbol)
        if signal:
            return {
                "triggered_value": 1 if signal == "bullish" else -1,
                "message": f"{'📈 Golden' if signal == 'bullish' else '📉 Death'} Cross detected on {symbol} (20/50 MA)",
            }

    elif alert_type == "bollinger_breakout":
        breakout = _check_bollinger_breakout(symbol)
        if breakout:
            direction = "above upper band ↑" if breakout == "above_upper" else "below lower band ↓"
            return {
                "triggered_value": 1 if breakout == "above_upper" else -1,
                "message": f"💥 {symbol} Bollinger Breakout — price {direction}",
            }

    elif alert_type == "percent_change":
        price = _get_current_price(symbol)
        if price is not None:
            try:
                ticker = yf.Ticker(symbol)
                data = ticker.history(period="2d")
                if len(data) >= 2:
                    prev = float(data["Close"].iloc[-2])
                    pct = ((price - prev) / prev) * 100
                    pct_thresh = threshold or 5
                    if abs(pct) >= pct_thresh:
                        direction = "up" if pct > 0 else "down"
                        return {
                            "triggered_value": round(pct, 2),
                            "message": f"📢 {symbol} moved {direction} {abs(pct):.1f}% (threshold: {pct_thresh}%)",
                        }
            except Exception:
                pass

    return None


# ─── Alert Engine (Background Task) ──────────────────────────────────────────

class AlertEngine:
    """Background alert checker that runs periodically."""

    def __init__(self, check_interval: int = 60):
        self.check_interval = check_interval
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self):
        """Start the background alert checking loop."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info(f"Alert engine started (interval={self.check_interval}s)")

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Alert engine stopped")

    async def _run_loop(self):
        while self._running:
            try:
                await self._check_all_alerts()
            except Exception as e:
                logger.error(f"Alert check error: {e}")
            await asyncio.sleep(self.check_interval)

    async def _check_all_alerts(self):
        session = SessionLocal()
        try:
            active_alerts = session.query(Alert).filter(Alert.status == "active").all()
            if not active_alerts:
                return

            logger.info(f"Checking {len(active_alerts)} active alerts...")

            for alert in active_alerts:
                try:
                    result = evaluate_alert(alert)
                    if result:
                        # Trigger the alert
                        alert.status = "triggered"
                        alert.triggered_value = result["triggered_value"]
                        alert.triggered_at = datetime.utcnow()

                        # Create notification
                        notif = Notification(
                            user_id=alert.user_id,
                            alert_id=alert.id,
                            message=result["message"],
                        )
                        session.add(notif)
                        session.commit()

                        # Push via WebSocket
                        await ws_manager.broadcast({
                            "type": "alert_triggered",
                            "alert_id": alert.id,
                            "symbol": alert.symbol,
                            "message": result["message"],
                            "triggered_value": result["triggered_value"],
                            "timestamp": datetime.utcnow().isoformat(),
                        })

                        logger.info(f"Alert #{alert.id} triggered: {result['message']}")

                except Exception as e:
                    logger.warning(f"Error checking alert #{alert.id}: {e}")

        except Exception as e:
            logger.error(f"Alert engine DB error: {e}")
        finally:
            session.close()


# Singleton alert engine
alert_engine = AlertEngine(check_interval=60)


# ─── CRUD Helpers ─────────────────────────────────────────────────────────────

def create_alert(symbol: str, alert_type: str, threshold: float = None,
                 condition: str = "", user_id: int = 1) -> Dict:
    session = SessionLocal()
    try:
        alert = Alert(
            user_id=user_id,
            symbol=symbol.upper(),
            alert_type=alert_type,
            threshold=threshold,
            condition=condition or f"{alert_type} @ {threshold}",
            status="active",
        )
        session.add(alert)
        session.commit()
        session.refresh(alert)
        return alert.to_dict()
    finally:
        session.close()


def get_all_alerts(user_id: int = 1, status: str = None) -> List[Dict]:
    session = SessionLocal()
    try:
        q = session.query(Alert).filter(Alert.user_id == user_id)
        if status:
            q = q.filter(Alert.status == status)
        alerts = q.order_by(Alert.created_at.desc()).all()
        return [a.to_dict() for a in alerts]
    finally:
        session.close()


def delete_alert(alert_id: int) -> bool:
    session = SessionLocal()
    try:
        alert = session.query(Alert).filter_by(id=alert_id).first()
        if alert:
            session.delete(alert)
            session.commit()
            return True
        return False
    finally:
        session.close()


def toggle_alert(alert_id: int) -> Optional[Dict]:
    session = SessionLocal()
    try:
        alert = session.query(Alert).filter_by(id=alert_id).first()
        if not alert:
            return None
        if alert.status == "active":
            alert.status = "disabled"
        elif alert.status in ("disabled", "triggered"):
            alert.status = "active"
            alert.triggered_at = None
            alert.triggered_value = None
        session.commit()
        session.refresh(alert)
        return alert.to_dict()
    finally:
        session.close()


def get_notifications(user_id: int = 1, unread_only: bool = False) -> List[Dict]:
    session = SessionLocal()
    try:
        q = session.query(Notification).filter(Notification.user_id == user_id)
        if unread_only:
            q = q.filter(Notification.is_read == False)
        notifs = q.order_by(Notification.created_at.desc()).limit(50).all()
        return [n.to_dict() for n in notifs]
    finally:
        session.close()


def mark_notification_read(notif_id: int) -> bool:
    session = SessionLocal()
    try:
        notif = session.query(Notification).filter_by(id=notif_id).first()
        if notif:
            notif.is_read = True
            session.commit()
            return True
        return False
    finally:
        session.close()


def get_unread_count(user_id: int = 1) -> int:
    session = SessionLocal()
    try:
        return session.query(Notification).filter(
            Notification.user_id == user_id,
            Notification.is_read == False,
        ).count()
    finally:
        session.close()
