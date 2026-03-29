# Financial Research AI — Indian Stock Market Dashboard

An AI-powered Financial Research Dashboard for analysing NSE/BSE Indian stock market data.

## Features

| Feature                  | Details                                                                   |
| ------------------------ | ------------------------------------------------------------------------- |
| **NSE/BSE Data**         | Yahoo Finance `.NS` / `.BO` suffixes; Redis caching                       |
| **SQLite Watchlist**     | Persistent watchlist with notes, sector tags, live prices                 |
| **Fundamental Analysis** | P/E, Forward P/E, P/B, ROE, Debt-to-Equity, EPS, Revenue Growth, and more |
| **Sector Comparison**    | Side-by-side comparison of 9 Indian market sectors with bar charts        |
| **INR Formatting**       | Prices in ₹; large numbers formatted as Lakhs / Crores                    |
| **Market Hours**         | Live IST clock; NSE/BSE open/closed indicator (09:15–15:30 IST)           |
| **AI Assistant**         | Gemini 2.5 Flash + LangGraph ReAct agent with 6 tools                     |
| **Technical Indicators** | RSI (14-day), 20-day MA, Volume chart                                     |
| **News Sentiment**       | TextBlob sentiment analysis on latest headlines                           |
| **Portfolio**            | Persistent portfolio with live prices and change tracking                 |

## Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set your API key
cp _env .env
# Edit .env: GOOGLE_API_KEY=your_key_here

# 3. Run
streamlit run app.py
```

## Project Structure

```
app.py            – Main Streamlit UI (5 tabs)
fundamentals.py   – P/E, ROE, sector maps, INR formatting, market hours
database.py       – SQLite: portfolio + watchlist CRUD
agent.py          – LangGraph ReAct agent (Gemini 2.5 Flash)
tools.py          – 6 LangChain tools for the agent
logger.py         – File-based API call logging
requirements.txt  – Python dependencies
```

## AI Agent Tools

1. `get_stock_price` — Current price + recent history
2. `get_news_sentiment` — TextBlob sentiment on latest headlines
3. `get_rsi_and_ma` — RSI (14) + MA (20)
4. `get_fundamental_analysis` — Full fundamental metrics
5. `get_sector_analysis` — Sector-wide comparison table
6. `get_market_status` — NSE/BSE open/closed + IST time
