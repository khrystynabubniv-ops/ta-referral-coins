import logging

import requests

from . import config

logger = logging.getLogger(__name__)


def send_alert(text: str) -> None:
    if not config.SLACK_BOT_TOKEN or not config.ALERT_CHANNEL:
        logger.warning("Slack alert not configured, dropping alert: %s", text)
        return

    try:
        requests.post(
            "https://slack.com/api/chat.postMessage",
            headers={"Authorization": f"Bearer {config.SLACK_BOT_TOKEN}"},
            json={"channel": config.ALERT_CHANNEL, "text": text},
            timeout=10,
        )
    except requests.RequestException:
        logger.exception("failed to post Slack alert")
