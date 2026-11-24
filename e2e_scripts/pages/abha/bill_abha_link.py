"""The ABHA link a sale bill carries to the server, seen without saving an ABHA-linked bill.

The bill save sends the chosen ABHA as `PatientAbhaDetails` (`processout.transaction.component.ts:11869`;
the server stores `patientAbhaLinkId`, `margerpdal/SaleChallanBill.cs:1826`). A saved ABHA-linked bill may be
forwarded by the server to the ABHA connector (`SaleChallanBill.cs:3618-3668`), which no browser route can
stop, so the save is answered here with a refusal and only the request body is read.

Reopening a bill reads `PatientAbhaDetails` from `BillSales/Get` and turns the button green
(`processout.transaction.component.ts:4486-4488`); `SavedBillAbhaPatch` adds the fake link to that reply of a
plain bill, so no ABHA-linked bill has to exist.
"""

import re
from collections.abc import Callable
from typing import Any

from playwright.sync_api import Page, Route

from pages.components.stubbed_endpoint import InterceptionNotProvenError, StubReply

BILL_SAVE = re.compile(r"/BillSales/Save(\?|$)", re.IGNORECASE)
# `res.status.status != "1"` shows the error and keeps the bill open; nothing is saved.
BILL_NOT_SAVED_REPLY = StubReply({"status": {"status": "0", "message": "QA stub: bill not saved"}})
BILL_GET = re.compile(r"/BillSales/Get(\?|$)", re.IGNORECASE)
PATCH_TIMEOUT_MS = 30_000


class SavedBillAbhaPatch:
    def __init__(self, page: Page, abha_row: dict[str, object]) -> None:
        self._page = page
        self._abha_row = abha_row
        self._patched = 0

    def install(self) -> None:
        self._page.route(BILL_GET, self._patch)

    def capture_patched(self, action: Callable[[], object]) -> None:
        patched_before = self._patched
        with self._page.expect_response(BILL_GET, timeout=PATCH_TIMEOUT_MS):
            action()
        if self._patched <= patched_before:
            raise InterceptionNotProvenError(BILL_GET, "the bill reply was not patched")

    def _patch(self, route: Route) -> None:
        response = route.fetch()
        body: dict[str, Any] = response.json()
        if body.get("Data"):
            body["Data"]["PatientAbhaDetails"] = self._abha_row
            self._patched += 1
        route.fulfill(response=response, json=body)


class NoAbhaLinkSentError(AssertionError):
    def __init__(self) -> None:
        super().__init__("The bill save request carried no PatientAbhaDetails")


def abha_link_in(body: object) -> dict[str, Any]:
    """The `PatientAbhaDetails` object anywhere in the save request (its nesting is not seen live yet)."""
    if isinstance(body, dict):
        for key, value in body.items():
            if key.lower() == "patientabhadetails" and isinstance(value, dict):
                return value
            found = _abha_link_or_none(value)
            if found is not None:
                return found
    if isinstance(body, list):
        for value in body:
            found = _abha_link_or_none(value)
            if found is not None:
                return found
    raise NoAbhaLinkSentError()


def _abha_link_or_none(body: object) -> dict[str, Any] | None:
    try:
        return abha_link_in(body)
    except NoAbhaLinkSentError:
        return None
