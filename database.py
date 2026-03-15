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