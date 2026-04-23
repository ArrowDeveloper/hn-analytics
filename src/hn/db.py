from contextlib import contextmanager
import os

import psycopg
import dotenv

dotenv.load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL")

@contextmanager
def get_conn():
    conn = psycopg.connect(DATABASE_URL)
    try:
        yield conn
    finally:
        conn.close()