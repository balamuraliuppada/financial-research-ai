"""
fundamentals.py
───────────────
Fundamental analysis helpers for Indian stocks:
  - P/E, debt-to-equity, current ratio, EPS growth, revenue growth
  - Sector mapping for NSE/BSE
  - Indian market hours (IST)
  - INR formatting utilities
"""

import yfinance as yf
import pandas as pd
from datetime import datetime
import pytz

# ─── Indian Market Hours ──────────────────────────────────────────────────────

IST = pytz.timezone("Asia/Kolkata")

NSE_OPEN  = (9, 15)   # 09:15 IST
NSE_CLOSE = (15, 30)  # 15:30 IST


def is_market_open() -> dict:
    """Return market status and next open/close time in IST."""
    now_ist = datetime.now(IST)
    weekday  = now_ist.weekday()          # Mon=0 … Sun=6

    open_time  = now_ist.replace(hour=NSE_OPEN[0],  minute=NSE_OPEN[1],  second=0, microsecond=0)
    close_time = now_ist.replace(hour=NSE_CLOSE[0], minute=NSE_CLOSE[1], second=0, microsecond=0)

    is_weekday = weekday < 5
    in_hours   = is_weekday and open_time <= now_ist <= close_time

    return {
        "is_open":    in_hours,
        "current_ist": now_ist.strftime("%d %b %Y  %I:%M %p IST"),
        "open_time":  open_time.strftime("%I:%M %p IST"),
        "close_time": close_time.strftime("%I:%M %p IST"),
        "day":        now_ist.strftime("%A"),
    }


# ─── INR Formatting ───────────────────────────────────────────────────────────

def format_inr(value) -> str:
    """Format a number in Indian numbering system (lakhs / crores)."""
    if value is None or value == "N/A":
        return "N/A"
    try:
        v = float(value)
    except (TypeError, ValueError):
        return "N/A"

    if abs(v) >= 1e12:
        return f"₹{v/1e12:.2f}T"
    if abs(v) >= 1e7:
        return f"₹{v/1e7:.2f} Cr"
    if abs(v) >= 1e5:
        return f"₹{v/1e5:.2f} L"
    return f"₹{v:,.2f}"


# ─── Sector Map ───────────────────────────────────────────────────────────────

# Maps Yahoo Finance ticker → (display name, sector)
INDIAN_STOCKS: dict[str, tuple[str, str]] = {
    # IT
    "TCS.NS":        ("Tata Consultancy Services", "Information Technology"),
    "INFY.NS":       ("Infosys",                   "Information Technology"),
    "WIPRO.NS":      ("Wipro",                     "Information Technology"),
    "HCLTECH.NS":    ("HCL Technologies",          "Information Technology"),
    "TECHM.NS":      ("Tech Mahindra",             "Information Technology"),
    "LTIM.NS":       ("LTIMindtree",               "Information Technology"),
    "MPHASIS.NS":    ("Mphasis",                   "Information Technology"),
    # Banking & Finance
    "HDFCBANK.NS":   ("HDFC Bank",                 "Banking & Finance"),
    "ICICIBANK.NS":  ("ICICI Bank",                "Banking & Finance"),
    "SBIN.NS":       ("State Bank of India",       "Banking & Finance"),
    "KOTAKBANK.NS":  ("Kotak Mahindra Bank",       "Banking & Finance"),
    "AXISBANK.NS":   ("Axis Bank",                 "Banking & Finance"),
    "BAJFINANCE.NS": ("Bajaj Finance",             "Banking & Finance"),
    "BAJAJFINSV.NS": ("Bajaj Finserv",             "Banking & Finance"),
    # Energy & Oil
    "RELIANCE.NS":   ("Reliance Industries",       "Energy & Conglomerates"),
    "ONGC.NS":       ("ONGC",                      "Energy & Oil"),
    "NTPC.NS":       ("NTPC",                      "Energy & Power"),
    "POWERGRID.NS":  ("Power Grid Corp",           "Energy & Power"),
    # Auto
    "TATAMOTORS.NS": ("Tata Motors",               "Automobile"),
    "MARUTI.NS":     ("Maruti Suzuki",             "Automobile"),
    "M&M.NS":        ("Mahindra & Mahindra",       "Automobile"),
    "HEROMOTOCO.NS": ("Hero MotoCorp",             "Automobile"),
    "BAJAJ-AUTO.NS": ("Bajaj Auto",                "Automobile"),
    # Pharma
    "SUNPHARMA.NS":  ("Sun Pharmaceutical",        "Pharmaceuticals"),
    "DRREDDY.NS":    ("Dr. Reddy's Laboratories",  "Pharmaceuticals"),
    "CIPLA.NS":      ("Cipla",                     "Pharmaceuticals"),
    "DIVISLAB.NS":   ("Divi's Laboratories",       "Pharmaceuticals"),
    # FMCG
    "HINDUNILVR.NS": ("Hindustan Unilever",        "FMCG"),
    "ITC.NS":        ("ITC",                       "FMCG"),
    "NESTLEIND.NS":  ("Nestle India",              "FMCG"),
    "BRITANNIA.NS":  ("Britannia Industries",      "FMCG"),
    # Metals
    "TATASTEEL.NS":  ("Tata Steel",                "Metals & Mining"),
    "JSWSTEEL.NS":   ("JSW Steel",                 "Metals & Mining"),
    "HINDALCO.NS":   ("Hindalco Industries",       "Metals & Mining"),
    # Infrastructure
    "ADANIPORTS.NS": ("Adani Ports",               "Infrastructure"),
    "ULTRACEMCO.NS": ("UltraTech Cement",          "Infrastructure"),
    "GRASIM.NS":     ("Grasim Industries",         "Infrastructure"),
    # Telecom
    "BHARTIARTL.NS": ("Bharti Airtel",             "Telecom"),
}

ALL_SECTORS = sorted(set(v[1] for v in INDIAN_STOCKS.values()))

def get_sector(symbol: str) -> str:
    return INDIAN_STOCKS.get(symbol, ("Unknown", "Unknown"))[1]

def get_stocks_by_sector(sector: str) -> list[str]:
    return [sym for sym, (_, sec) in INDIAN_STOCKS.items() if sec == sector]


# ─── Fundamental Analysis ─────────────────────────────────────────────────────

def get_fundamentals(symbol: str) -> dict:
    """
    Return a dict of key fundamental metrics for a stock.
    Gracefully handles missing data.
    """
    try:
        ticker = yf.Ticker(symbol)
        info   = ticker.info

        def safe(key, default="N/A"):
            val = info.get(key)
            return val if val is not None else default

        # Valuation
        pe_ratio         = safe("trailingPE")
        forward_pe       = safe("forwardPE")
        pb_ratio         = safe("priceToBook")
        ps_ratio         = safe("priceToSalesTrailing12Months")
        ev_ebitda        = safe("enterpriseToEbitda")

        # Profitability
        profit_margin    = safe("profitMargins")
        operating_margin = safe("operatingMargins")
        roe              = safe("returnOnEquity")
        roa              = safe("returnOnAssets")

        # Debt & Liquidity
        debt_to_equity   = safe("debtToEquity")
        current_ratio    = safe("currentRatio")
        quick_ratio      = safe("quickRatio")

        # Growth (TTM vs prior year approximations)
        revenue_growth   = safe("revenueGrowth")
        earnings_growth  = safe("earningsGrowth")
        eps_ttm          = safe("trailingEps")
        eps_forward      = safe("forwardEps")

        # Size
        market_cap       = safe("marketCap")
        enterprise_value = safe("enterpriseValue")

        # Dividend
        dividend_yield   = safe("dividendYield")

        # 52-week
        week_52_high     = safe("fiftyTwoWeekHigh")
        week_52_low      = safe("fiftyTwoWeekLow")
        beta             = safe("beta")

        def pct(val):
            if val == "N/A":
                return "N/A"
            try:
                return f"{float(val)*100:.2f}%"
            except Exception:
                return "N/A"

        def ratio(val, decimals=2):
            if val == "N/A":
                return "N/A"
            try:
                return f"{float(val):.{decimals}f}x"
            except Exception:
                return "N/A"

        return {
            # Valuation
            "P/E Ratio (TTM)":           ratio(pe_ratio),
            "Forward P/E":               ratio(forward_pe),
            "P/B Ratio":                 ratio(pb_ratio),
            "P/S Ratio":                 ratio(ps_ratio),
            "EV/EBITDA":                 ratio(ev_ebitda),
            # Profitability
            "Profit Margin":             pct(profit_margin),
            "Operating Margin":          pct(operating_margin),
            "Return on Equity (ROE)":    pct(roe),
            "Return on Assets (ROA)":    pct(roa),
            # Debt
            "Debt-to-Equity":            ratio(debt_to_equity),
            "Current Ratio":             ratio(current_ratio),
            "Quick Ratio":               ratio(quick_ratio),
            # Growth
            "Revenue Growth (YoY)":      pct(revenue_growth),
            "Earnings Growth (YoY)":     pct(earnings_growth),
            "EPS (TTM)":                 f"₹{float(eps_ttm):.2f}" if eps_ttm != "N/A" else "N/A",
            "EPS (Forward)":             f"₹{float(eps_forward):.2f}" if eps_forward != "N/A" else "N/A",
            # Size
            "Market Cap":                format_inr(market_cap),
            "Enterprise Value":          format_inr(enterprise_value),
            # Income
            "Dividend Yield":            pct(dividend_yield),
            # Range
            "52-Week High":              f"₹{float(week_52_high):.2f}" if week_52_high != "N/A" else "N/A",
            "52-Week Low":               f"₹{float(week_52_low):.2f}" if week_52_low != "N/A" else "N/A",
            "Beta":                      f"{float(beta):.2f}" if beta != "N/A" else "N/A",
        }
    except Exception as e:
        return {"Error": str(e)}


def get_sector_comparison(sector: str) -> pd.DataFrame:
    """
    Fetch key metrics for all stocks in a given sector and return as DataFrame.
    """
    symbols = get_stocks_by_sector(sector)
    if not symbols:
        return pd.DataFrame()

    rows = []
    for sym in symbols:
        try:
            info = yf.Ticker(sym).info
            pe   = info.get("trailingPE")
            pb   = info.get("priceToBook")
            roe  = info.get("returnOnEquity")
            de   = info.get("debtToEquity")
            mg   = info.get("profitMargins")
            cap  = info.get("marketCap")
            rev  = info.get("revenueGrowth")
            name = INDIAN_STOCKS.get(sym, (sym, ""))[0]

            rows.append({
                "Symbol":            sym,
                "Company":           name,
                "P/E":               round(pe, 2)  if pe  else None,
                "P/B":               round(pb, 2)  if pb  else None,
                "ROE (%)":           round(roe*100, 2) if roe else None,
                "D/E":               round(de, 2)  if de  else None,
                "Net Margin (%)":    round(mg*100, 2) if mg  else None,
                "Revenue Growth (%)":round(rev*100,2) if rev else None,
                "Market Cap":        format_inr(cap),
            })
        except Exception:
            continue

    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.set_index("Symbol")
    return df
