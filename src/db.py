import contextlib

import psycopg

from . import config


@contextlib.contextmanager
def cursor():
    """Yield a cursor whose transaction is committed on success, rolled back on error."""
    conn = psycopg.connect(config.DATABASE_URL)
    try:
        with conn:
            with conn.cursor() as cur:
                yield cur
    finally:
        conn.close()
