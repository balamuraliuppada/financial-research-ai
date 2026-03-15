import streamlit as st
import yfinance as yf
import plotly.graph_objs as go
import redis
import pandas as pd
from database import create_table, save_search
from logger import log_api_call, log_api_error
from streamlit_autorefresh import st_autorefresh
from textblob import TextBlob
import requests

# Auto refresh every 5 minutes
st_autorefresh(interval=300000)

create_table()

# Redis setup
try:
    redis_client = redis.Redis(host="localhost", port=6379, db=0)
    redis_client.ping()
except:
    redis_client = None

st.set_page_config(page_title="Financial Research AI", layout="wide")

st.title("Financial Research AI - Stock Dashboard")

# -----------------------------
# Stock Options
# -----------------------------
stock_options = {
    "Reliance Industries": "RELIANCE.NS",
    "Tata Consultancy Services (TCS)": "TCS.NS",
    "Infosys": "INFY.NS",
    "HDFC Bank": "HDFCBANK.NS",
    "ICICI Bank": "ICICIBANK.NS"
}

selected_stock_name = st.selectbox(
    "Select an Indian Stock",
    list(stock_options.keys())
)

symbol = stock_options[selected_stock_name]

period = st.selectbox(
    "Select Time Range",
    ["1d", "5d", "1mo", "3mo", "6mo", "1y", "5y"]
)

# -----------------------------
# Get Stock Data (with caching)
# -----------------------------
@st.cache_data(ttl=300)
def get_stock_data(symbol, period):

    cache_key = f"{symbol}_{period}"

    if redis_client is not None:
        cached_data = redis_client.get(cache_key)

        if cached_data:
            cached_data = cached_data.decode("utf-8")
            return pd.read_json(cached_data)

    stock = yf.Ticker(symbol)

    log_api_call(symbol, period)

    if period == "1d":
        data = stock.history(period="1d", interval="5m")
    else:
        data = stock.history(period=period)

    if redis_client is not None:
        redis_client.set(cache_key, data.to_json(), ex=300)

    return data

# -----------------------------
# News Sentiment Function
# -----------------------------
def get_news_sentiment(company_name):

    url = f"https://newsapi.org/v2/everything?q={company_name}&pageSize=5&apiKey=7b74b92a008c43d7a0e8fc6f8712d2f2"

    try:
        response = requests.get(url)
        news_data = response.json()

        if news_data["status"] != "ok":
            return None, []

        articles = news_data["articles"]

        sentiments = []
        titles = []

        for article in articles:
            title = article["title"]
            titles.append(title)

            sentiment = TextBlob(title).sentiment.polarity
            sentiments.append(sentiment)

        avg_sentiment = sum(sentiments) / len(sentiments)

        return avg_sentiment, titles

    except:
        return None, []


# -----------------------------
# Main Logic
# -----------------------------
try:

    stock = yf.Ticker(symbol)

    data = get_stock_data(symbol, period)

    save_search(symbol, period)

    if data.empty:
        st.warning("⚠ No stock data available.")
        st.stop()

    info = stock.info

    company_name = info.get("longName", selected_stock_name)
    market_cap = info.get("marketCap", "N/A")
    volume = info.get("volume", "N/A")

    # -----------------------------
    # Technical Indicators
    # -----------------------------

    data["MA20"] = data["Close"].rolling(window=20).mean()

    delta = data["Close"].diff()

    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()

    rs = gain / loss
    data["RSI"] = 100 - (100 / (1 + rs))

    # -----------------------------
    # Metrics
    # -----------------------------

    current_price = round(data["Close"].iloc[-1], 2)
    previous_close = round(data["Close"].iloc[-2], 2)

    price_change = round(current_price - previous_close, 2)
    percent_change = round((price_change / previous_close) * 100, 2)

    period_high = round(data["High"].max(), 2)
    period_low = round(data["Low"].min(), 2)

    st.subheader(f"{company_name} ({symbol})")

    col1, col2, col3 = st.columns(3)

    col1.metric("Current Price (₹)", current_price,
                f"{price_change} ({percent_change}%)")

    col2.metric(f"{period} High", period_high)
    col3.metric(f"{period} Low", period_low)

    st.markdown("---")

    col4, col5 = st.columns(2)

    col4.write(f"**Market Cap:** {market_cap}")
    col5.write(f"**Volume:** {volume}")

    st.markdown("---")

    st.metric("RSI Indicator", round(data["RSI"].iloc[-1], 2))

    # -----------------------------
    # Main Chart
    # -----------------------------

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=data.index,
        y=data["Close"],
        mode="lines",
        name=f"{selected_stock_name} Price"
    ))

    fig.add_trace(go.Scatter(
        x=data.index,
        y=data["MA20"],
        mode="lines",
        name="20 Day Moving Average"
    ))

    fig.update_layout(
        title=f"{company_name} Price Timeline",
        xaxis_title="Date",
        yaxis_title="Price (INR)",
        template="plotly_dark"
    )

    st.plotly_chart(fig, use_container_width=True)

    # -----------------------------
    # News Sentiment
    # -----------------------------

    st.markdown("---")
    st.subheader("News Sentiment Analysis")

    sentiment, news_titles = get_news_sentiment(selected_stock_name)

    if sentiment is not None:

        if sentiment > 0.1:
            st.success("Overall Sentiment: Positive 📈")
        elif sentiment < -0.1:
            st.error("Overall Sentiment: Negative 📉")
        else:
            st.info("Overall Sentiment: Neutral")

        for title in news_titles:
            st.write("•", title)

    else:
        st.warning("News data not available.")

    # -----------------------------
    # Stock Comparison (Below News)
    # -----------------------------

    st.markdown("---")
    st.subheader("Stock Comparison")

    compare_stock = st.selectbox(
        "Select another stock to compare",
        list(stock_options.keys())
    )

    compare_symbol = stock_options[compare_stock]

    compare_data = get_stock_data(compare_symbol, period)

    st.write(f"Comparing **{selected_stock_name}** vs **{compare_stock}**")

    compare_fig = go.Figure()

    compare_fig.add_trace(go.Scatter(
        x=data.index,
        y=data["Close"],
        mode="lines",
        name=selected_stock_name
    ))

    compare_fig.add_trace(go.Scatter(
        x=compare_data.index,
        y=compare_data["Close"],
        mode="lines",
        name=compare_stock
    ))

    compare_fig.update_layout(
        title="Stock Price Comparison",
        xaxis_title="Date",
        yaxis_title="Price (INR)",
        template="plotly_dark"
    )

    st.plotly_chart(compare_fig, use_container_width=True)


except ConnectionError:
    st.error("🌐 Network error.")

except ValueError:
    st.error("⚠ Invalid data received.")

except Exception as e:
    log_api_error(e)
    st.error(f"⚠ Unexpected error occurred: {e}")