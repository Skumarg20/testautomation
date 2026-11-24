"""The Support Ticket list, `/support/support-ticket` (`support-ticket.component.html`,
`support-ticket.component.ts`). Locators from the Angular source, not yet checked live.

The grid is ag-Grid 19 (`#supportTicket`): rows carry `row-index`, cells carry the column's `col-id`
(the field name: `TicketNo`, `SubProblemTypeMargDescriptin`, `Description`, `Status`).
"""

import json
import re

from playwright.sync_api import Locator, expect

from pages.base_page import BasePage
from pages.components.shortcut import press_until_visible
from pages.support.desk_endpoints import TICKET_LIST
from pages.support.ticket_modal import CREATE_TITLE, TicketModal

PATH = "/support/support-ticket"
LIST_TIMEOUT_MS = 60_000
HEADING = "Support Ticket"
# What scopes the list request (`support-ticket.component.ts:419-424`): the login and its licence, no company.
LIST_SCOPE_FIELDS = ("UserId", "UserTypeId", "LicNo")
SEARCH_KEY_DELAY_MS = 50
REOPEN = "Reopen"


class SupportTicketList(BasePage):
    def open(self) -> None:
        self.goto(PATH, LIST_TIMEOUT_MS)
        self.expect_loaded()

    def open_capturing_scope(self) -> dict[str, object]:
        """Opens the list and returns the scope fields of the ticket-list request it sends (a read)."""
        with self.page.expect_request(TICKET_LIST, timeout=LIST_TIMEOUT_MS) as request_info:
            self.open()
        body: dict[str, object] = json.loads(request_info.value.post_data or "{}")
        return {field: body.get(field) for field in LIST_SCOPE_FIELDS}

    def expect_loaded(self) -> None:
        expect(self.page).to_have_url(re.compile(re.escape(PATH)), timeout=LIST_TIMEOUT_MS)
        expect(self.page.get_by_role("heading", name=HEADING, exact=True)).to_be_visible(
            timeout=LIST_TIMEOUT_MS
        )

    def expect_header_actions(self) -> None:
        expect(self._home_link).to_be_visible()
        expect(self._remote_support).to_be_visible()
        expect(self._create_button).to_be_visible()

    def expect_remote_support_link(self, href: str) -> None:
        expect(self._remote_support).to_have_attribute("href", href)
        expect(self._remote_support).to_have_attribute("target", "_blank")

    def go_home(self) -> None:
        self._home_link.click()
        # Why: callers go offline right after; the dashboard must have loaded first.
        expect(self.page).to_have_url(re.compile("/dashboard"), timeout=LIST_TIMEOUT_MS)

    @property
    def _home_link(self) -> Locator:
        # Why main: the sidebar has its own "Home" link; this is the one in the page header.
        return self.page.get_by_role("main").get_by_role("link", name="Home", exact=True)

    def start_ticket(self) -> TicketModal:
        self._create_button.click()
        return TicketModal(self.page, CREATE_TITLE)

    def start_ticket_with_f2(self) -> TicketModal:
        modal = TicketModal(self.page, CREATE_TITLE)
        press_until_visible(self.page, "F2", modal.dialog)
        return modal

    def column_headers(self) -> list[str]:
        headers = self._grid.get_by_role("columnheader")
        expect(headers.first).to_be_visible(timeout=LIST_TIMEOUT_MS)
        return [text.strip() for text in headers.all_inner_texts()]

    def ticket_numbers_top_down(self) -> list[str]:
        """The Ticket ID cells in display order; ag-Grid keeps rows in DOM order of creation, not display."""
        expect(self._ticket_cells.first).to_be_visible(timeout=LIST_TIMEOUT_MS)
        numbered: list[tuple[int, str]] = []
        for row in self._rows.all():
            ticket_no = row.locator('[col-id="TicketNo"]').inner_text().strip()
            if ticket_no:
                numbered.append((int(row.get_attribute("row-index") or 0), ticket_no))
        return [ticket_no for _, ticket_no in sorted(numbered)]

    def focus_ticket(self, ticket_no: str) -> None:
        self._row(ticket_no).locator('[col-id="TicketNo"]').click()

    def expect_other_info(self, label: str, value: str) -> None:
        # Why CSS: the "Other Info" labels are not tied to their values (no for/aria); each pair shares a row.
        pair = self.page.locator(".borderLable .form-group").filter(
            has=self.page.get_by_text(label, exact=True)
        )
        expect(pair).to_contain_text(value)

    def open_chat_by_double_click(self, ticket_no: str) -> None:
        self._row(ticket_no).locator('[col-id="Description"]').dblclick()

    def search(self, text: str) -> None:
        """Typed key by key: marg-search filters on key events."""
        # Why the role: the first LIST_SEARCH_BOX match is the <marg-search> wrapper, which takes no keys.
        box = self.page.get_by_role("searchbox", name="Search", exact=True)
        box.click()
        self.page.keyboard.press("Control+A")
        self.page.keyboard.type(text, delay=SEARCH_KEY_DELAY_MS)

    def expect_listed(self, ticket_no: str) -> None:
        expect(self._row(ticket_no)).to_have_count(1)

    def expect_not_listed(self, ticket_no: str) -> None:
        expect(self._row(ticket_no)).to_have_count(0)

    def ask_to_edit(self, ticket_no: str) -> None:
        self._row(ticket_no).get_by_role("button", name=re.compile("Edit")).click()

    def ask_to_delete(self, ticket_no: str) -> None:
        self._row(ticket_no).get_by_role("button", name="Delete").click()

    def expect_reopen_offered(self, ticket_no: str) -> None:
        expect(self._row(ticket_no).get_by_text(REOPEN, exact=True)).to_be_visible()

    def expect_reopen_not_offered(self, ticket_no: str) -> None:
        expect(self._row(ticket_no).get_by_text(REOPEN, exact=True)).to_have_count(0)

    def reopen(self, ticket_no: str) -> None:
        self._row(ticket_no).get_by_text(REOPEN, exact=True).click()

    @property
    def _create_button(self) -> Locator:
        return self.page.get_by_role("button", name="Create/F2")

    @property
    def _remote_support(self) -> Locator:
        return self.page.get_by_role("link", name="Remote Support")

    @property
    def _grid(self) -> Locator:
        # Why CSS: ag-Grid exposes only ids, row-index and col-id; the screen has no test ids.
        return self.page.locator("#supportTicket")

    @property
    def _rows(self) -> Locator:
        return self._grid.locator('[ref="eBodyContainer"] [row-index]')

    @property
    def _ticket_cells(self) -> Locator:
        return self._rows.locator('[col-id="TicketNo"]')

    def _row(self, ticket_no: str) -> Locator:
        cell = self.page.locator(
            '[col-id="TicketNo"]', has_text=re.compile(rf"^\s*{re.escape(ticket_no)}\s*$")
        )
        return self._rows.filter(has=cell)
