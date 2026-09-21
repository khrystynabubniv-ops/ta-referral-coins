import requests
from requests.auth import HTTPBasicAuth

from . import config


class AshbyApiError(Exception):
    pass


def get_application_history(application_id: str) -> list:
    """Fetch the stage history for an Ashby application.

    Ashby authenticates API requests with HTTP Basic auth using the API key
    as the username and an empty password.
    """
    response = requests.post(
        f"{config.ASHBY_API_BASE_URL}/applicationHistory.list",
        json={"applicationId": application_id},
        auth=HTTPBasicAuth(config.ASHBY_API_KEY, ""),
        timeout=15,
    )
    response.raise_for_status()
    body = response.json()
    if not body.get("success", False):
        raise AshbyApiError(f"Ashby API error: {body.get('errors')}")
    return body.get("results", [])


def has_reached_milestone_stage(application_id: str, milestone_stages) -> bool:
    history = get_application_history(application_id)
    visited_stages = {
        entry["stage"]["title"]
        for entry in history
        if entry.get("stage", {}).get("title")
    }
    return bool(visited_stages & set(milestone_stages))
