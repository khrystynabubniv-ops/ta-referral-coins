import logging
import threading

from . import alerter, ashby_parser, coin_client, config, inbox
from .handlers import coin_handler

logger = logging.getLogger(__name__)

_stop_event = threading.Event()


def _process_row(row_id, payload, attempts) -> None:
    try:
        event = ashby_parser.parse_event(payload)
        coin_handler.process_coin_row(event)
    except coin_handler.SkipRow as exc:
        logger.info("skipping coin_inbox row %s: %s", row_id, exc)
        inbox.mark_skipped(row_id, str(exc))
        return
    except coin_client.CoinApiError as exc:
        message = f"[{exc.status_code or exc.error_code}] {exc}"
        if exc.retryable and attempts + 1 < config.WORKER_MAX_ATTEMPTS:
            logger.warning("retryable Coin API error on row %s: %s", row_id, message)
            inbox.mark_retry(row_id, message)
            return
        logger.error("Coin API error on row %s, marking failed: %s", row_id, message)
        inbox.mark_failed(row_id, message)
        alerter.send_alert(f":rotating_light: ta-referral-coins: failed to award coins for row {row_id}: {message}")
        return
    except Exception as exc:
        logger.exception("unexpected error processing coin_inbox row %s", row_id)
        if attempts + 1 < config.WORKER_MAX_ATTEMPTS:
            inbox.mark_retry(row_id, str(exc))
            return
        inbox.mark_failed(row_id, str(exc))
        alerter.send_alert(
            f":rotating_light: ta-referral-coins: row {row_id} failed after {config.WORKER_MAX_ATTEMPTS} attempts: {exc}"
        )
        return

    inbox.mark_done(row_id)


def run_once() -> None:
    for row_id, payload, attempts in inbox.fetch_pending():
        _process_row(row_id, payload, attempts)


def _loop() -> None:
    while not _stop_event.is_set():
        try:
            run_once()
        except Exception:
            logger.exception("worker loop iteration failed")
        _stop_event.wait(config.WORKER_INTERVAL_SEC)


def start() -> threading.Thread:
    _stop_event.clear()
    thread = threading.Thread(target=_loop, name="coin-worker", daemon=True)
    thread.start()
    return thread


def stop() -> None:
    _stop_event.set()
