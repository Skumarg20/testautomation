"""Gives the patient list two known ABHA states without writing a patient: the real `GetPatientList` reply
is fetched from the server and passed on with `IsAbhaStatus` set on one patient and cleared on another.

The grid's "Abha Status" cell shows "Active" when `IsAbhaStatus` is true and nothing otherwise
(`Component/Shared/template-abha-text-color.ts:13-18`). Setting a real ABHA link needs `SaveAbhadetails`,
which the guard blocks (decision N3), so the reply is changed in the browser instead. `capture_patched`
proves the grid's list call went through this patch.
"""

import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from playwright.sync_api import Page, Route

from pages.components.stubbed_endpoint import InterceptionNotProvenError

PATIENT_LIST = re.compile(r"MedicalPrescription/GetPatientList", re.IGNORECASE)
PATCH_TIMEOUT_MS = 30_000


class NotEnoughPatientsError(AssertionError):
    def __init__(self, count: int) -> None:
        super().__init__(f"The patient list returned {count} own patient(s); the ABHA status check needs two")


@dataclass(frozen=True)
class PatchedPatients:
    active_name: str
    inactive_name: str


class PatientAbhaStatusPatch:
    def __init__(self, page: Page) -> None:
        self._page = page
        self._patched: list[PatchedPatients] = []

    def install(self) -> None:
        self._page.route(PATIENT_LIST, self._patch)

    def capture_patched(self, action: Callable[[], object]) -> PatchedPatients:
        patched_before = len(self._patched)
        with self._page.expect_response(PATIENT_LIST, timeout=PATCH_TIMEOUT_MS):
            action()
        if len(self._patched) <= patched_before:
            raise InterceptionNotProvenError(PATIENT_LIST, "the list reply was not patched")
        return self._patched[-1]

    def _patch(self, route: Route) -> None:
        response = route.fetch()
        body: dict[str, Any] = response.json()
        rows = [row for row in body.get("Data") or [] if not row.get("Ispredefine")]
        if len(rows) < 2:
            raise NotEnoughPatientsError(len(rows))
        for row in rows:
            row["IsAbhaStatus"] = False
        rows[0]["IsAbhaStatus"] = True
        self._patched.append(PatchedPatients(active_name=rows[0]["Name"], inactive_name=rows[1]["Name"]))
        route.fulfill(response=response, json=body)
