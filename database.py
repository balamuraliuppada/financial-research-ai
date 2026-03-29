import sqlite3
import os
from datetime import datetime

DB_PATH = "financial_ai.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def create_table():
    conn = get_connection()
    cur = conn.cursor()

    cur.executescript("""
        CREATE TABLE IF NOT EXISTS stock_searches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            period TEXT NOT NULL,
            searched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS portfolio (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT UNIQUE NOT NULL,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS watchlist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            name TEXT,
            sector TEXT,
            note TEXT,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(symbol)
        );
    """)

    conn.commit()
    cur.close()
    conn.close()


def save_search(symbol, period):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO stock_searches (symbol, period) VALUES (?, ?)",
        (symbol, period)
    )
    conn.commit()
    cur.close()
    conn.close()


# ─── Portfolio ────────────────────────────────────────────────────────────────

def add_to_portfolio(symbol):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT OR IGNORE INTO portfolio (symbol) VALUES (?)",
            (symbol,)
        )
        conn.commit()
    except Exception as e:
        print(f"Error adding to portfolio: {e}")
    finally:
        cur.close()
        conn.close()


def remove_from_portfolio(symbol):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM portfolio WHERE symbol = ?", (symbol,))
        conn.commit()
    except Exception as e:
        print(f"Error removing from portfolio: {e}")
    finally:
        cur.close()
        conn.close()


def get_portfolio():
    conn = get_connection()
    cur = conn.cursor()
    symbols = []
    try:
        cur.execute("SELECT symbol FROM portfolio ORDER BY added_at DESC")
        symbols = [row["symbol"] for row in cur.fetchall()]
    except Exception as e:
        print(f"Error fetching portfolio: {e}")
    finally:
        cur.close()
        conn.close()
    return symbols


# ─── Watchlist ────────────────────────────────────────────────────────────────

def add_to_watchlist(symbol: str, name: str = "", sector: str = "", note: str = ""):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """INSERT INTO watchlist (symbol, name, sector, note)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(symbol) DO UPDATE SET
                   name=excluded.name,
                   sector=excluded.sector,
                   note=excluded.note""",
            (symbol.upper(), name, sector, note)
        )
        conn.commit()
    except Exception as e:
        print(f"Error adding to watchlist: {e}")
    finally:
        cur.close()
        conn.close()


def remove_from_watchlist(symbol: str):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM watchlist WHERE symbol = ?", (symbol.upper(),))
        conn.commit()
    except Exception as e:
        print(f"Error removing from watchlist: {e}")
    finally:
        cur.close()
        conn.close()


def get_watchlist():
    conn = get_connection()
    cur = conn.cursor()
    rows = []
    try:
        cur.execute("SELECT symbol, name, sector, note, added_at FROM watchlist ORDER BY added_at DESC")
        rows = [dict(r) for r in cur.fetchall()]
    except Exception as e:
        print(f"Error fetching watchlist: {e}")
    finally:
        cur.close()
        conn.close()
    return rows


def update_watchlist_note(symbol: str, note: str):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("UPDATE watchlist SET note=? WHERE symbol=?", (note, symbol.upper()))
        conn.commit()
    except Exception as e:
        print(f"Error updating note: {e}")
    finally:
        cur.close()
        conn.close()
