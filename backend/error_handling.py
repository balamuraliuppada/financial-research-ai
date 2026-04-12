"""
error_handling.py
─────────────────
Sophisticated error-handling infrastructure:
  - Custom exception hierarchy for financial APIs
  - Circuit breaker pattern (per-API)
  - Exponential backoff retry with jitter
  - Token-bucket rate limiter
"""

import time
import random
import asyncio
import logging
import functools
from enum import Enum
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

logger = logging.getLogger("finai.errors")


# ─── Custom Exceptions ───────────────────────────────────────────────────────

class FinAIError(Exception):
    """Base exception for Financial AI platform."""
    def __init__(self, message: str, code: str = "UNKNOWN", details: dict = None):
        super().__init__(message)
        self.code = code
        self.details = details or {}
        self.timestamp = datetime.utcnow().isoformat()

    def to_dict(self) -> dict:
        return {
            "error": True,
            "code": self.code,
            "message": str(self),
            "details": self.details,
            "timestamp": self.timestamp,
        }


class APIRateLimitError(FinAIError):
    """Raised when an API rate limit is hit."""
    def __init__(self, api_name: str, retry_after: float = 60):
        super().__init__(
            f"{api_name} rate limit exceeded. Retry after {retry_after}s",
            code="RATE_LIMIT",
            details={"api": api_name, "retry_after": retry_after},
        )
        self.retry_after = retry_after


class APITimeoutError(FinAIError):
    """Raised when an API request times out."""
    def __init__(self, api_name: str, timeout: float):
        super().__init__(
            f"{api_name} request timed out after {timeout}s",
            code="TIMEOUT",
            details={"api": api_name, "timeout": timeout},
        )


class APIBadResponseError(FinAIError):
    """Raised when an API returns an unexpected response."""
    def __init__(self, api_name: str, status_code: int = 0, body: str = ""):
        super().__init__(
            f"{api_name} returned unexpected response (HTTP {status_code})",
            code="BAD_RESPONSE",
            details={"api": api_name, "status_code": status_code, "body": body[:500]},
        )


class CircuitOpenError(FinAIError):
    """Raised when a circuit breaker is open (API is considered down)."""
    def __init__(self, api_name: str, reset_at: str):
        super().__init__(
            f"{api_name} circuit breaker is OPEN — service unavailable until {reset_at}",
            code="CIRCUIT_OPEN",
            details={"api": api_name, "reset_at": reset_at},
        )


class DataNotAvailableError(FinAIError):
    """Raised when requested data doesn't exist."""
    def __init__(self, symbol: str, data_type: str = "price"):
        super().__init__(
            f"No {data_type} data available for {symbol}",
            code="NO_DATA",
            details={"symbol": symbol, "data_type": data_type},
        )


# ─── Circuit Breaker ─────────────────────────────────────────────────────────

class CircuitState(Enum):
    CLOSED = "CLOSED"       # Normal operation
    OPEN = "OPEN"           # Failing — block requests
    HALF_OPEN = "HALF_OPEN" # Testing recovery


class CircuitBreaker:
    """
    Per-API circuit breaker.
    - After `failure_threshold` consecutive failures → OPEN (block calls for `recovery_timeout` seconds).
    - After cooldown → HALF_OPEN (allow one probe call).
    - If probe succeeds → CLOSED; if fails → OPEN again.
    """

    def __init__(self, name: str, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.success_count = 0
        self.total_calls = 0

    def can_execute(self) -> bool:
        if self.state == CircuitState.CLOSED:
            return True
        if self.state == CircuitState.OPEN:
            if self.last_failure_time and (time.time() - self.last_failure_time) > self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                logger.info(f"[CircuitBreaker:{self.name}] OPEN → HALF_OPEN (probing)")
                return True
            return False
        # HALF_OPEN — allow one request
        return True

    def record_success(self):
        self.total_calls += 1
        self.success_count += 1
        self.failure_count = 0
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.CLOSED
            logger.info(f"[CircuitBreaker:{self.name}] HALF_OPEN → CLOSED (recovered)")

    def record_failure(self):
        self.total_calls += 1
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning(f"[CircuitBreaker:{self.name}] → OPEN after {self.failure_count} failures")

    def get_status(self) -> dict:
        reset_at = None
        if self.state == CircuitState.OPEN and self.last_failure_time:
            reset_at = datetime.fromtimestamp(
                self.last_failure_time + self.recovery_timeout
            ).isoformat()
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "total_calls": self.total_calls,
            "reset_at": reset_at,
        }


# ─── Rate Limiter (Token Bucket) ─────────────────────────────────────────────

class RateLimiter:
    """
    Token-bucket rate limiter.
    - `max_tokens` requests allowed in any `refill_period` seconds window.
    - Tokens refill gradually.
    """

    def __init__(self, max_tokens: int, refill_period: float = 60.0):
        self.max_tokens = max_tokens
        self.refill_period = refill_period
        self.tokens = float(max_tokens)
        self.last_refill = time.time()

    def _refill(self):
        now = time.time()
        elapsed = now - self.last_refill
        new_tokens = elapsed * (self.max_tokens / self.refill_period)
        self.tokens = min(self.max_tokens, self.tokens + new_tokens)
        self.last_refill = now

    def acquire(self) -> bool:
        self._refill()
        if self.tokens >= 1:
            self.tokens -= 1
            return True
        return False

    @property
    def remaining(self) -> int:
        self._refill()
        return int(self.tokens)


# ─── Retry with Exponential Backoff ──────────────────────────────────────────

def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    exceptions: tuple = (Exception,),
    circuit_breaker: CircuitBreaker = None,
):
    """
    Decorator: retries the wrapped function with exponential backoff + jitter.
    Integrates with CircuitBreaker if provided.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries + 1):
                # Check circuit breaker
                if circuit_breaker and not circuit_breaker.can_execute():
                    status = circuit_breaker.get_status()
                    raise CircuitOpenError(circuit_breaker.name, status.get("reset_at", "unknown"))

                try:
                    result = func(*args, **kwargs)
                    if circuit_breaker:
                        circuit_breaker.record_success()
                    return result
                except exceptions as e:
                    last_exception = e
                    if circuit_breaker:
                        circuit_breaker.record_failure()

                    if attempt < max_retries:
                        delay = min(base_delay * (2 ** attempt), max_delay)
                        jitter = random.uniform(0, delay * 0.5)
                        sleep_time = delay + jitter
                        logger.warning(
                            f"[Retry] {func.__name__} attempt {attempt+1}/{max_retries} "
                            f"failed: {e}. Retrying in {sleep_time:.1f}s"
                        )
                        time.sleep(sleep_time)
                    else:
                        logger.error(f"[Retry] {func.__name__} exhausted {max_retries} retries: {e}")

            raise last_exception

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries + 1):
                if circuit_breaker and not circuit_breaker.can_execute():
                    status = circuit_breaker.get_status()
                    raise CircuitOpenError(circuit_breaker.name, status.get("reset_at", "unknown"))

                try:
                    result = await func(*args, **kwargs)
                    if circuit_breaker:
                        circuit_breaker.record_success()
                    return result
                except exceptions as e:
                    last_exception = e
                    if circuit_breaker:
                        circuit_breaker.record_failure()
                    if attempt < max_retries:
                        delay = min(base_delay * (2 ** attempt), max_delay)
                        jitter = random.uniform(0, delay * 0.5)
                        await asyncio.sleep(delay + jitter)

            raise last_exception

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return wrapper
    return decorator


# ─── API Health Aggregator ────────────────────────────────────────────────────

class APIHealthMonitor:
    """Tracks health status of all integrated APIs."""

    def __init__(self):
        self._breakers: Dict[str, CircuitBreaker] = {}
        self._limiters: Dict[str, RateLimiter] = {}
        self._last_latency: Dict[str, float] = {}

    def register(self, name: str, breaker: CircuitBreaker, limiter: RateLimiter):
        self._breakers[name] = breaker
        self._limiters[name] = limiter

    def record_latency(self, name: str, latency_ms: float):
        self._last_latency[name] = latency_ms

    def get_health(self) -> dict:
        apis = {}
        for name in self._breakers:
            breaker = self._breakers[name]
            limiter = self._limiters.get(name)
            status = breaker.get_status()
            apis[name] = {
                **status,
                "remaining_quota": limiter.remaining if limiter else None,
                "last_latency_ms": self._last_latency.get(name),
            }

        all_ok = all(b.state == CircuitState.CLOSED for b in self._breakers.values())
        return {
            "overall": "healthy" if all_ok else "degraded",
            "apis": apis,
            "checked_at": datetime.utcnow().isoformat(),
        }


# Singleton health monitor
health_monitor = APIHealthMonitor()
