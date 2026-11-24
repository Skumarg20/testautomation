"""CRM > Pending Approvals (/crm/pending-grid): transactions waiting for an approver, filtered by status."""

import re
from typing import Literal

from playwright.sync_api import Locator, expect

from pages.base_page import BasePage
from pages.crm.crm_menu import CrmMenu

ApprovalStatus = Literal["Pending", "Approved", "Reject", "All"]
SCREEN_TIMEOUT_MS = 60_000
COUNT_TEXT = re.compile(r"^Count: \d+$")


class PendingApprovals(BasePage):
    def open_from_menu(self) -> None:
        CrmMenu(self.page).open_pending_approvals()
        expect(self._heading).to_be_visible(timeout=SCREEN_TIMEOUT_MS)

    def show(self, status: ApprovalStatus) -> None:
        self._status(status).check()

    def expect_showing(self, status: ApprovalStatus) -> None:
        expect(self._status(status)).to_be_checked()

    def expect_count_shown(self) -> None:
        expect(self.page.get_by_text(COUNT_TEXT)).to_be_visible(timeout=SCREEN_TIMEOUT_MS)

    def expect_columns(self, columns: tuple[str, ...]) -> None:
        for column in columns:
            expect(self.page.get_by_role("columnheader", name=column, exact=True)).to_be_visible()

    @property
    def _heading(self) -> Locator:
        return self.page.get_by_role("heading", name="Pending Approvals", level=1)

    def _status(self, status: ApprovalStatus) -> Locator:
        return self.page.get_by_role("radio", name=status, exact=True)
