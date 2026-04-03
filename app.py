import redis
import streamlit as st
import yfinance as yf
import plotly.graph_objs as go
import pandas as pd
from backend.database import (
    create_table, save_search,
    add_to_portfolio, remove_from_portfolio, get_portfolio,
    add_to_watchlist, remove_from_watchlist, get_watchlist, update_watchlist_note,
)
from backend.logger import log_api_call, log_api_error
from streamlit_autorefresh import st_autorefresh
from textblob import TextBlob
import requests
from backend.agent import run_financial_agent
from backend.fundamentals import (
    get_fundamentals, get_sector_comparison, get_sector,
    is_market_open, format_inr, ALL_SECTORS, INDIAN_STOCKS,
)

# ─── Page Config ──────────────────────────────────────────────────────────────
st.set_page_config(page_title="Financial Research AI", layout="wide", page_icon="📈")

# Auto-refresh every 5 minutes
st_autorefresh(interval=300000)

create_table()

# ─── Redis (optional, graceful degradation) ───────────────────────────────────
import os

try:
    redis_url = os.getenv("REDIS_URL")

    if redis_url:
        redis_client = redis.from_url(redis_url)
    else:
        redis_client = redis.Redis(host="localhost", port=6379, db=0)

    redis_client.ping()
    print("Redis connected")

except Exception as e:
    print("Redis not available:", e)
    redis_client = None

# ─── Global CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
[data-testid="metric-container"] { background:#1e2533; border-radius:10px; padding:12px; }
.stTabs [data-baseweb="tab-list"] { gap:8px; }
.stTabs [data-baseweb="tab"] { border-radius:8px 8px 0 0; padding:6px 18px; }
div[data-testid="stSidebarContent"] { background:#0f1117; }
.market-open   { color:#00c896; font-weight:700; font-size:1.1rem; }
.market-closed { color:#ff4b4b; font-weight:700; font-size:1.1rem; }
</style>
""", unsafe_allow_html=True)

# ─── Sidebar – Market Status & Quick Links ────────────────────────────────────
with st.sidebar:
    st.title("📈 Financial Research AI")
    st.markdown("---")

    mkt = is_market_open()
    if mkt["is_open"]:
        st.markdown(f'<p class="market-open">🟢 NSE/BSE OPEN</p>', unsafe_allow_html=True)
    else:
        st.markdown(f'<p class="market-closed">🔴 NSE/BSE CLOSED</p>', unsafe_allow_html=True)

    st.caption(mkt["current_ist"])
    st.caption(f"Trading hours: {mkt['open_time']} – {mkt['close_time']}")
    st.markdown("---")

    st.subheader("Quick Add to Watchlist")
    quick_sym = st.text_input("Symbol (e.g. ZOMATO.NS)", key="sidebar_sym")
    quick_note = st.text_input("Note (optional)", key="sidebar_note")
    if st.button("➕ Add to Watchlist"):
        if quick_sym:
            sym_up = quick_sym.upper()
            sector = get_sector(sym_up)
            name   = INDIAN_STOCKS.get(sym_up, (sym_up, ""))[0]
            add_to_watchlist(sym_up, name=name, sector=sector, note=quick_note)
            st.success(f"Added {sym_up} to watchlist!")

# ─── Stock Universe ───────────────────────────────────────────────────────────
stock_options = {v[0]: k for k, v in INDIAN_STOCKS.items() if k.endswith(".NS")}
# Ensure the original 5 are always present
stock_options.update({
    "Reliance Industries":             "RELIANCE.NS",
    "Tata Consultancy Services (TCS)": "TCS.NS",
    "Infosys":                         "INFY.NS",
    "HDFC Bank":                       "HDFCBANK.NS",
    "ICICI Bank":                      "ICICIBANK.NS",
})

# ─── Data Fetching ────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def get_stock_data(symbol: str, period: str) -> pd.DataFrame:
    cache_key = f"{symbol}_{period}"
    if redis_client is not None:
        cached = redis_client.get(cache_key)
        if cached:
            return pd.read_json(cached.decode("utf-8"))

    stock = yf.Ticker(symbol)
    log_api_call(symbol, period)

    data = stock.history(period="1d", interval="5m") if period == "1d" else stock.history(period=period)

    if redis_client is not None and not data.empty:
        redis_client.set(cache_key, data.to_json(), ex=300)

    return data


@st.cache_data(ttl=600)
def cached_fundamentals(symbol: str) -> dict:
    return get_fundamentals(symbol)


@st.cache_data(ttl=600)
def cached_sector_comparison(sector: str) -> pd.DataFrame:
    return get_sector_comparison(sector)


# ─── News Sentiment ───────────────────────────────────────────────────────────
def get_news_sentiment(company_name: str):
    url = (
        f"https://newsapi.org/v2/everything?q={company_name}"
        f"&pageSize=5&apiKey=7b74b92a008c43d7a0e8fc6f8712d2f2"
    )
    try:
        news_data = requests.get(url).json()
        if news_data.get("status") != "ok":
            return None, []
        articles  = news_data.get("articles", [])
        sentiments, titles = [], []
        for art in articles:
            title = art.get("title", "")
            if title:
                titles.append(title)
                sentiments.append(TextBlob(title).sentiment.polarity)
        if not sentiments:
            return None, []
        return sum(sentiments) / len(sentiments), titles
    except Exception:
        return None, []


# ─── Tabs ─────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Dashboard",
    "💼 Portfolio",
    "📋 Watchlist",
    "🔬 Fundamentals & Sectors",
    "🤖 AI Assistant",
])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 – DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    st.header("Stock Dashboard")

    col_sel1, col_sel2 = st.columns(2)
    with col_sel1:
        selected_stock_name = st.selectbox("Select an Indian Stock", sorted(stock_options.keys()))
        symbol = stock_options[selected_stock_name]
    with col_sel2:
        period = st.selectbox("Select Time Range", ["1d", "5d", "1mo", "3mo", "6mo", "1y", "5y"])

    try:
        stock = yf.Ticker(symbol)
        data  = get_stock_data(symbol, period)
        save_search(symbol, period)

        if data.empty:
            st.warning("⚠ No stock data available.")
        else:
            info         = stock.info
            company_name = info.get("longName", selected_stock_name)
            market_cap   = info.get("marketCap", "N/A")
            volume       = info.get("volume", "N/A")

            # Technical Indicators
            data["MA20"] = data["Close"].rolling(window=20).mean()
            delta = data["Close"].diff()
            gain  = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss  = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs    = gain / loss
            data["RSI"] = 100 - (100 / (1 + rs))

            current_price  = round(data["Close"].iloc[-1], 2)
            previous_close = round(data["Close"].iloc[-2], 2)
            price_change   = round(current_price - previous_close, 2)
            percent_change = round((price_change / previous_close) * 100, 2)
            period_high    = round(data["High"].max(), 2)
            period_low     = round(data["Low"].min(), 2)

            st.subheader(f"{company_name} ({symbol})")
            st.caption(f"Sector: **{get_sector(symbol)}**")

            btn_col1, btn_col2 = st.columns([1, 8])
            with btn_col1:
                if st.button("➕ Portfolio"):
                    add_to_portfolio(symbol)
                    st.success(f"{symbol} added to portfolio!")
            with btn_col2:
                if st.button("⭐ Watchlist"):
                    add_to_watchlist(symbol, name=company_name, sector=get_sector(symbol))
                    st.success(f"{symbol} added to watchlist!")

            col1, col2, col3 = st.columns(3)
            col1.metric("Current Price (₹)", f"₹{current_price}", f"{price_change:+.2f} ({percent_change:+.2f}%)")
            col2.metric(f"{period} High", f"₹{period_high}")
            col3.metric(f"{period} Low",  f"₹{period_low}")

            st.markdown("---")
            col4, col5, col6 = st.columns(3)
            col4.write(f"**Market Cap:** {format_inr(market_cap)}")
            col5.write(f"**Volume:** {volume:,}" if isinstance(volume, int) else f"**Volume:** {volume}")
            col6.metric("RSI (14-day)", round(data["RSI"].iloc[-1], 2))

            # RSI interpretation
            rsi_val = data["RSI"].iloc[-1]
            if rsi_val > 70:
                st.warning("⚠ RSI > 70: Stock may be **overbought**")
            elif rsi_val < 30:
                st.info("ℹ RSI < 30: Stock may be **oversold**")

            st.markdown("---")

            # Main Chart
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=data.index, y=data["Close"],  mode="lines", name="Price",    line=dict(color="#00c896", width=2)))
            fig.add_trace(go.Scatter(x=data.index, y=data["MA20"],   mode="lines", name="MA20",     line=dict(color="#f7931a", width=1.5, dash="dot")))
            fig.update_layout(
                title=f"{company_name} — Price & 20-day MA",
                xaxis_title="Date", yaxis_title="Price (₹)",
                template="plotly_dark", hovermode="x unified",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            )
            st.plotly_chart(fig, use_container_width=True)

            # Volume bar chart
            fig_vol = go.Figure()
            fig_vol.add_trace(go.Bar(x=data.index, y=data["Volume"], name="Volume", marker_color="#4b77d1"))
            fig_vol.update_layout(title="Volume", template="plotly_dark", height=220, margin=dict(t=30, b=10))
            st.plotly_chart(fig_vol, use_container_width=True)

            # News Sentiment
            st.markdown("---")
            st.subheader("News Sentiment Analysis")
            sentiment, news_titles = get_news_sentiment(selected_stock_name)
            if sentiment is not None:
                if sentiment > 0.1:
                    st.success(f"Overall Sentiment: Positive 📈 ({sentiment:.2f})")
                elif sentiment < -0.1:
                    st.error(f"Overall Sentiment: Negative 📉 ({sentiment:.2f})")
                else:
                    st.info(f"Overall Sentiment: Neutral ({sentiment:.2f})")
                for title in news_titles:
                    st.write("•", title)
            else:
                st.warning("News data not available.")

            # Stock Comparison
            st.markdown("---")
            st.subheader("Stock Comparison")
            compare_stock  = st.selectbox("Select another stock to compare", sorted(stock_options.keys()), key="compare_select")
            compare_symbol = stock_options[compare_stock]
            compare_data   = get_stock_data(compare_symbol, period)

            compare_fig = go.Figure()
            # Normalise to 100 for fair comparison
            base1 = data["Close"].iloc[0]
            base2 = compare_data["Close"].iloc[0] if not compare_data.empty else 1

            compare_fig.add_trace(go.Scatter(
                x=data.index, y=(data["Close"] / base1) * 100,
                mode="lines", name=selected_stock_name, line=dict(color="#00c896"),
            ))
            if not compare_data.empty:
                compare_fig.add_trace(go.Scatter(
                    x=compare_data.index, y=(compare_data["Close"] / base2) * 100,
                    mode="lines", name=compare_stock, line=dict(color="#f7931a"),
                ))
            compare_fig.update_layout(
                title="Normalised Price Comparison (Base = 100)",
                xaxis_title="Date", yaxis_title="Indexed Price",
                template="plotly_dark", hovermode="x unified",
            )
            st.plotly_chart(compare_fig, use_container_width=True)

    except ConnectionError:
        st.error("🌐 Network error.")
    except Exception as e:
        log_api_error(e)
        st.error(f"⚠ Error loading dashboard: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 – PORTFOLIO
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.header("Your Portfolio")

    with st.form("add_portfolio_form"):
        new_symbol = st.text_input("Add Custom Symbol (e.g. ZOMATO.NS)")
        add_btn    = st.form_submit_button("Add to Portfolio")
        if add_btn and new_symbol:
            add_to_portfolio(new_symbol.upper())
            st.success(f"Added {new_symbol.upper()}")
            st.rerun()

    symbols = get_portfolio()
    if not symbols:
        st.info("Your portfolio is empty. Add stocks to start tracking them.")
    else:
        header_cols = st.columns([3, 2, 2, 2, 1])
        header_cols[0].markdown("**Symbol**")
        header_cols[1].markdown("**Price (₹)**")
        header_cols[2].markdown("**Change**")
        header_cols[3].markdown("**Sector**")
        header_cols[4].markdown("**Action**")
        st.markdown("---")

        for sym in symbols:
            col_a, col_b, col_c, col_d, col_e = st.columns([3, 2, 2, 2, 1])
            col_a.write(f"**{sym}**")
            try:
                p_data = get_stock_data(sym, "1d")
                if not p_data.empty and len(p_data) >= 2:
                    cp  = round(p_data["Close"].iloc[-1], 2)
                    pc  = round(p_data["Close"].iloc[-2], 2)
                    chg = round(cp - pc, 2)
                    pct = round((chg / pc) * 100, 2)
                    col_b.write(f"₹{cp}")
                    color = "🟢" if chg >= 0 else "🔴"
                    col_c.write(f"{color} {chg:+.2f} ({pct:+.2f}%)")
                else:
                    col_b.write("N/A")
                    col_c.write("—")
            except Exception:
                col_b.write("Error")
                col_c.write("—")
            col_d.write(get_sector(sym))
            if col_e.button("🗑", key=f"rm_port_{sym}"):
                remove_from_portfolio(sym)
                st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 – WATCHLIST (SQLite-backed)
# ══════════════════════════════════════════════════════════════════════════════
with tab3:
    st.header("⭐ Stock Watchlist")
    st.caption("Saved to a local SQLite database — persists across sessions.")

    with st.form("add_watchlist_form"):
        wl_cols = st.columns([2, 2, 2, 3])
        wl_sym  = wl_cols[0].text_input("Symbol*", placeholder="TATASTEEL.NS")
        wl_name = wl_cols[1].text_input("Company name", placeholder="Tata Steel")
        wl_sec  = wl_cols[2].selectbox("Sector", [""] + ALL_SECTORS)
        wl_note = wl_cols[3].text_input("Note", placeholder="Watching for breakout above ₹150")
        wl_add  = st.form_submit_button("➕ Add to Watchlist")
        if wl_add and wl_sym:
            add_to_watchlist(wl_sym.upper(), name=wl_name, sector=wl_sec, note=wl_note)
            st.success(f"Added {wl_sym.upper()} to watchlist!")
            st.rerun()

    watchlist = get_watchlist()
    if not watchlist:
        st.info("Your watchlist is empty. Add stocks using the form above or the sidebar.")
    else:
        h = st.columns([2, 3, 2, 3, 2, 1])
        for col, label in zip(h, ["Symbol", "Company", "Sector", "Note", "Price", ""]):
            col.markdown(f"**{label}**")
        st.markdown("---")

        for item in watchlist:
            sym = item["symbol"]
            cols = st.columns([2, 3, 2, 3, 2, 1])
            cols[0].write(f"**{sym}**")
            cols[1].write(item.get("name") or "—")
            cols[2].write(item.get("sector") or "—")

            # Inline note edit
            new_note = cols[3].text_input("", value=item.get("note") or "", key=f"note_{sym}", label_visibility="collapsed")
            if new_note != (item.get("note") or ""):
                update_watchlist_note(sym, new_note)

            # Live price
            try:
                wd = get_stock_data(sym, "1d")
                if not wd.empty:
                    cols[4].write(f"₹{round(wd['Close'].iloc[-1], 2)}")
                else:
                    cols[4].write("N/A")
            except Exception:
                cols[4].write("—")

            if cols[5].button("🗑", key=f"rm_wl_{sym}"):
                remove_from_watchlist(sym)
                st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 – FUNDAMENTALS & SECTOR COMPARISON
# ══════════════════════════════════════════════════════════════════════════════
with tab4:
    st.header("🔬 Fundamental Analysis & Sector Comparison")

    fund_tab, sector_tab = st.tabs(["📌 Single Stock Fundamentals", "🏭 Sector Comparison"])

    # ── Single Stock Fundamentals ──────────────────────────────────────────────
    with fund_tab:
        fund_stock = st.selectbox(
            "Select Stock for Fundamental Analysis",
            sorted(stock_options.keys()),
            key="fund_select",
        )
        fund_symbol = stock_options[fund_stock]

        if st.button("Fetch Fundamentals", key="fetch_fund"):
            with st.spinner(f"Fetching fundamentals for {fund_symbol}…"):
                fundamentals = cached_fundamentals(fund_symbol)

            if "Error" in fundamentals:
                st.error(f"Could not load fundamentals: {fundamentals['Error']}")
            else:
                ticker_info = yf.Ticker(fund_symbol).info
                st.subheader(f"{ticker_info.get('longName', fund_stock)} — Fundamentals")
                st.caption(f"Sector: **{get_sector(fund_symbol)}**  |  Exchange: NSE")

                # ── Valuation block ──
                st.markdown("#### 📊 Valuation")
                v_cols = st.columns(5)
                val_keys = ["P/E Ratio (TTM)", "Forward P/E", "P/B Ratio", "P/S Ratio", "EV/EBITDA"]
                for col, key in zip(v_cols, val_keys):
                    col.metric(key, fundamentals.get(key, "N/A"))

                # ── Profitability ──
                st.markdown("#### 💰 Profitability")
                p_cols = st.columns(4)
                prof_keys = ["Profit Margin", "Operating Margin", "Return on Equity (ROE)", "Return on Assets (ROA)"]
                for col, key in zip(p_cols, prof_keys):
                    col.metric(key, fundamentals.get(key, "N/A"))

                # ── Debt & Liquidity ──
                st.markdown("#### 🏦 Debt & Liquidity")
                d_cols = st.columns(3)
                debt_keys = ["Debt-to-Equity", "Current Ratio", "Quick Ratio"]
                for col, key in zip(d_cols, debt_keys):
                    col.metric(key, fundamentals.get(key, "N/A"))

                # ── Growth ──
                st.markdown("#### 📈 Growth & EPS")
                g_cols = st.columns(4)
                grow_keys = ["Revenue Growth (YoY)", "Earnings Growth (YoY)", "EPS (TTM)", "EPS (Forward)"]
                for col, key in zip(g_cols, grow_keys):
                    col.metric(key, fundamentals.get(key, "N/A"))

                # ── Market ──
                st.markdown("#### 🌐 Market Data")
                m_cols = st.columns(5)
                mkt_keys = ["Market Cap", "Enterprise Value", "Dividend Yield", "52-Week High", "52-Week Low"]
                for col, key in zip(m_cols, mkt_keys):
                    col.metric(key, fundamentals.get(key, "N/A"))

                st.metric("Beta (Volatility)", fundamentals.get("Beta", "N/A"))

    # ── Sector Comparison ──────────────────────────────────────────────────────
    with sector_tab:
        selected_sector = st.selectbox("Select a Sector", ALL_SECTORS, key="sector_select")

        if st.button("Compare Sector", key="compare_sector"):
            with st.spinner(f"Fetching data for all {selected_sector} stocks…"):
                df_sector = cached_sector_comparison(selected_sector)

            if df_sector.empty:
                st.warning("No data available for this sector.")
            else:
                st.subheader(f"{selected_sector} — Sector Comparison")
                st.dataframe(
                    df_sector.style
                        .format(na_rep="N/A")
                        .background_gradient(subset=["P/E", "ROE (%)", "Net Margin (%)"], cmap="RdYlGn"),
                    use_container_width=True,
                )

                # Radar / bar chart for ROE & P/E
                if "P/E" in df_sector.columns and "ROE (%)" in df_sector.columns:
                    fig_bar = go.Figure()
                    df_plot = df_sector.dropna(subset=["P/E"])
                    fig_bar.add_trace(go.Bar(
                        x=df_plot["Company"] if "Company" in df_plot.columns else df_plot.index,
                        y=df_plot["P/E"],
                        name="P/E Ratio",
                        marker_color="#4b77d1",
                    ))
                    fig_bar.update_layout(
                        title=f"{selected_sector} — P/E Ratio Comparison",
                        template="plotly_dark", xaxis_tickangle=-30,
                    )
                    st.plotly_chart(fig_bar, use_container_width=True)

                    df_roe = df_sector.dropna(subset=["ROE (%)"])
                    fig_roe = go.Figure()
                    fig_roe.add_trace(go.Bar(
                        x=df_roe["Company"] if "Company" in df_roe.columns else df_roe.index,
                        y=df_roe["ROE (%)"],
                        name="ROE (%)",
                        marker_color="#00c896",
                    ))
                    fig_roe.update_layout(
                        title=f"{selected_sector} — Return on Equity (%)",
                        template="plotly_dark", xaxis_tickangle=-30,
                    )
                    st.plotly_chart(fig_roe, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 – AI ASSISTANT
# ══════════════════════════════════════════════════════════════════════════════
with tab5:
    st.header("🤖 Financial AI Assistant")
    st.write(
        "Ask anything about Indian stocks — prices, fundamentals, news sentiment, "
        "moving averages, sector comparisons, or market status."
    )
    st.caption("Powered by Gemini 2.5 Flash + LangGraph ReAct Agent")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Suggested prompts
    suggested = [
        "What is the P/E ratio of TCS?",
        "Compare IT sector stocks by ROE",
        "Is the market open right now?",
        "Show RSI and MA for Reliance",
        "What's the news sentiment for Infosys?",
    ]
    st.markdown("**💡 Try asking:**")
    sug_cols = st.columns(len(suggested))
    for col, sug in zip(sug_cols, suggested):
        if col.button(sug, key=f"sug_{sug[:10]}"):
            st.session_state.messages.append({"role": "user", "content": sug})
            with st.spinner("Analysing…"):
                resp = run_financial_agent(sug)
            st.session_state.messages.append({"role": "assistant", "content": resp})
            st.rerun()

    st.markdown("---")

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("Ask the AI assistant…"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            with st.spinner("Analysing…"):
                response = run_financial_agent(prompt)
                st.markdown(response)
        st.session_state.messages.append({"role": "assistant", "content": response})

    if st.session_state.messages:
        if st.button("🗑 Clear Chat"):
            st.session_state.messages = []
            st.rerun()
