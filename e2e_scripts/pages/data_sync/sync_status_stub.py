"""The data sync request state, answered by the test instead of the DataSync server (J35 DS-19 to DS-21).

Both the layout (`homelayout.component.ts:3457-3473`, called from `ngOnInit` at `:425`) and the Data Sync
screen (`data-syncreport.component.ts:200-226`) POST `{complinkid, dbinfolinkid}` to
`OfflineOnline/SyncRequeststatus`. The answer `{statuscode: "200", data: {status: "1"}}` sets
`DatasyncSetting.isDataSyncEnable`, which locks transactions ("Transaction locked after datasync",
`global.ts:19714`); statuscode 201 means no request (`OfflineOnlineDataSync.cs:2167-2171`). The stub is a
page route, so it changes only this page's view: nothing is written on the server, and the shared company
never gets a real request. `CompanyKeys` reads the ids the app sends from its own stored login (as
`pages/company_switch_page.py`).
"""

import json
from dataclasses import dataclass
from enum import Enum

from playwright.sync_api import Page, Route

from pages.data_sync.data_sync_screen import STATUS_ENDPOINT

COMPANY_KEYS_SCRIPT = """
() => {
    const info = JSON.parse(
        localStorage.getItem('{"key":"LoggedInUserInfo","session":"mb-session"}') || 'null');
    return {
        complinkid: Number(info?.SelectedCompany?.linkid ?? 0),
        dbinfolinkid: Number(info?.UserLoginData?.userData?.DBInfolinkid ?? 0),
    };
}
"""
NO_REQUEST_STATUS_CODE = "201"


class RequestStatus(Enum):
    """`tbldataSyncRequest.status` (`data-syncreport.component.ts:208-215`)."""

    PENDING = "0"
    APPROVED = "1"
    CANCELLED = "2"


@dataclass(frozen=True)
class CompanyKeys:
    complinkid: int
    dbinfolinkid: int

    @classmethod
    def of_selected_company(cls, page: Page) -> "CompanyKeys":
        stored = page.evaluate(COMPANY_KEYS_SCRIPT)
        return cls(complinkid=int(stored["complinkid"]), dbinfolinkid=int(stored["dbinfolinkid"]))


class SyncStatusStub:
    """Answers one company's status with a chosen state and every other company with "no request"."""

    def __init__(self, page: Page, company: CompanyKeys, status: RequestStatus) -> None:
        self._page = page
        self._company = company
        self._status = status
        self._asked_for: list[int] = []

    def install(self) -> None:
        """Call before the page loads the layout: the layout asks once, on start."""
        self._page.route(STATUS_ENDPOINT, self._answer)

    @property
    def asked_for(self) -> tuple[int, ...]:
        """The complinkid of every status request answered so far."""
        return tuple(self._asked_for)

    def _answer(self, route: Route) -> None:
        asked = int(json.loads(route.request.post_data or "{}").get("complinkid", 0))
        self._asked_for.append(asked)
        route.fulfill(status=200, content_type="application/json", body=json.dumps(self._reply_for(asked)))

    def _reply_for(self, complinkid: int) -> dict[str, object]:
        if complinkid == self._company.complinkid:
            return {"statuscode": "200", "data": {"status": self._status.value, "Remarks": ""}}
        return {"statuscode": NO_REQUEST_STATUS_CODE, "data": None}
