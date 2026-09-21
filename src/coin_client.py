import time

import requests

from . import config

_RETRYABLE_STATUSES = {429, 500}
_MAX_ATTEMPTS = 3
_BASE_BACKOFF_SEC = 1.0


class CoinApiError(Exception):
    def __init__(self, message, status_code=None, error_code=None, retryable=False, response_body=None):
        super().__init__(message)
        self.status_code = status_code
        self.error_code = error_code
        self.retryable = retryable
        self.response_body = response_body


def _safe_body(response):
    try:
        return response.json()
    except ValueError:
        return response.text


def award_coins(email: str, coins: int, comment: str, idempotency_key: str) -> dict:
    """Call the Coin Awards API. Retries 429/500 with exponential backoff.

    Raises CoinApiError on any non-201 outcome; `.retryable` tells the caller
    whether attempts were already exhausted for a transient error (True) or
    whether the error is a permanent rejection that should not be retried (False).
    """
    body = {
        "recipient": {"email": email},
        "coins": coins,
        "comment": comment,
        "idempotencyKey": idempotency_key,
    }
    headers = {
        "Authorization": f"Bearer {config.COIN_API_TOKEN}",
        "Content-Type": "application/json",
    }

    for attempt in range(1, _MAX_ATTEMPTS + 1):
        response = requests.post(config.COIN_API_URL, json=body, headers=headers, timeout=15)

        if response.status_code == 201:
            return response.json()

        response_body = _safe_body(response)
        error_code = response_body.get("code") if isinstance(response_body, dict) else None
        message = response_body.get("message") if isinstance(response_body, dict) else None
        message = message or f"Coin API returned {response.status_code}"

        if response.status_code in _RETRYABLE_STATUSES:
            if attempt < _MAX_ATTEMPTS:
                time.sleep(_BASE_BACKOFF_SEC * (2 ** (attempt - 1)))
                continue
            raise CoinApiError(
                message,
                status_code=response.status_code,
                error_code=error_code,
                retryable=True,
                response_body=response_body,
            )

        raise CoinApiError(
            message,
            status_code=response.status_code,
            error_code=error_code,
            retryable=False,
            response_body=response_body,
        )
