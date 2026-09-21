import logging

from psycopg.types.json import Jsonb

from .. import ashby_client, coin_client, config, db

logger = logging.getLogger(__name__)


class SkipRow(Exception):
    """Row does not need (or no longer needs) a coin award; mark it done, no error."""


def _reserve_award(candidate_id, outcome, referrer_email, coins, idempotency_key):
    """Insert a placeholder award row, guarded by UNIQUE(candidate_id, outcome).

    Returns the new row's id, or None if a row for this candidate/outcome
    already exists (i.e. it was already reserved/awarded by a prior attempt).
    """
    with db.cursor() as cur:
        cur.execute(
            """
            INSERT INTO coin_awards (candidate_id, referrer_email, outcome, coins, idempotency_key)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (candidate_id, outcome) DO NOTHING
            RETURNING id
            """,
            (candidate_id, referrer_email, outcome, coins, idempotency_key),
        )
        row = cur.fetchone()
        return row[0] if row else None


def _existing_award(candidate_id, outcome):
    with db.cursor() as cur:
        cur.execute(
            "SELECT id, api_status FROM coin_awards WHERE candidate_id = %s AND outcome = %s",
            (candidate_id, outcome),
        )
        return cur.fetchone()


def _record_api_result(award_id, api_status, api_response) -> None:
    with db.cursor() as cur:
        cur.execute(
            "UPDATE coin_awards SET api_status = %s, api_response = %s WHERE id = %s",
            (api_status, Jsonb(api_response), award_id),
        )


def process_coin_row(event) -> None:
    """Process one ParsedEvent: decide whether coins are owed, then award them.

    Raises SkipRow when nothing should be awarded. Raises coin_client.CoinApiError
    when the Coin API call itself failed; the caller decides whether to retry
    based on `.retryable`.
    """
    if event.outcome is None:
        raise SkipRow("event does not correspond to a coin-awarding outcome")

    if not event.candidate_id or not event.referrer_email:
        raise SkipRow("missing candidate_id or referrer_email in payload")

    if event.outcome == config.OUTCOME_ARCHIVED:
        # A candidate who was already hired keeps the "hired" award only;
        # ignore any archive event that arrives for them afterwards.
        if _existing_award(event.candidate_id, config.OUTCOME_HIRED) is not None:
            raise SkipRow("candidate already hired; ignoring later archive event")

        if not event.application_id:
            raise SkipRow("missing application_id, cannot verify milestone stages")

        if not ashby_client.has_reached_milestone_stage(event.application_id, config.MILESTONE_STAGES):
            raise SkipRow("candidate archived without reaching a milestone stage")

    coins = config.COIN_MAP[event.outcome]
    comment = config.COIN_COMMENTS[event.outcome]
    idempotency_key = f"referral-coin-{event.candidate_id}-{event.outcome}"

    award_id = _reserve_award(event.candidate_id, event.outcome, event.referrer_email, coins, idempotency_key)
    if award_id is None:
        existing = _existing_award(event.candidate_id, event.outcome)
        if existing is None:
            raise SkipRow("award race: reservation missing and no existing row found")
        award_id, api_status = existing
        if api_status == "success":
            raise SkipRow("coins already awarded for this candidate/outcome")

    try:
        api_response = coin_client.award_coins(
            email=event.referrer_email,
            coins=coins,
            comment=comment,
            idempotency_key=idempotency_key,
        )
    except coin_client.CoinApiError as exc:
        _record_api_result(
            award_id,
            f"error:{exc.status_code or 'network'}",
            {"error_code": exc.error_code, "message": str(exc), "body": exc.response_body},
        )
        raise

    _record_api_result(award_id, "success", api_response)
    logger.info("awarded %s coins to %s for candidate %s (%s)", coins, event.referrer_email, event.candidate_id, event.outcome)
