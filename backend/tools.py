import yfinance as yf
from textblob import TextBlob
import requests
import pandas as pd
from langchain_core.tools import tool
from backend.fundamentals import get_fundamentals, get_sector_comparison, get_stocks_by_sector, is_market_open

@tool
def get_stock_price(symbol: str, period: str = "1mo") -> str:
    """Fetch current stock price and recent history for a given ticker symbol. Use the symbol parameter like 'RELIANCE.NS'."""
    try:
        stock = yf.Ticker(symbol)
        data = stock.history(period=period)
        if data.empty:
            return f"No data found for {symbol}."
        current_price = round(data["Close"].iloc[-1], 2)
        return f"The current price of {symbol} is ₹{current_price}. Recent history:\n{data[['Close']].tail().to_string()}"
    except Exception as e:
        return f"Error fetching stock data: {e}"


@tool
def get_news_sentiment(company_name: str) -> str:
    """Fetch the latest news sentiment for a given company name. The sentiment ranges from -1 (Negative) to 1 (Positive)."""
    url = f"https://newsapi.org/v2/everything?q={company_name}&pageSize=5&apiKey=7b74b92a008c43d7a0e8fc6f8712d2f2"
    try:
        response = requests.get(url)
        news_data = response.json()
        if news_data.get("status") != "ok":
            return "Failed to fetch news."
        articles = news_data.get("articles", [])
        if not articles:
            return "No news found."

        sentiments, titles = [], []
        for article in articles:
            title = article.get("title", "")
            if title:
                titles.append(title)
                sentiments.append(TextBlob(title).sentiment.polarity)

        if not sentiments:
            return "Could not compute sentiment."

        avg_sentiment = sum(sentiments) / len(sentiments)
        label = "Positive" if avg_sentiment > 0.1 else ("Negative" if avg_sentiment < -0.1 else "Neutral")
        return f"Overall Sentiment: {label} ({avg_sentiment:.2f}). Recent headlines: {', '.join(titles)}"
    except Exception as e:
        return f"Error fetching news sentiment: {e}"


@tool
def get_rsi_and_ma(symbol: str) -> str:
    """Calculate the 14-day RSI and 20-day Moving Average for a stock."""
    try:
        stock = yf.Ticker(symbol)
        data = stock.history(period="3mo")
        if data.empty:
            return "No data available."

        data["MA20"] = data["Close"].rolling(window=20).mean()
        delta = data["Close"].diff()
        gain  = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss  = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs    = gain / loss
        data["RSI"] = 100 - (100 / (1 + rs))

        latest = data.iloc[-1]
        return f"RSI (14-day): {latest['RSI']:.2f}, 20-day MA: ₹{latest['MA20']:.2f}"
    except Exception as e:
        return f"Error computing indicators: {e}"


@tool
def get_fundamental_analysis(symbol: str) -> str:
    """
    Get fundamental analysis for an Indian stock — P/E ratio, P/B ratio, debt-to-equity,
    ROE, profit margins, EPS, revenue growth, and more. Symbol must be in Yahoo Finance
    format e.g. 'RELIANCE.NS', 'TCS.NS', 'INFY.NS'.
    """
    try:
        data = get_fundamentals(symbol)
        if "Error" in data:
            return f"Could not fetch fundamentals for {symbol}: {data['Error']}"
        lines = [f"**Fundamental Analysis for {symbol}**"]
        for key, val in data.items():
            lines.append(f"  • {key}: {val}")
        return "\n".join(lines)
    except Exception as e:
        return f"Error fetching fundamentals: {e}"


@tool
def get_sector_analysis(sector: str) -> str:
    """
    Compare all major Indian stocks in a given sector side-by-side.
    Available sectors: Information Technology, Banking & Finance, Energy & Conglomerates,
    Automobile, Pharmaceuticals, FMCG, Metals & Mining, Infrastructure, Telecom, Energy & Oil, Energy & Power.
    Returns a table with P/E, P/B, ROE, D/E, Net Margin, Revenue Growth, Market Cap.
    """
    try:
        df = get_sector_comparison(sector)
        if df.empty:
            stocks = get_stocks_by_sector(sector)
            if not stocks:
                return f"No stocks found for sector '{sector}'. Try one of: Information Technology, Banking & Finance, Automobile, Pharmaceuticals, FMCG, Metals & Mining."
            return f"Could not fetch comparison data for {sector}."
        return f"**Sector Comparison — {sector}**\n\n{df.to_string()}"
    except Exception as e:
        return f"Error in sector analysis: {e}"


@tool
def get_market_status() -> str:
    """
    Check whether the Indian stock market (NSE/BSE) is currently open or closed.
    Returns the current IST time, market open/close times, and market status.
    """
    status = is_market_open()
    state  = "🟢 OPEN" if status["is_open"] else "🔴 CLOSED"
    return (
        f"Market Status: {state}\n"
        f"Current Time : {status['current_ist']}\n"
        f"Day          : {status['day']}\n"
        f"NSE Hours    : {status['open_time']} – {status['close_time']}"
    )


# ─── NEW TOOLS ────────────────────────────────────────────────────────────────

@tool
def get_trading_signals(symbol: str) -> str:
    """
    Get comprehensive algorithmic trading signals for a stock.
    Analyses RSI, MACD, Stochastic, EMA, ADX, Bollinger, OBV, Supertrend, VWAP.
    Returns a composite BUY/SELL/HOLD signal with confidence percentage.
    Symbol should be in Yahoo Finance format e.g. 'RELIANCE.NS', 'TCS.NS'.
    """
    try:
        from backend.algo_signals import generate_signals
        result = generate_signals(symbol)
        if "error" in result:
            return f"Could not generate signals: {result['error']}"

        lines = [f"**Trading Signals for {symbol}**", f"Price: ₹{result['current_price']}"]
        lines.append(f"\n🎯 **Composite: {result['composite']['signal']} ({result['composite']['confidence']}% confidence)**")
        lines.append(f"Score: {result['composite']['score']}")
        lines.append(f"\nIndividual Signals:")
        for sig in result["signals"]:
            emoji = "🟢" if sig["signal"] == "BUY" else ("🔴" if sig["signal"] == "SELL" else "🟡")
            lines.append(f"  {emoji} {sig['name']}: {sig['signal']} — {sig['reason']}")
        return "\n".join(lines)
    except Exception as e:
        return f"Error generating signals: {e}"


@tool
def get_options_price(spot: float, strike: float, expiry_years: float,
                      volatility: float = 0.25, rate: float = 0.05,
                      option_type: str = "call") -> str:
    """
    Price a European option using the Black-Scholes model.
    Parameters:
      - spot: Current stock price (e.g. 2500.0)
      - strike: Strike price (e.g. 2600.0)
      - expiry_years: Time to expiry in years (e.g. 0.25 for 3 months)
      - volatility: Annual volatility as decimal (e.g. 0.25 for 25%)
      - rate: Risk-free rate (e.g. 0.065 for 6.5%)
      - option_type: 'call' or 'put'
    Returns option price and all Greeks (Delta, Gamma, Theta, Vega, Rho).
    """
    try:
        from backend.options_pricing import black_scholes
        result = black_scholes(spot, strike, expiry_years, rate, volatility, option_type)
        lines = [
            f"**{option_type.upper()} Option Pricing (Black-Scholes)**",
            f"  Spot: ₹{spot}, Strike: ₹{strike}, Expiry: {expiry_years:.2f}y",
            f"  Volatility: {volatility*100:.1f}%, Risk-free Rate: {rate*100:.1f}%",
            f"\n  💰 **Price: ₹{result['price']:.4f}**",
            f"\n  Greeks:",
            f"    Δ Delta: {result['delta']:.4f}",
            f"    Γ Gamma: {result['gamma']:.6f}",
            f"    Θ Theta: {result['theta']:.4f} (per day)",
            f"    ν Vega:  {result['vega']:.4f} (per 1% vol change)",
            f"    ρ Rho:   {result['rho']:.4f}",
        ]
        return "\n".join(lines)
    except Exception as e:
        return f"Error pricing option: {e}"


@tool
def get_portfolio_optimization(symbols_csv: str, strategy: str = "max_sharpe") -> str:
    """
    Run Modern Portfolio Theory optimization on a set of stocks.
    Parameters:
      - symbols_csv: Comma-separated stock symbols (e.g. 'RELIANCE.NS,TCS.NS,HDFCBANK.NS,INFY.NS')
      - strategy: One of 'max_sharpe', 'min_volatility', 'risk_parity', 'equal_weight'
    Returns optimal weights, expected return, volatility, and Sharpe ratio.
    """
    try:
        from backend.portfolio_optimizer import run_optimization
        symbols = [s.strip() for s in symbols_csv.split(",") if s.strip()]
        if len(symbols) < 2:
            return "Need at least 2 stocks for portfolio optimization."

        result = run_optimization(symbols, strategy=strategy, include_frontier=False)
        optimal = result["optimal"]
        lines = [
            f"**Portfolio Optimization ({strategy.replace('_', ' ').title()})**",
            f"\n📊 Optimal Weights:",
        ]
        for sym, w in optimal["weights"].items():
            lines.append(f"  • {sym}: {w*100:.1f}%")
        lines.extend([
            f"\n📈 Expected Annual Return: {optimal['expected_return']*100:.2f}%",
            f"📉 Annual Volatility: {optimal['volatility']*100:.2f}%",
            f"✨ Sharpe Ratio: {optimal['sharpe_ratio']:.4f}",
            f"⚠️ VaR (95%): {optimal['var_95']*100:.2f}%",
            f"⚠️ CVaR (95%): {optimal['cvar_95']*100:.2f}%",
            f"📉 Max Drawdown: {optimal['max_drawdown']*100:.2f}%",
        ])
        return "\n".join(lines)
    except Exception as e:
        return f"Error in optimization: {e}"


@tool
def get_commodity_price(commodity: str) -> str:
    """
    Get current price for a commodity.
    Available: gold, silver, crude_oil, natural_gas, copper, platinum.
    """
    try:
        from backend.multi_asset import get_all_commodities
        commodities = get_all_commodities()
        for c in commodities:
            if c["id"] == commodity.lower() or commodity.lower() in c["name"].lower():
                emoji = "🟢" if c["change"] >= 0 else "🔴"
                return (
                    f"**{c['name']}**: ${c['price']:.2f} {c['unit']}\n"
                    f"{emoji} Change: ${c['change']:.2f} ({c['change_pct']:+.2f}%)"
                )
        available = ", ".join([c["id"] for c in commodities])
        return f"Commodity not found. Available: {available}"
    except Exception as e:
        return f"Error fetching commodity: {e}"


@tool
def get_macro_data() -> str:
    """
    Get macroeconomic indicators and global market indices.
    Returns key indices like NIFTY 50, S&P 500, VIX, plus Treasury yields.
    """
    try:
        from backend.api_clients import MacroDataClient
        indices = MacroDataClient.get_market_indices()
        yields = MacroDataClient.get_treasury_yields()

        lines = ["**Global Market Indices:**"]
        for name, data in indices.items():
            emoji = "🟢" if data["change"] >= 0 else "🔴"
            lines.append(f"  {emoji} {name}: {data['price']:,.2f} ({data['change_pct']:+.2f}%)")

        if yields:
            lines.append("\n**US Treasury Yields:**")
            for mat, val in yields.items():
                if val is not None:
                    lines.append(f"  • {mat}: {val:.3f}%")

        return "\n".join(lines)
    except Exception as e:
        return f"Error fetching macro data: {e}"
