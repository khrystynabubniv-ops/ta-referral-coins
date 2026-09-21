from src import ashby_parser, config


def _payload(event_type, **data_overrides):
    data = {
        "candidate": {
            "id": "cand-1",
            "customFields": [{"title": "Referrer Email", "value": "ref@uni.tech"}],
        },
        "application": {"id": "app-1"},
    }
    data.update(data_overrides)
    return {"type": event_type, "data": data}


def test_parses_archive_event_as_archived_outcome():
    event = ashby_parser.parse_event(_payload(config.ARCHIVE_EVENT))

    assert event.outcome == config.OUTCOME_ARCHIVED
    assert event.candidate_id == "cand-1"
    assert event.application_id == "app-1"
    assert event.referrer_email == "ref@uni.tech"


def test_parses_hired_stage_change_as_hired_outcome():
    event = ashby_parser.parse_event(_payload(config.STAGE_CHANGE_EVENT, stage={"title": "Hired"}))

    assert event.outcome == config.OUTCOME_HIRED


def test_ignores_stage_change_into_non_milestone_stage():
    event = ashby_parser.parse_event(_payload(config.STAGE_CHANGE_EVENT, stage={"title": "Phone Screen"}))

    assert event.outcome is None


def test_ignores_unrelated_event_type():
    event = ashby_parser.parse_event(_payload("candidate.created"))

    assert event.outcome is None


def test_missing_referrer_email_is_none():
    payload = {
        "type": config.ARCHIVE_EVENT,
        "data": {"candidate": {"id": "cand-2"}, "application": {"id": "app-2"}},
    }

    event = ashby_parser.parse_event(payload)

    assert event.referrer_email is None
    assert event.candidate_id == "cand-2"


def test_referrer_email_field_name_matching_is_case_insensitive():
    payload = _payload(
        config.ARCHIVE_EVENT,
        candidate={
            "id": "cand-3",
            "customFields": [{"title": "REFERRED BY EMAIL", "value": "someone@uni.tech"}],
        },
    )

    event = ashby_parser.parse_event(payload)

    assert event.referrer_email == "someone@uni.tech"


def test_top_level_referrer_email_fallback():
    payload = {
        "type": config.ARCHIVE_EVENT,
        "referrerEmail": "fallback@uni.tech",
        "data": {"candidate": {"id": "cand-4"}, "application": {"id": "app-4"}},
    }

    event = ashby_parser.parse_event(payload)

    assert event.referrer_email == "fallback@uni.tech"
