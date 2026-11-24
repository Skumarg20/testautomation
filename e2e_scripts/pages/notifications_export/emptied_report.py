"""A report call answered with the server's own response minus its rows.

The server is asked as usual (`route.fetch`), so the columns, totals and envelope are real; only the row
lists named in `row_keys` are emptied wherever they appear in the body. This gives an empty report on a
company that has data, without inventing the response's shape.
"""

import json
from re import Pattern
from typing import Any

from playwright.sync_api import Page, Route


class EmptiedReport:
    def __init__(self, page: Page, endpoint: Pattern[str]) -> None:
        self._page = page
        self._endpoint = endpoint

    def serve_without(self, row_keys: tuple[str, ...]) -> None:
        """Call before the report is opened."""
        self._page.route(self._endpoint, lambda route: _fulfil_without_rows(route, row_keys))


def _fulfil_without_rows(route: Route, row_keys: tuple[str, ...]) -> None:
    response = route.fetch()
    body = _without_rows(response.json(), row_keys)
    route.fulfill(response=response, body=json.dumps(body), content_type="application/json")


def _without_rows(value: Any, row_keys: tuple[str, ...]) -> Any:
    if isinstance(value, dict):
        return {key: [] if key in row_keys else _without_rows(item, row_keys) for key, item in value.items()}
    if isinstance(value, list):
        return [_without_rows(item, row_keys) for item in value]
    return value
