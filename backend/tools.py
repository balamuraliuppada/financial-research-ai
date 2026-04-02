import yfinance as yf
from textblob import TextBlob
import requests
import pandas as pd
from langchain_core.tools import tool
from fundamentals import get_fundamentals, get_sector_comparison, get_stocks_by_sector, is_market_open

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
