import streamlit as st
import yfinance as yf
import plotly.graph_objs as go
import redis
import pandas as pd
from database import create_table, save_search, add_to_portfolio, remove_from_portfolio, get_portfolio
from logger import log_api_call, log_api_error
from streamlit_autorefresh import st_autorefresh
from textblob import TextBlob
import requests
from utils.agent import run_financial_agent

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

st.title("Financial Research AI")

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
# Tabs
# -----------------------------
tab1, tab2, tab3 = st.tabs(["Dashboard", "Portfolio", "AI Assistant"])

with tab1:
    st.header("Stock Dashboard")
    
    col_sel1, col_sel2 = st.columns(2)
    with col_sel1:
        selected_stock_name = st.selectbox(
            "Select an Indian Stock",
            list(stock_options.keys())
        )
        symbol = stock_options[selected_stock_name]
    
    with col_sel2:
        period = st.selectbox(
            "Select Time Range",
            ["1d", "5d", "1mo", "3mo", "6mo", "1y", "5y"]
        )

    try:
        stock = yf.Ticker(symbol)
        data = get_stock_data(symbol, period)
        save_search(symbol, period)

        if data.empty:
            st.warning("⚠ No stock data available.")
        else:
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
            
            # Allow adding directly to portfolio from dashboard
            if st.button("Add to Portfolio"):
                add_to_portfolio(symbol)
                st.success(f"{symbol} added to portfolio!")

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
                x=data.index, y=data["Close"], mode="lines", name=f"{selected_stock_name} Price"
            ))
            fig.add_trace(go.Scatter(
                x=data.index, y=data["MA20"], mode="lines", name="20 Day Moving Average"
            ))
            fig.update_layout(
                title=f"{company_name} Price Timeline",
                xaxis_title="Date", yaxis_title="Price (INR)", template="plotly_dark"
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
            # Stock Comparison
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
                x=data.index, y=data["Close"], mode="lines", name=selected_stock_name
            ))
            if not compare_data.empty:
                compare_fig.add_trace(go.Scatter(
                    x=compare_data.index, y=compare_data["Close"], mode="lines", name=compare_stock
                ))
            compare_fig.update_layout(
                title="Stock Price Comparison",
                xaxis_title="Date", yaxis_title="Price (INR)", template="plotly_dark"
            )
            st.plotly_chart(compare_fig, use_container_width=True)

    except ConnectionError:
        st.error("🌐 Network error.")
    except Exception as e:
        log_api_error(e)
        st.error(f"⚠ Error loading dashboard: {e}")

with tab2:
    st.header("Your Portfolio")
    
    # Add new stock widget
    with st.form("add_portfolio_form"):
        new_symbol = st.text_input("Add Custom Symbol (e.g. ZOMATO.NS)")
        add_btn = st.form_submit_button("Add")
        if add_btn and new_symbol:
            add_to_portfolio(new_symbol.upper())
            st.success(f"Added {new_symbol.upper()}")
            st.rerun()

    symbols = get_portfolio()
    
    if not symbols:
        st.info("Your portfolio is empty. Add stocks to start tracking them.")
    else:
        for sym in symbols:
            col_a, col_b, col_c = st.columns([2, 1, 1])
            col_a.write(f"**{sym}**")
            
            # Quick price fetch for portfolio
            try:
                p_data = get_stock_data(sym, "1d")
                if not p_data.empty:
                    c_price = round(p_data["Close"].iloc[-1], 2)
                    col_b.write(f"₹{c_price}")
                else:
                    col_b.write("N/A")
            except:
                col_b.write("Error fetching price")
            
            if col_c.button("Remove", key=f"remove_{sym}"):
                remove_from_portfolio(sym)
                st.rerun()

with tab3:
    st.header("Financial AI Assistant")
    st.write("Ask the LangGraph Agent questions about stocks, news sentiment, and moving averages.")
    
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("E.g., What is the 20-day MA for Reliance?"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Analyzing..."):
                response = run_financial_agent(prompt)
                st.markdown(response)
                
        st.session_state.messages.append({"role": "assistant", "content": response})