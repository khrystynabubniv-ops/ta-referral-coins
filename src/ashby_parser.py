from dataclasses import dataclass
from typing import Optional

from . import config


@dataclass
class ParsedEvent:
    outcome: Optional[str]
    candidate_id: Optional[str]
    application_id: Optional[str]
    referrer_email: Optional[str]
    raw: dict


def _find_referrer_email(payload: dict) -> Optional[str]:
    data = payload.get("data") or {}

    for holder in (data.get("candidate") or {}, data.get("application") or {}):
        for field in holder.get("customFields") or []:
            title = str(field.get("title", "")).strip().lower()
            if title in config.REFERRER_EMAIL_FIELD_NAMES and field.get("value"):
                return field["value"]

    return data.get("referrerEmail") or payload.get("referrerEmail")


def parse_event(payload: dict) -> ParsedEvent:
    """Parse an Ashby webhook payload into a normalized event.

    ``outcome`` is one of ``config.OUTCOME_ARCHIVED``, ``config.OUTCOME_HIRED``,
    or ``None`` when the event doesn't correspond to a coin-awarding outcome
    (e.g. a stage change into a non-terminal stage, or an unrelated event type).
    """
    event_type = payload.get("type")
    data = payload.get("data") or {}
    candidate = data.get("candidate") or {}
    application = data.get("application") or {}

    candidate_id = candidate.get("id") or application.get("candidateId")
    application_id = application.get("id")
    referrer_email = _find_referrer_email(payload)

    outcome = None
    if event_type == config.ARCHIVE_EVENT:
        outcome = config.OUTCOME_ARCHIVED
    elif event_type == config.STAGE_CHANGE_EVENT:
        stage = data.get("stage") or data.get("newStage") or {}
        if stage.get("title") == config.HIRED_STAGE_NAME:
            outcome = config.OUTCOME_HIRED

    return ParsedEvent(
        outcome=outcome,
        candidate_id=candidate_id,
        application_id=application_id,
        referrer_email=referrer_email,
        raw=payload,
    )
