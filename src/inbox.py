from psycopg.types.json import Jsonb

from . import db


def enqueue(payload: dict) -> str:
    with db.cursor() as cur:
        cur.execute(
            "INSERT INTO coin_inbox (payload) VALUES (%s) RETURNING id",
            (Jsonb(payload),),
        )
        return str(cur.fetchone()[0])


def fetch_pending(limit: int = 20):
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT id, payload, attempts
            FROM coin_inbox
            WHERE status = 'pending'
            ORDER BY received_at ASC
            LIMIT %s
            """,
            (limit,),
        )
        return cur.fetchall()


def mark_done(row_id) -> None:
    with db.cursor() as cur:
        cur.execute("UPDATE coin_inbox SET status = 'done' WHERE id = %s", (row_id,))


def mark_skipped(row_id, reason: str) -> None:
    with db.cursor() as cur:
        cur.execute(
            "UPDATE coin_inbox SET status = 'skipped', last_error = %s WHERE id = %s",
            (reason, row_id),
        )


def mark_retry(row_id, error: str) -> None:
    with db.cursor() as cur:
        cur.execute(
            """
            UPDATE coin_inbox
            SET attempts = attempts + 1, last_error = %s
            WHERE id = %s
            """,
            (error, row_id),
        )


def mark_failed(row_id, error: str) -> None:
    with db.cursor() as cur:
        cur.execute(
            """
            UPDATE coin_inbox
            SET status = 'failed', attempts = attempts + 1, last_error = %s
            WHERE id = %s
            """,
            (error, row_id),
        )
