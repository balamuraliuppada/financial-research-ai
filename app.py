import streamlit as st
import yfinance as yf
import plotly.graph_objs as go
import redis
import pandas as pd
from database import create_table, save_search
from logger import log_api_call, log_api_error
from streamlit_autorefresh import st_autorefresh

st_autorefresh(interval=60000, key="datarefresh")

create_table()
try:
    redis_client = redis.Redis(host="localhost", port=6379, db=0)
    redis_client.ping()
except:
    redis_client = None

st.set_page_config(page_title="Financial Research AI", layout="wide")

st.title("Financial Research AI - Stock Dashboard")

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
    ["1mo", "3mo", "6mo", "1y", "5y"]
)


def get_stock_data(symbol, period):

    cache_key = f"{symbol}_{period}"

    if redis_client is not None:
        cached_data = redis_client.get(cache_key)

        if cached_data:
            cached_data = cached_data.decode("utf-8")
            return pd.read_json(cached_data)

    stock = yf.Ticker(symbol)
    log_api_call(symbol, period)
    data = stock.history(period=period)

    if redis_client is not None:
        redis_client.set(cache_key, data.to_json(), ex=300)

    return data


try:

    stock = yf.Ticker(symbol)

    data = get_stock_data(symbol, period)
    save_search(symbol, period)

    if data.empty:
        st.warning("⚠ No stock data available for this symbol or time range.")
        st.stop()

    info = stock.info

    company_name = info.get("longName", selected_stock_name)
    market_cap = info.get("marketCap", "N/A")
    volume = info.get("volume", "N/A")

    current_price = round(data["Close"].iloc[-1], 2)
    previous_close = round(data["Close"].iloc[-2], 2)

    price_change = round(current_price - previous_close, 2)
    percent_change = round((price_change / previous_close) * 100, 2)

    period_high = round(data["High"].max(), 2)
    period_low = round(data["Low"].min(), 2)

    st.subheader(f"{company_name} ({symbol})")

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Current Price (₹)",
        current_price,
        f"{price_change} ({percent_change}%)"
    )

    col2.metric(f"{period} High", period_high)
    col3.metric(f"{period} Low", period_low)

    st.markdown("---")

    col4, col5 = st.columns(2)

    col4.write(f"**Market Cap:** {market_cap}")
    col5.write(f"**Volume:** {volume}")

    st.markdown("---")


    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=data.index,
        y=data["Close"],
        mode="lines",
        name="Closing Price"
    ))

    fig.update_layout(
        title=f"{company_name} - Price Timeline",
        xaxis_title="Date",
        yaxis_title="Price (INR)",
        template="plotly_dark",
        xaxis=dict(
            rangeselector=dict(
                buttons=list([
                    dict(count=1, label="1M", step="month", stepmode="backward"),
                    dict(count=3, label="3M", step="month", stepmode="backward"),
                    dict(count=6, label="6M", step="month", stepmode="backward"),
                    dict(count=1, label="1Y", step="year", stepmode="backward"),
                    dict(step="all")
                ])
            ),
            rangeslider=dict(visible=True),
            type="date"
        )
    )

    st.plotly_chart(fig, use_container_width=True)


except ConnectionError:
    st.error("🌐 Network error. Please check your internet connection.")

except ValueError:
    st.error("⚠ Invalid data received from the API.")

except Exception as e:
    log_api_error(e)
    st.error(f"⚠ Unexpected error occurred: {e}")