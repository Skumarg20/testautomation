"""A call to the MargBooks API with no token, no tenant header and no cookies."""

from dataclasses import dataclass
from typing import Any

from playwright.sync_api import Playwright

CALL_TIMEOUT_MS = 30_000


@dataclass(frozen=True)
class ApiAnswer:
    """The API answers HTTP 200 and puts its own status in the body:
    `{"status": {"status": "0", "httpstatuscode": "417", "error": {"message": ...}}}` (live 2026-10-12)."""

    status_code: str
    error_message: str
    has_data: bool


def anonymous_get(playwright: Playwright, url: str) -> ApiAnswer:
    context = playwright.request.new_context()
    try:
        body: dict[str, Any] = context.get(url, timeout=CALL_TIMEOUT_MS).json()
    finally:
        context.dispose()
    status = body.get("status", {})
    return ApiAnswer(
        status_code=str(status.get("httpstatuscode", "")),
        error_message=str(status.get("error", {}).get("message", "")),
        has_data="Data" in body,
    )
