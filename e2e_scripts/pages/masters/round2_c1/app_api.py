"""Calls to the MargBooks API signed with the logged-in browser session (same idea as pages/abha/app_api.py).

The app signs every call with per-company headers (Services/LoaderInterceptor.service.ts:45-60). A session is
taken from a call the app itself makes while an action runs; headers stay in memory and are never logged.
"""

import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from playwright.sync_api import APIRequestContext, Page, Request

from pages.base_page import BasePage
from pages.masters.round2_c1.scheme_payload import Session

CAPTURE_TIMEOUT_MS = 60_000
NOT_REPLAYED = frozenset({"host", "content-length", "cookie", "connection", "accept-encoding"})
OK_STATUS = "1"
SESSION_SCRIPT = """
() => {
    const key = JSON.stringify({key: 'LoggedInUserInfo', session: 'mb-session'});
    const info = JSON.parse(localStorage.getItem(key));
    const company = info.SelectedCompany;
    return {companyLinkid: Number(company.linkid), userLinkid: Number(info.UserLoginData.userData.linkid),
            userName: String(info.UserLoginData.userData.username),
            yearFrom: String(company.FinancialYearFrom), yearTo: String(company.FinancialYearTo)};
}
"""


class ApiRefusedError(AssertionError):
    def __init__(self, path: str, reply: dict[str, Any]) -> None:
        super().__init__(f"{path} was refused: {reply.get('status')}")


@dataclass(frozen=True)
class AppApi:
    client: APIRequestContext
    base_url: str
    headers: dict[str, str]
    session: Session

    def post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        reply: dict[str, Any] = self.client.post(self.base_url + path, data=body, headers=self.headers).json()
        return _accepted(path, reply)

    def get(self, path: str) -> dict[str, Any]:
        reply: dict[str, Any] = self.client.get(self.base_url + path, headers=self.headers).json()
        return _accepted(path, reply)


def _accepted(path: str, reply: dict[str, Any]) -> dict[str, Any]:
    status = reply.get("status")
    code = str(status.get("status") if isinstance(status, dict) else status)
    if code != OK_STATUS:
        raise ApiRefusedError(path, reply)
    return reply


class SessionCapture(BasePage):
    def during(self, action: Callable[[], object], marker: re.Pattern[str]) -> tuple[AppApi, Request]:
        """Runs `action`; returns an API signed like the first matching call it made, and that call."""
        with self.page.expect_request(
            lambda request: marker.search(request.url) is not None, timeout=CAPTURE_TIMEOUT_MS
        ) as made:
            action()
        request = made.value
        base = request.url[: marker.search(request.url).start()]  # type: ignore[union-attr]
        return AppApi(self.page.request, base, _replayable(request), self._session()), request

    def _session(self) -> Session:
        ids = self.page.evaluate(SESSION_SCRIPT)
        return Session(
            ids["companyLinkid"],
            ids["userLinkid"],
            ids["userName"],
            0,
            ids["yearFrom"][:10],
            ids["yearTo"][:10],
        )


def _replayable(request: Request) -> dict[str, str]:
    return {
        name: value
        for name, value in request.all_headers().items()
        if not name.startswith(":") and name.lower() not in NOT_REPLAYED
    }


def page_of(api_page: Page) -> SessionCapture:
    return SessionCapture(api_page)
