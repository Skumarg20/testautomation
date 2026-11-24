"""Calls to the MargBooks API made with the logged-in browser session, for the API-level ABHA scenarios
(AB-36..AB-38).

The suite's `api` fixture has no login, and the app signs every call with encrypted per-company headers set
by its interceptor (`Services/LoaderInterceptor.service.ts:45-60`). So a session is taken from a call the
app itself makes: its headers are kept in memory only (never logged or returned), and the browser context's
request client sends the test's calls with them. These calls do not pass the page's routes, so the
`SendGuard` does not see them; the module calls only `MedicalPrescription` endpoints, never the ABDM proxy.
"""

import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from playwright.sync_api import APIRequestContext, Request

from pages.base_page import BasePage

PATIENT_LIST = re.compile(r"MedicalPrescription/GetPatientList", re.IGNORECASE)
CONTROLLER = "MedicalPrescription/"
ABHA_DETAILS = "GetPatientAbhaDetails"
SAVE_ABHA_DETAILS = "SaveAbhadetails"
NOT_REPLAYED_HEADERS = frozenset({"host", "content-length", "cookie", "connection", "accept-encoding"})
CAPTURE_TIMEOUT_MS = 60_000
OK_STATUS = "1"

SESSION_IDS_SCRIPT = """
() => {
    const key = JSON.stringify({key: 'LoggedInUserInfo', session: 'mb-session'});
    const info = JSON.parse(localStorage.getItem(key));
    const user = info.UserLoginData.userData;
    return {companyLinkid: Number(info.SelectedCompany.linkid), userLinkid: Number(user.linkid),
            userName: String(user.username)};
}
"""


@dataclass(frozen=True)
class SessionIds:
    company_linkid: int
    user_linkid: int
    user_name: str


class AbhaDetailsApi:
    """`MedicalPrescription` calls signed as the company the session was taken in."""

    def __init__(self, client: APIRequestContext, controller_url: str, headers: dict[str, str]) -> None:
        self._client = client
        self._controller_url = controller_url
        self._headers = headers

    @property
    def controller_url(self) -> str:
        return self._controller_url

    def abha_rows_of(self, patient_linkid: int) -> list[dict[str, Any]]:
        response = self._client.get(
            self._controller_url + ABHA_DETAILS,
            params={"patientlinkid": patient_linkid},
            headers=self._headers,
        )
        rows: list[dict[str, Any]] = response.json().get("Data") or []
        return rows

    def save_abha_details(self, body: dict[str, object]) -> dict[str, Any]:
        response = self._client.post(
            self._controller_url + SAVE_ABHA_DETAILS, data=body, headers=self._headers
        )
        reply: dict[str, Any] = response.json()
        return reply


@dataclass(frozen=True)
class CompanySession:
    api: AbhaDetailsApi
    ids: SessionIds


@dataclass(frozen=True)
class OwnCompany:
    session: CompanySession
    patient_linkids: list[int]


def was_accepted(reply: dict[str, Any]) -> bool:
    return str((reply.get("status") or {}).get("status")) == OK_STATUS


class AppSession(BasePage):
    def session_ids(self) -> SessionIds:
        ids = self.page.evaluate(SESSION_IDS_SCRIPT)
        return SessionIds(int(ids["companyLinkid"]), int(ids["userLinkid"]), str(ids["userName"]))

    def patient_list_session(self, open_list: Callable[[], object]) -> tuple[AbhaDetailsApi, list[int]]:
        """Runs `open_list` (opens the patient master); returns the session it signed its list call with
        and the linkids of the company's own patients in the first page of the list."""
        with self.page.expect_response(PATIENT_LIST, timeout=CAPTURE_TIMEOUT_MS) as response_info:
            open_list()
        response = response_info.value
        rows = response.json().get("Data") or []
        patients = [int(row["linkid"]) for row in rows if not row.get("Ispredefine")]
        return self._api_from(response.request), patients

    def any_call_session(self, action: Callable[[], object], controller_url: str) -> AbhaDetailsApi:
        """The session of the first signed API call `action` makes (any screen; headers are per company)."""
        with self.page.expect_request(_is_signed_api_call, timeout=CAPTURE_TIMEOUT_MS) as request_info:
            action()
        return AbhaDetailsApi(self.page.request, controller_url, _replayable(request_info.value))

    def _api_from(self, request: Request) -> AbhaDetailsApi:
        controller_url = request.url[: request.url.index(CONTROLLER) + len(CONTROLLER)]
        return AbhaDetailsApi(self.page.request, controller_url, _replayable(request))


def _is_signed_api_call(request: Request) -> bool:
    return "complinkid" in request.headers


def _replayable(request: Request) -> dict[str, str]:
    return {
        name: value
        for name, value in request.all_headers().items()
        if not name.startswith(":") and name.lower() not in NOT_REPLAYED_HEADERS
    }
