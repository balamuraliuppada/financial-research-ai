"""
options_pricing.py
──────────────────
Options pricing models:
  - Black-Scholes (European options)
  - Binomial Tree (American options with early exercise)
  - Greeks: Delta, Gamma, Theta, Vega, Rho
  - Implied Volatility via Newton-Raphson
  - Options strategy payoff computation
"""

import math
import numpy as np
from scipy.stats import norm
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger("finai.options")


# ─── Black-Scholes Model ─────────────────────────────────────────────────────

def black_scholes(S: float, K: float, T: float, r: float, sigma: float,
                  option_type: str = "call") -> Dict:
    """
    Black-Scholes option pricing for European options.

    Args:
        S: Current stock price
        K: Strike price
        T: Time to expiration (in years)
        r: Risk-free rate (annual, e.g., 0.05 for 5%)
        sigma: Volatility (annual, e.g., 0.25 for 25%)
        option_type: 'call' or 'put'

    Returns:
        Price and all Greeks
    """
    if T <= 0:
        # At expiration
        if option_type == "call":
            price = max(S - K, 0)
        else:
            price = max(K - S, 0)
        return {
            "price": round(price, 4),
            "delta": 1.0 if S > K and option_type == "call" else (-1.0 if S < K and option_type == "put" else 0),
            "gamma": 0, "theta": 0, "vega": 0, "rho": 0,
        }

    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)

    if option_type == "call":
        price = S * norm.cdf(d1) - K * math.exp(-r * T) * norm.cdf(d2)
        delta = norm.cdf(d1)
        rho = K * T * math.exp(-r * T) * norm.cdf(d2) / 100
    else:
        price = K * math.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)
        delta = norm.cdf(d1) - 1
        rho = -K * T * math.exp(-r * T) * norm.cdf(-d2) / 100

    # Greeks
    gamma = norm.pdf(d1) / (S * sigma * math.sqrt(T))
    vega = S * norm.pdf(d1) * math.sqrt(T) / 100
    theta_common = -(S * norm.pdf(d1) * sigma) / (2 * math.sqrt(T))

    if option_type == "call":
        theta = (theta_common - r * K * math.exp(-r * T) * norm.cdf(d2)) / 365
    else:
        theta = (theta_common + r * K * math.exp(-r * T) * norm.cdf(-d2)) / 365

    return {
        "price": round(price, 4),
        "delta": round(delta, 4),
        "gamma": round(gamma, 6),
        "theta": round(theta, 4),
        "vega": round(vega, 4),
        "rho": round(rho, 4),
        "d1": round(d1, 4),
        "d2": round(d2, 4),
        "model": "black_scholes",
    }


# ─── Binomial Tree (American Options) ────────────────────────────────────────

def binomial_tree(S: float, K: float, T: float, r: float, sigma: float,
                  option_type: str = "call", steps: int = 100,
                  american: bool = True) -> Dict:
    """
    Binomial tree option pricing.
    Supports American options (with early exercise) and European.

    Args:
        S: Spot price
        K: Strike price
        T: Time to expiry (years)
        r: Risk-free rate
        sigma: Volatility
        option_type: 'call' or 'put'
        steps: Number of tree steps
        american: If True, allow early exercise
    """
    dt = T / steps
    u = math.exp(sigma * math.sqrt(dt))
    d = 1 / u
    p = (math.exp(r * dt) - d) / (u - d)

    # Initialize asset prices at maturity
    prices = np.zeros(steps + 1)
    for i in range(steps + 1):
        prices[i] = S * (u ** (steps - i)) * (d ** i)

    # Option values at maturity
    if option_type == "call":
        values = np.maximum(prices - K, 0)
    else:
        values = np.maximum(K - prices, 0)

    # Backward induction
    for j in range(steps - 1, -1, -1):
        for i in range(j + 1):
            values[i] = math.exp(-r * dt) * (p * values[i] + (1 - p) * values[i + 1])
            if american:
                asset_price = S * (u ** (j - i)) * (d ** i)
                if option_type == "call":
                    exercise = max(asset_price - K, 0)
                else:
                    exercise = max(K - asset_price, 0)
                values[i] = max(values[i], exercise)

    price = values[0]

    # Approximate Greeks via finite differences
    delta = _fd_delta(S, K, T, r, sigma, option_type, steps, american)
    gamma = _fd_gamma(S, K, T, r, sigma, option_type, steps, american)
    theta = _fd_theta(S, K, T, r, sigma, option_type, steps, american)
    vega = _fd_vega(S, K, T, r, sigma, option_type, steps, american)

    return {
        "price": round(price, 4),
        "delta": round(delta, 4),
        "gamma": round(gamma, 6),
        "theta": round(theta, 4),
        "vega": round(vega, 4),
        "rho": 0,  # Not computed for binomial
        "model": "binomial_american" if american else "binomial_european",
        "steps": steps,
    }


def _binomial_price(S, K, T, r, sigma, option_type, steps, american):
    """Helper to compute just the price via binomial tree."""
    if T <= 0:
        return max(S - K, 0) if option_type == "call" else max(K - S, 0)
    dt = T / steps
    u = math.exp(sigma * math.sqrt(dt))
    d = 1 / u
    p = (math.exp(r * dt) - d) / (u - d)
    prices = np.array([S * (u ** (steps - i)) * (d ** i) for i in range(steps + 1)])
    values = np.maximum(prices - K, 0) if option_type == "call" else np.maximum(K - prices, 0)
    for j in range(steps - 1, -1, -1):
        for i in range(j + 1):
            values[i] = math.exp(-r * dt) * (p * values[i] + (1 - p) * values[i + 1])
            if american:
                ap = S * (u ** (j - i)) * (d ** i)
                ex = max(ap - K, 0) if option_type == "call" else max(K - ap, 0)
                values[i] = max(values[i], ex)
    return values[0]


def _fd_delta(S, K, T, r, sigma, ot, steps, am):
    ds = S * 0.01
    up = _binomial_price(S + ds, K, T, r, sigma, ot, steps, am)
    dn = _binomial_price(S - ds, K, T, r, sigma, ot, steps, am)
    return (up - dn) / (2 * ds)


def _fd_gamma(S, K, T, r, sigma, ot, steps, am):
    ds = S * 0.01
    up = _binomial_price(S + ds, K, T, r, sigma, ot, steps, am)
    md = _binomial_price(S, K, T, r, sigma, ot, steps, am)
    dn = _binomial_price(S - ds, K, T, r, sigma, ot, steps, am)
    return (up - 2 * md + dn) / (ds ** 2)


def _fd_theta(S, K, T, r, sigma, ot, steps, am):
    dt = 1 / 365
    if T - dt <= 0:
        return 0
    now = _binomial_price(S, K, T, r, sigma, ot, steps, am)
    later = _binomial_price(S, K, T - dt, r, sigma, ot, steps, am)
    return (later - now)


def _fd_vega(S, K, T, r, sigma, ot, steps, am):
    dsig = 0.01
    up = _binomial_price(S, K, T, r, sigma + dsig, ot, steps, am)
    dn = _binomial_price(S, K, T, r, sigma - dsig, ot, steps, am)
    return (up - dn) / (2 * dsig) / 100


# ─── Implied Volatility ──────────────────────────────────────────────────────

def implied_volatility(market_price: float, S: float, K: float, T: float,
                       r: float, option_type: str = "call",
                       max_iterations: int = 100, tolerance: float = 1e-6) -> float:
    """
    Newton-Raphson method to find implied volatility.
    """
    sigma = 0.3  # Initial guess

    for _ in range(max_iterations):
        result = black_scholes(S, K, T, r, sigma, option_type)
        price = result["price"]
        vega = result["vega"] * 100  # Undo /100 from BS

        diff = price - market_price
        if abs(diff) < tolerance:
            return round(sigma, 6)

        if abs(vega) < 1e-12:
            break

        sigma -= diff / vega
        sigma = max(0.001, min(sigma, 5.0))  # Clamp

    return round(sigma, 6)


# ─── Options Strategy Payoff ─────────────────────────────────────────────────

def compute_strategy_payoff(legs: List[Dict], spot_range: Tuple[float, float] = None,
                            n_points: int = 100) -> Dict:
    """
    Compute P&L payoff diagram for multi-leg options strategies.

    Each leg: {
        'type': 'call' or 'put',
        'strike': float,
        'premium': float,
        'quantity': int (positive=long, negative=short),
        'expiry_years': float (optional, for IV scenarios)
    }
    """
    if not legs:
        return {"error": "No legs provided"}

    strikes = [leg["strike"] for leg in legs]
    if spot_range is None:
        min_s = min(strikes) * 0.7
        max_s = max(strikes) * 1.3
    else:
        min_s, max_s = spot_range

    spot_prices = np.linspace(min_s, max_s, n_points)
    payoffs = np.zeros(n_points)
    total_premium = 0

    for leg in legs:
        strike = leg["strike"]
        premium = leg.get("premium", 0)
        qty = leg.get("quantity", 1)
        opt_type = leg.get("type", "call")

        total_premium += premium * qty  # negative qty = income

        for i, s in enumerate(spot_prices):
            if opt_type == "call":
                intrinsic = max(s - strike, 0)
            else:
                intrinsic = max(strike - s, 0)

            payoffs[i] += (intrinsic - premium) * qty

    # Breakeven points
    breakevens = []
    for i in range(len(payoffs) - 1):
        if payoffs[i] * payoffs[i + 1] < 0:
            # Linear interpolation
            x = spot_prices[i] - payoffs[i] * (spot_prices[i + 1] - spot_prices[i]) / (payoffs[i + 1] - payoffs[i])
            breakevens.append(round(x, 2))

    return {
        "spot_prices": spot_prices.round(2).tolist(),
        "payoffs": payoffs.round(2).tolist(),
        "max_profit": round(float(payoffs.max()), 2),
        "max_loss": round(float(payoffs.min()), 2),
        "breakevens": breakevens,
        "total_premium": round(total_premium, 2),
        "legs": legs,
    }


# ─── Predefined Strategies ───────────────────────────────────────────────────

STRATEGY_TEMPLATES = {
    "long_call": lambda S, K, p: [{"type": "call", "strike": K, "premium": p, "quantity": 1}],
    "long_put": lambda S, K, p: [{"type": "put", "strike": K, "premium": p, "quantity": 1}],
    "covered_call": lambda S, K, p: [
        {"type": "call", "strike": K, "premium": p, "quantity": -1},
    ],
    "straddle": lambda S, K, p: [
        {"type": "call", "strike": K, "premium": p, "quantity": 1},
        {"type": "put", "strike": K, "premium": p * 0.9, "quantity": 1},
    ],
    "strangle": lambda S, K, p: [
        {"type": "call", "strike": K * 1.05, "premium": p * 0.7, "quantity": 1},
        {"type": "put", "strike": K * 0.95, "premium": p * 0.6, "quantity": 1},
    ],
    "bull_call_spread": lambda S, K, p: [
        {"type": "call", "strike": K, "premium": p, "quantity": 1},
        {"type": "call", "strike": K * 1.05, "premium": p * 0.5, "quantity": -1},
    ],
    "bear_put_spread": lambda S, K, p: [
        {"type": "put", "strike": K, "premium": p, "quantity": 1},
        {"type": "put", "strike": K * 0.95, "premium": p * 0.5, "quantity": -1},
    ],
    "iron_condor": lambda S, K, p: [
        {"type": "put", "strike": K * 0.92, "premium": p * 0.3, "quantity": 1},
        {"type": "put", "strike": K * 0.96, "premium": p * 0.5, "quantity": -1},
        {"type": "call", "strike": K * 1.04, "premium": p * 0.5, "quantity": -1},
        {"type": "call", "strike": K * 1.08, "premium": p * 0.3, "quantity": 1},
    ],
    "butterfly": lambda S, K, p: [
        {"type": "call", "strike": K * 0.95, "premium": p * 1.2, "quantity": 1},
        {"type": "call", "strike": K, "premium": p, "quantity": -2},
        {"type": "call", "strike": K * 1.05, "premium": p * 0.5, "quantity": 1},
    ],
}


def get_strategy_payoff(strategy_name: str, spot: float, strike: float,
                        premium: float) -> Dict:
    """Compute payoff for a predefined strategy."""
    template = STRATEGY_TEMPLATES.get(strategy_name)
    if not template:
        return {"error": f"Unknown strategy: {strategy_name}"}

    legs = template(spot, strike, premium)
    return compute_strategy_payoff(legs)
