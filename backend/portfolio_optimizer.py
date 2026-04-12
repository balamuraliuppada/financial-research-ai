"""
portfolio_optimizer.py
──────────────────────
Modern Portfolio Theory implementation:
  - Efficient Frontier (Monte Carlo + analytical)
  - Mean-Variance Optimization (Markowitz)
  - Maximum Sharpe Ratio portfolio
  - Minimum Volatility portfolio
  - Risk Parity
  - Black-Litterman model
  - Risk metrics: VaR, CVaR, drawdown, beta, alpha
"""

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from typing import List, Dict, Optional, Tuple
import yfinance as yf
import logging

logger = logging.getLogger("finai.optimizer")

# ─── Data Fetching ────────────────────────────────────────────────────────────

def fetch_returns(symbols: List[str], period: str = "1y") -> pd.DataFrame:
    """Fetch daily returns for a list of symbols."""
    prices = pd.DataFrame()
    for sym in symbols:
        try:
            ticker = yf.Ticker(sym)
            data = ticker.history(period=period)
            if not data.empty:
                prices[sym] = data["Close"]
        except Exception as e:
            logger.warning(f"Could not fetch {sym}: {e}")

    if prices.empty:
        raise ValueError("No price data available for any symbol")

    # Forward fill missing dates, then compute returns
    prices = prices.fillna(method="ffill").dropna()
    returns = prices.pct_change().dropna()
    return returns


def annualize(daily_return: float, daily_vol: float, trading_days: int = 252) -> Tuple[float, float]:
    """Convert daily return/vol to annualized."""
    ann_return = daily_return * trading_days
    ann_vol = daily_vol * np.sqrt(trading_days)
    return ann_return, ann_vol


# ─── Portfolio Metrics ────────────────────────────────────────────────────────

def portfolio_performance(weights: np.ndarray, mean_returns: np.ndarray,
                          cov_matrix: np.ndarray, risk_free: float = 0.05,
                          trading_days: int = 252) -> Dict:
    """Compute annualized return, volatility, and Sharpe ratio."""
    weights = np.array(weights)
    port_return = np.dot(weights, mean_returns) * trading_days
    port_vol = np.sqrt(np.dot(weights.T, np.dot(cov_matrix * trading_days, weights)))
    sharpe = (port_return - risk_free) / port_vol if port_vol > 0 else 0
    return {
        "expected_return": round(float(port_return), 6),
        "volatility": round(float(port_vol), 6),
        "sharpe_ratio": round(float(sharpe), 4),
    }


def compute_var(returns: pd.DataFrame, weights: np.ndarray,
                confidence: float = 0.95, days: int = 1) -> float:
    """Parametric Value at Risk."""
    port_returns = returns.dot(weights)
    var = float(np.percentile(port_returns, (1 - confidence) * 100)) * np.sqrt(days)
    return round(var, 6)


def compute_cvar(returns: pd.DataFrame, weights: np.ndarray,
                 confidence: float = 0.95, days: int = 1) -> float:
    """Conditional Value at Risk (Expected Shortfall)."""
    port_returns = returns.dot(weights)
    var = np.percentile(port_returns, (1 - confidence) * 100)
    cvar = float(port_returns[port_returns <= var].mean()) * np.sqrt(days)
    return round(cvar, 6)


def max_drawdown(returns: pd.DataFrame, weights: np.ndarray) -> float:
    """Maximum drawdown of the portfolio."""
    port_returns = returns.dot(weights)
    cum = (1 + port_returns).cumprod()
    peak = cum.cummax()
    dd = (cum - peak) / peak
    return round(float(dd.min()), 6)


# ─── Optimization Strategies ─────────────────────────────────────────────────

def _neg_sharpe(weights, mean_returns, cov_matrix, risk_free, trading_days):
    """Negative Sharpe ratio for minimization."""
    perf = portfolio_performance(weights, mean_returns, cov_matrix, risk_free, trading_days)
    return -perf["sharpe_ratio"]


def _portfolio_vol(weights, cov_matrix, trading_days):
    """Portfolio volatility."""
    return np.sqrt(np.dot(weights.T, np.dot(cov_matrix * trading_days, weights)))


def optimize_max_sharpe(mean_returns: np.ndarray, cov_matrix: np.ndarray,
                        risk_free: float = 0.05, trading_days: int = 252,
                        bounds: tuple = None) -> Dict:
    """Find the tangency portfolio (maximum Sharpe ratio)."""
    n = len(mean_returns)
    init = np.array([1.0 / n] * n)
    constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1}]
    if bounds is None:
        bounds = tuple((0, 1) for _ in range(n))

    result = minimize(
        _neg_sharpe, init,
        args=(mean_returns, cov_matrix, risk_free, trading_days),
        method="SLSQP", bounds=bounds, constraints=constraints,
        options={"maxiter": 1000, "ftol": 1e-12},
    )

    weights = result.x
    perf = portfolio_performance(weights, mean_returns, cov_matrix, risk_free, trading_days)
    return {"weights": weights.tolist(), **perf, "strategy": "max_sharpe"}


def optimize_min_volatility(mean_returns: np.ndarray, cov_matrix: np.ndarray,
                            risk_free: float = 0.05, trading_days: int = 252,
                            bounds: tuple = None) -> Dict:
    """Find the global minimum variance portfolio."""
    n = len(mean_returns)
    init = np.array([1.0 / n] * n)
    constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1}]
    if bounds is None:
        bounds = tuple((0, 1) for _ in range(n))

    result = minimize(
        _portfolio_vol, init,
        args=(cov_matrix, trading_days),
        method="SLSQP", bounds=bounds, constraints=constraints,
        options={"maxiter": 1000, "ftol": 1e-12},
    )

    weights = result.x
    perf = portfolio_performance(weights, mean_returns, cov_matrix, risk_free, trading_days)
    return {"weights": weights.tolist(), **perf, "strategy": "min_volatility"}


def optimize_risk_parity(cov_matrix: np.ndarray, mean_returns: np.ndarray,
                         risk_free: float = 0.05, trading_days: int = 252) -> Dict:
    """
    Risk Parity: allocate so each asset contributes equally to total portfolio risk.
    """
    n = cov_matrix.shape[0]
    cov_ann = cov_matrix * trading_days

    def risk_budget_objective(weights):
        port_vol = np.sqrt(weights.T @ cov_ann @ weights)
        marginal_contrib = cov_ann @ weights
        risk_contrib = weights * marginal_contrib / port_vol
        target = port_vol / n
        return np.sum((risk_contrib - target) ** 2)

    init = np.array([1.0 / n] * n)
    constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1}]
    bounds = tuple((0.01, 1) for _ in range(n))

    result = minimize(
        risk_budget_objective, init,
        method="SLSQP", bounds=bounds, constraints=constraints,
    )

    weights = result.x
    perf = portfolio_performance(weights, mean_returns, cov_matrix, risk_free, trading_days)
    return {"weights": weights.tolist(), **perf, "strategy": "risk_parity"}


def optimize_black_litterman(mean_returns: np.ndarray, cov_matrix: np.ndarray,
                             market_caps: np.ndarray = None,
                             views: Dict = None,
                             risk_free: float = 0.05,
                             trading_days: int = 252, tau: float = 0.05) -> Dict:
    """
    Black-Litterman model: combine market equilibrium with investor views.
    If no views provided, returns market-cap weighted equilibrium portfolio.
    """
    n = len(mean_returns)
    cov_ann = cov_matrix * trading_days

    # Market equilibrium weights
    if market_caps is not None:
        mkt_weights = market_caps / market_caps.sum()
    else:
        mkt_weights = np.array([1.0 / n] * n)

    # Risk aversion coefficient
    port_return = np.dot(mkt_weights, mean_returns) * trading_days
    port_var = mkt_weights.T @ cov_ann @ mkt_weights
    delta = (port_return - risk_free) / port_var if port_var > 0 else 2.5

    # Implied equilibrium returns
    pi = delta * cov_ann @ mkt_weights

    if views and len(views) > 0:
        # Construct P (pick matrix) and Q (view returns)
        view_symbols = list(views.keys())
        k = len(view_symbols)
        P = np.zeros((k, n))
        Q = np.zeros(k)
        for i, (sym_idx, view_return) in enumerate(views.items()):
            idx = int(sym_idx) if isinstance(sym_idx, (int, str)) else 0
            if idx < n:
                P[i, idx] = 1
                Q[i] = view_return

        # Omega — uncertainty of views (proportional to variance)
        omega = np.diag(np.diag(P @ (tau * cov_ann) @ P.T))

        # Black-Litterman posterior
        M = np.linalg.inv(np.linalg.inv(tau * cov_ann) + P.T @ np.linalg.inv(omega) @ P)
        bl_returns = M @ (np.linalg.inv(tau * cov_ann) @ pi + P.T @ np.linalg.inv(omega) @ Q)
    else:
        bl_returns = pi

    # Optimize with BL returns
    init = np.array([1.0 / n] * n)
    constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1}]
    bounds = tuple((0, 1) for _ in range(n))

    def neg_utility(weights):
        ret = weights.T @ bl_returns
        risk = weights.T @ cov_ann @ weights
        return -(ret - 0.5 * delta * risk)

    result = minimize(neg_utility, init, method="SLSQP", bounds=bounds, constraints=constraints)
    weights = result.x

    perf = portfolio_performance(weights, mean_returns, cov_matrix, risk_free, trading_days)
    return {"weights": weights.tolist(), **perf, "strategy": "black_litterman"}


# ─── Efficient Frontier ──────────────────────────────────────────────────────

def compute_efficient_frontier(mean_returns: np.ndarray, cov_matrix: np.ndarray,
                               risk_free: float = 0.05, trading_days: int = 252,
                               n_points: int = 50) -> List[Dict]:
    """
    Compute the efficient frontier via target-return optimization.
    Returns a list of {return, volatility, sharpe, weights} points.
    """
    n = len(mean_returns)
    min_ret = float(mean_returns.min()) * trading_days
    max_ret = float(mean_returns.max()) * trading_days
    target_returns = np.linspace(min_ret * 0.8, max_ret * 1.2, n_points)

    frontier = []
    for target in target_returns:
        constraints = [
            {"type": "eq", "fun": lambda w: np.sum(w) - 1},
            {"type": "eq", "fun": lambda w, t=target: np.dot(w, mean_returns) * trading_days - t},
        ]
        bounds = tuple((0, 1) for _ in range(n))
        init = np.array([1.0 / n] * n)

        result = minimize(
            _portfolio_vol, init,
            args=(cov_matrix, trading_days),
            method="SLSQP", bounds=bounds, constraints=constraints,
        )

        if result.success:
            vol = float(result.fun)
            sharpe = (target - risk_free) / vol if vol > 0 else 0
            frontier.append({
                "expected_return": round(target, 6),
                "volatility": round(vol, 6),
                "sharpe_ratio": round(sharpe, 4),
                "weights": result.x.tolist(),
            })

    return frontier


def monte_carlo_simulation(mean_returns: np.ndarray, cov_matrix: np.ndarray,
                           risk_free: float = 0.05, trading_days: int = 252,
                           n_portfolios: int = 5000) -> List[Dict]:
    """Random portfolio simulation for visualization."""
    n = len(mean_returns)
    results = []

    for _ in range(n_portfolios):
        weights = np.random.dirichlet(np.ones(n))
        perf = portfolio_performance(weights, mean_returns, cov_matrix, risk_free, trading_days)
        results.append({**perf, "weights": weights.tolist()})

    return results


# ─── Main Optimization Entry Point ───────────────────────────────────────────

def run_optimization(symbols: List[str], strategy: str = "max_sharpe",
                     period: str = "1y", risk_free: float = 0.05,
                     views: Dict = None, include_frontier: bool = True) -> Dict:
    """
    Full optimization pipeline.
    Returns optimal weights, metrics, efficient frontier, and simulation data.
    """
    # 1. Fetch returns
    returns = fetch_returns(symbols, period)
    valid_symbols = list(returns.columns)

    if len(valid_symbols) < 2:
        raise ValueError("Need at least 2 assets with valid price data for optimization")

    mean_returns = returns.mean().values
    cov_matrix = returns.cov().values

    # 2. Run selected strategy
    strategies = {
        "max_sharpe": lambda: optimize_max_sharpe(mean_returns, cov_matrix, risk_free),
        "min_volatility": lambda: optimize_min_volatility(mean_returns, cov_matrix, risk_free),
        "risk_parity": lambda: optimize_risk_parity(cov_matrix, mean_returns, risk_free),
        "black_litterman": lambda: optimize_black_litterman(
            mean_returns, cov_matrix, views=views, risk_free=risk_free
        ),
        "equal_weight": lambda: {
            "weights": [1.0 / len(valid_symbols)] * len(valid_symbols),
            **portfolio_performance(
                np.array([1.0 / len(valid_symbols)] * len(valid_symbols)),
                mean_returns, cov_matrix, risk_free
            ),
            "strategy": "equal_weight",
        },
    }

    if strategy not in strategies:
        strategy = "max_sharpe"

    optimal = strategies[strategy]()
    weights = np.array(optimal["weights"])

    # 3. Risk metrics
    var_95 = compute_var(returns, weights, 0.95)
    cvar_95 = compute_cvar(returns, weights, 0.95)
    mdd = max_drawdown(returns, weights)

    # 4. Correlation matrix
    corr_matrix = returns.corr()

    # 5. Efficient frontier + Monte Carlo
    frontier = []
    simulation = []
    if include_frontier:
        try:
            frontier = compute_efficient_frontier(mean_returns, cov_matrix, risk_free)
        except Exception as e:
            logger.warning(f"Frontier computation failed: {e}")
        try:
            simulation = monte_carlo_simulation(mean_returns, cov_matrix, risk_free, n_portfolios=3000)
        except Exception as e:
            logger.warning(f"Monte Carlo failed: {e}")

    # 6. Assemble result
    weight_map = {sym: round(w, 6) for sym, w in zip(valid_symbols, weights)}

    return {
        "symbols": valid_symbols,
        "strategy": strategy,
        "optimal": {
            **optimal,
            "weights": weight_map,
            "var_95": var_95,
            "cvar_95": cvar_95,
            "max_drawdown": mdd,
        },
        "correlation": {
            "symbols": valid_symbols,
            "matrix": corr_matrix.round(4).values.tolist(),
        },
        "frontier": frontier,
        "simulation": simulation,
        "period": period,
        "risk_free_rate": risk_free,
    }
