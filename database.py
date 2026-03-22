import psycopg2

DB_NAME = "financial_ai"
DB_USER = "postgres"
DB_PASSWORD = "#PostSQL"
DB_HOST = "localhost"
DB_PORT = "5432"


def get_connection():
    return psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )


def create_table():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS stock_searches (
            id SERIAL PRIMARY KEY,
            symbol VARCHAR(20),
            period VARCHAR(10),
            searched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS portfolio (
            id SERIAL PRIMARY KEY,
            symbol VARCHAR(20) UNIQUE,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    conn.commit()
    cur.close()
    conn.close()


def save_search(symbol, period):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "INSERT INTO stock_searches (symbol, period) VALUES (%s, %s)",
        (symbol, period)
    )

    conn.commit()
    cur.close()
    conn.close()


def add_to_portfolio(symbol):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO portfolio (symbol) VALUES (%s) ON CONFLICT (symbol) DO NOTHING",
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
        cur.execute("DELETE FROM portfolio WHERE symbol = %s", (symbol,))
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
        rows = cur.fetchall()
        symbols = [row[0] for row in rows]
    except Exception as e:
        print(f"Error fetching portfolio: {e}")
    finally:
        cur.close()
        conn.close()
    return symbols
