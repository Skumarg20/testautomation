"""The list screen of sale bills or sale returns: find a document, open it for change, or use its ⋮ menu.

Live 2026-10-09 (GST Invoice List): each row has an edit button (`button.mksBtn.edit`), a print button and a
⋮ menu (Delete, Logs, Cash Receive). The menu opens outside the row and its entries are anchors without
href, so they have no link role. Opening an adjusted bill first shows an "Alert!" naming the adjusting
voucher, which is acknowledged.
"""

import re

from playwright.sync_api import Locator, Page, expect

from pages.accounting.waiting import appears_within
from pages.components.info_alert import InfoAlert
from pages.dashboard_page import DashboardPage
from pages.sale.documents.screen import DocumentScreen

MenuPath = tuple[str, ...]
ADJUSTED_NOTICE_LOOKUP_MS = 5_000
LIST_TIMEOUT_MS = 60_000
MODIFY_LOOKUP_MS = 3_000
MODIFY_BUTTON = re.compile(r"^\s*F3\s*Modify")


class DocumentList:
    def __init__(self, page: Page, menu: MenuPath) -> None:
        self._page = page
        self._menu = menu
        self._screen = DocumentScreen(page)

    def open_for_change(self, number: str) -> None:
        self._show(number)
        # Why a class: the edit button is an icon with neither a title nor an accessible name.
        self._screen.list_row(number).locator("button.mksBtn.edit").click()
        self._screen.wait_for_loader()
        InfoAlert(self._page).acknowledge_if_shown(ADJUSTED_NOTICE_LOOKUP_MS)
        self._unlock_if_read_only()

    def _unlock_if_read_only(self) -> None:
        """The edit button sometimes opens the document read-only (footer "F3 Modify", 2026-10-09);
        F3 makes it editable, and an adjusted bill then shows its "Alert!" again."""
        modify = self._page.get_by_role("button", name=MODIFY_BUTTON)
        if appears_within(modify, MODIFY_LOOKUP_MS):
            self._page.keyboard.press("F3")
            self._screen.wait_for_loader()
            InfoAlert(self._page).acknowledge_if_shown(ADJUSTED_NOTICE_LOOKUP_MS)

    def choose_from_menu(self, number: str, action: str) -> None:
        self._show(number)
        self._screen.list_row(number).locator('button[data-toggle="dropdown"]').click()
        self._page.locator(".dropdown-menu.show .dropdown-item").filter(has_text=action).first.click()
        self._screen.wait_for_loader()

    def numbers_for(self, party: str) -> list[str]:
        """The document numbers the list shows for the party (columns `entryNo`, `tmp_LedgerName`)."""
        self._show(party)
        party_cell = self._page.locator('[col-id="tmp_LedgerName"]').get_by_text(party, exact=True)
        rows = self._rows.filter(has=party_cell)
        expect(rows.first).to_be_visible(timeout=LIST_TIMEOUT_MS)
        return [text.strip() for text in rows.locator('[col-id="entryNo"]').all_inner_texts()]

    @property
    def _rows(self) -> Locator:
        return self._page.locator('[ref="eBodyContainer"] .ag-row')

    def _show(self, search_text: str) -> None:
        """Typing before the rows have loaded is lost (the list stayed unfiltered, OA-002 on 2026-10-09),
        so the search waits for the rows. Enter is not pressed: it opens the highlighted row."""
        DashboardPage(self._page).open()
        self._screen.open_menu(self._menu)
        expect(self._rows.first).to_be_visible(timeout=LIST_TIMEOUT_MS)
        self._screen.search_list(search_text)
