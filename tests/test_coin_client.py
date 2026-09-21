from unittest.mock import MagicMock, patch

import pytest

from src import coin_client


def _response(status_code, json_body=None, text=""):
    resp = MagicMock()
    resp.status_code = status_code
    resp.text = text
    if json_body is None:
        resp.json.side_effect = ValueError("no json body")
    else:
        resp.json.return_value = json_body
    return resp


@patch("src.coin_client.requests.post")
def test_201_returns_response_body(mock_post):
    mock_post.return_value = _response(201, {"transaction": {"id": "t1"}, "recipientBalance": 100})

    result = coin_client.award_coins("referrer@uni.tech", 20, "comment", "key-201")

    assert result["recipientBalance"] == 100
    assert mock_post.call_count == 1


@pytest.mark.parametrize(
    "status_code,error_code",
    [
        (400, "validation_error"),
        (401, "token_invalid"),
        (403, "recipient_not_eligible"),
        (404, "recipient_not_found"),
        (409, "ambiguous_recipient"),
    ],
)
@patch("src.coin_client.requests.post")
def test_non_transient_errors_raise_without_retrying(mock_post, status_code, error_code):
    mock_post.return_value = _response(status_code, {"code": error_code, "message": "nope"})

    with pytest.raises(coin_client.CoinApiError) as excinfo:
        coin_client.award_coins("referrer@uni.tech", 20, "comment", f"key-{status_code}")

    assert excinfo.value.status_code == status_code
    assert excinfo.value.error_code == error_code
    assert excinfo.value.retryable is False
    assert mock_post.call_count == 1


@patch("src.coin_client.time.sleep", return_value=None)
@patch("src.coin_client.requests.post")
def test_rate_limited_retries_up_to_max_then_raises_retryable(mock_post, mock_sleep):
    mock_post.return_value = _response(429, {"code": "rate_limited", "message": "slow down"})

    with pytest.raises(coin_client.CoinApiError) as excinfo:
        coin_client.award_coins("referrer@uni.tech", 20, "comment", "key-429")

    assert excinfo.value.retryable is True
    assert excinfo.value.status_code == 429
    assert mock_post.call_count == 3
    assert mock_sleep.call_count == 2


@patch("src.coin_client.time.sleep", return_value=None)
@patch("src.coin_client.requests.post")
def test_internal_error_retries_then_succeeds(mock_post, mock_sleep):
    mock_post.side_effect = [
        _response(500, {"code": "internal_error", "message": "oops"}),
        _response(201, {"transaction": {"id": "t2"}, "recipientBalance": 42}),
    ]

    result = coin_client.award_coins("referrer@uni.tech", 20, "comment", "key-500")

    assert result["recipientBalance"] == 42
    assert mock_post.call_count == 2
    assert mock_sleep.call_count == 1


@patch("src.coin_client.time.sleep", return_value=None)
@patch("src.coin_client.requests.post")
def test_internal_error_exhausts_retries_then_raises(mock_post, mock_sleep):
    mock_post.return_value = _response(500, {"code": "internal_error", "message": "still broken"})

    with pytest.raises(coin_client.CoinApiError) as excinfo:
        coin_client.award_coins("referrer@uni.tech", 20, "comment", "key-500-fail")

    assert excinfo.value.retryable is True
    assert mock_post.call_count == 3
