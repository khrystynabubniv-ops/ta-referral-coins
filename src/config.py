import os

from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL", "")

ASHBY_API_KEY = os.environ.get("ASHBY_API_KEY", "")
ASHBY_API_BASE_URL = os.environ.get("ASHBY_API_BASE_URL", "https://api.ashbyhq.com")
ASHBY_WEBHOOK_SECRET = os.environ.get("ASHBY_WEBHOOK_SECRET", "")

COIN_API_TOKEN = os.environ.get("COIN_API_TOKEN", "")
COIN_API_URL = os.environ.get("COIN_API_URL", "")

SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "")
ALERT_CHANNEL = os.environ.get("ALERT_CHANNEL", "")

WORKER_INTERVAL_SEC = int(os.environ.get("WORKER_INTERVAL_SEC", "5"))
WORKER_MAX_ATTEMPTS = int(os.environ.get("WORKER_MAX_ATTEMPTS", "3"))

# Kill switch: until this is "true", webhooks are still queued but the worker
# leaves them pending and never calls the Coin API.
COIN_AWARDS_ENABLED = os.environ.get("COIN_AWARDS_ENABLED", "false").strip().lower() == "true"

PORT = int(os.environ.get("PORT", "5000"))

# Ashby webhook event types we react to.
STAGE_CHANGE_EVENT = "candidate.stagechange"
ARCHIVE_EVENT = "candidate.archive"

OUTCOME_ARCHIVED = "archived"
OUTCOME_HIRED = "hired"

HIRED_STAGE_NAME = os.environ.get("HIRED_STAGE_NAME", "Hired")

# Stages that "count" towards a referral payout on archive, even if the
# candidate did not end up getting hired. Configurable/extendable via env.
MILESTONE_STAGES = {
    stage.strip()
    for stage in os.environ.get(
        "MILESTONE_STAGES",
        "Hiring Manager Interview,Bar-raising,Test",
    ).split(",")
    if stage.strip()
}

COIN_MAP = {
    OUTCOME_ARCHIVED: int(os.environ.get("COINS_ARCHIVED", "20")),
    OUTCOME_HIRED: int(os.environ.get("COINS_HIRED", "50")),
}

COIN_COMMENTS = {
    OUTCOME_ARCHIVED: "Дякуємо за реферальну рекомендацію — кандидат пройшов до фінального етапу",
    OUTCOME_HIRED: "Дякуємо за реферальну рекомендацію — кандидата найнято!",
}

# Custom-field titles on the Ashby candidate/application that may carry the
# referrer's email. Matched case-insensitively.
REFERRER_EMAIL_FIELD_NAMES = {
    name.strip().lower()
    for name in os.environ.get(
        "REFERRER_EMAIL_FIELD_NAMES",
        "Referrer Email,Referred By Email,Referral Email",
    ).split(",")
    if name.strip()
}
