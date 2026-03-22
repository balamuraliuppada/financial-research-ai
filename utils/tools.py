import yfinance as yf
from textblob import TextBlob
import requests
import pandas as pd
from langchain_core.tools import tool

@tool
def get_stock_price(symbol: str, period: str = "1mo") -> str:
    """Fetch current stock price and recent history for a given ticker symbol. Use the symbol parameter like 'RELIANCE.NS'."""
    try:
        stock = yf.Ticker(symbol)
        data = stock.history(period=period)
        if data.empty:
            return f"No data found for {symbol}."
        current_price = round(data["Close"].iloc[-1], 2)
        return f"The current price of {symbol} is {current_price}. Recent history:\n{data[['Close']].tail().to_string()}"
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
        
        sentiments = []
        titles = []
        for article in articles:
            title = article.get("title", "")
            if title:
                titles.append(title)
                sentiments.append(TextBlob(title).sentiment.polarity)
        
        if not sentiments:
            return "Could not compute sentiment."
            
        avg_sentiment = sum(sentiments) / len(sentiments)
        sentiment_label = "Positive" if avg_sentiment > 0.1 else ("Negative" if avg_sentiment < -0.1 else "Neutral")
        
        return f"Overall Sentiment: {sentiment_label} ({avg_sentiment:.2f}). Recent headlines: {', '.join(titles)}"
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
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        data["RSI"] = 100 - (100 / (1 + rs))
        
        latest = data.iloc[-1]
        return f"RSI (14-day): {latest['RSI']:.2f}, 20-day MA: {latest['MA20']:.2f}"
    except Exception as e:
        return f"Error computing indicators: {e}"
