"""Answers a routed API call with a MargBooks JSON envelope instead of the server."""

import json

from playwright.sync_api import Route

SUCCESS_STATUS = {"status": "1", "error": {}}


def success_envelope(data: object) -> dict[str, object]:
    """`{"Data": data, "status": {"status": "1"}}`, the shape the app checks for success."""
    return {"Data": data, "status": SUCCESS_STATUS}


def fulfil_with_data(route: Route, data: object) -> None:
    route.fulfill(status=200, content_type="application/json", body=json.dumps(success_envelope(data)))
