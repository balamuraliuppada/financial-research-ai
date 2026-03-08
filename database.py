import psycopg2

def connect_db():
    return psycopg2.connect(
        host="localhost",
        database="financial_ai",
        user="postgres",
        password="postgres"
    )

def create_table():
    conn = connect_db()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS stock_search_history (
            id SERIAL PRIMARY KEY,
            stock_symbol TEXT,
            time_range TEXT,
            search_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    cur.close()
    conn.close()


def save_search(symbol, period):
    conn = connect_db()
    cur = conn.cursor()

    cur.execute(
        "INSERT INTO stock_search_history (stock_symbol, time_range) VALUES (%s,%s)",
        (symbol, period)
    )

    conn.commit()
    cur.close()
    conn.close()