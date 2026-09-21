import os
import uuid

import psycopg
import pytest

DATABASE_URL = os.environ.get("DATABASE_URL")


@pytest.fixture
def pg_cursor():
    """Runs against a real Postgres (e.g. the Railway DB) when DATABASE_URL is set.

    Skipped otherwise, since the UNIQUE(candidate_id, outcome) guarantee is a
    database-level behavior that cannot be verified without a real Postgres.
    """
    if not DATABASE_URL:
        pytest.skip("DATABASE_URL is not set; skipping Postgres integration test")

    try:
        conn = psycopg.connect(DATABASE_URL)
    except psycopg.OperationalError as exc:
        pytest.skip(f"cannot connect to Postgres: {exc}")

    conn.autocommit = False
    try:
        with conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS coin_awards (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    candidate_id TEXT NOT NULL,
                    referrer_email TEXT NOT NULL,
                    outcome TEXT NOT NULL CHECK (outcome IN ('archived', 'hired')),
                    coins INT NOT NULL,
                    idempotency_key TEXT NOT NULL UNIQUE,
                    api_status TEXT,
                    api_response JSONB,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    UNIQUE (candidate_id, outcome)
                )
                """
            )
            conn.commit()
            yield cur
            conn.rollback()
    finally:
        conn.close()


def test_duplicate_candidate_and_outcome_is_rejected(pg_cursor):
    candidate_id = f"cand-{uuid.uuid4()}"

    pg_cursor.execute(
        """
        INSERT INTO coin_awards (candidate_id, referrer_email, outcome, coins, idempotency_key)
        VALUES (%s, %s, 'archived', 20, %s)
        """,
        (candidate_id, "ref@uni.tech", f"referral-coin-{candidate_id}-archived"),
    )
    pg_cursor.connection.commit()

    with pytest.raises(psycopg.errors.UniqueViolation):
        pg_cursor.execute(
            """
            INSERT INTO coin_awards (candidate_id, referrer_email, outcome, coins, idempotency_key)
            VALUES (%s, %s, 'archived', 20, %s)
            """,
            (candidate_id, "ref@uni.tech", f"referral-coin-{candidate_id}-archived-2"),
        )
    pg_cursor.connection.rollback()


def test_same_candidate_can_have_one_archived_and_one_hired_row(pg_cursor):
    candidate_id = f"cand-{uuid.uuid4()}"

    pg_cursor.execute(
        """
        INSERT INTO coin_awards (candidate_id, referrer_email, outcome, coins, idempotency_key)
        VALUES (%s, %s, 'archived', 20, %s)
        """,
        (candidate_id, "ref@uni.tech", f"referral-coin-{candidate_id}-archived"),
    )
    pg_cursor.execute(
        """
        INSERT INTO coin_awards (candidate_id, referrer_email, outcome, coins, idempotency_key)
        VALUES (%s, %s, 'hired', 50, %s)
        """,
        (candidate_id, "ref@uni.tech", f"referral-coin-{candidate_id}-hired"),
    )
    pg_cursor.connection.commit()

    pg_cursor.execute("SELECT outcome, coins FROM coin_awards WHERE candidate_id = %s ORDER BY outcome", (candidate_id,))
    rows = pg_cursor.fetchall()

    assert rows == [("archived", 20), ("hired", 50)]
