"""Sale checklist rows 8, 9, 10 and 38 (party half): the "Select Party" window of a new sale bill.

The window is `LedgerMasterComponent` (`Component/Master/Ledger/ledger.component.ts`, LM) opened by
`processout.transaction.component.ts:3270-3300` (PO). It only opens by itself while Ask Party in Retail
Billing = Ask ("1"), so each test holds that setting and puts the original back.
"""

from collections.abc import Iterator

import pytest
from playwright.sync_api import expect

from pages.sale.checklist.bill_screen import ChecklistBill, standard_party
from pages.sale.checklist.request_log import logging_requests
from pages.sale.checklist.sale_setting import ASK_PARTY, setting_held
from pages.stock.search_typing import KEY_DELAY_MS

pytestmark = [
    pytest.mark.p1,
    pytest.mark.journey("sale-bill-creation"),
    pytest.mark.xdist_group("chemist-tenant"),
]

ASK = "1"
FULL_PAGE_ROWS = 20  # LM:3599 asks 25 rows per page after the first
SEARCH_TEXT_LENGTH = 3
GRID_ROW_COUNT = ".ag-root[aria-rowcount]"
LEDGER_NAME_CELL = '[col-id="LedgerName"]'


@pytest.fixture
def asking_bill(bill: ChecklistBill) -> Iterator[ChecklistBill]:
    """A fresh bill with the party being asked, so the party window opens from the bill date."""
    with setting_held(bill, ASK_PARTY, ASK):
        bill.reopen()
        yield bill


def open_party_window(bill: ChecklistBill) -> None:
    bill.press_enter_on_date()
    expect(bill.party_window).to_be_visible(timeout=20_000)


def test_party_window_opens_with_the_cursor_in_its_search_box(asking_bill: ChecklistBill) -> None:
    """Row 8: LM:491 and LM:2853 focus the window's search box (`viewChildSearchItems`) as it opens."""
    open_party_window(asking_bill)

    expect(asking_bill.party_window.get_by_role("searchbox")).to_be_focused()


def test_party_window_highlights_the_party_used_last(asking_bill: ChecklistBill) -> None:
    """Row 8: reopened, the window selects the party already on the bill (LM:1447-1455 selects the row whose
    linkid is sharedData.data.selectedLinkId, which PO:3291 sets to the bill's party or the last one used)."""
    asking_bill.choose_standard_party()
    asking_bill.party_input.click()
    expect(asking_bill.party_window).to_be_visible(timeout=20_000)

    selected_rows = asking_bill.party_window.locator(".ag-row-selected")

    expect(selected_rows.first).to_contain_text(standard_party(), ignore_case=True)


def test_party_window_loads_the_next_page_when_scrolled_to_the_end(asking_bill: ChecklistBill) -> None:
    """Row 9: LM:3523-3536 (handleScroll) asks for the next page when the list is scrolled to its end and
    fewer rows than the total are loaded, so the row count grows."""
    open_party_window(asking_bill)
    window = asking_bill.party_window
    counter = window.locator(GRID_ROW_COUNT).first
    expect(counter).to_be_visible()
    rows_before = int(counter.get_attribute("aria-rowcount") or 0)
    if rows_before < FULL_PAGE_ROWS:
        pytest.skip(f"row 9: the company has only {rows_before} parties, less than one page")

    window.locator(".ag-body-viewport").first.evaluate("el => { el.scrollTop = el.scrollHeight; }")

    window.page.wait_for_function(
        "([css, before]) => Number(document.querySelector(css)?.getAttribute('aria-rowcount')) > before",
        arg=[GRID_ROW_COUNT, rows_before],
    )


def test_party_search_lists_only_matching_parties_with_at_most_one_call_per_key(
    asking_bill: ChecklistBill,
) -> None:
    """Rows 10 and 38: typing in the party window filters the list on the server (LM:2263-2279
    externalFilterChanged calls getLedgerMasterList for a bill window), asking for page 1 only (LM:3656). The
    checklist says calls must be limited; the only limit the source implies is one call per typed character,
    which is what is asserted."""
    open_party_window(asking_bill)
    window = asking_bill.party_window
    term = standard_party()[:SEARCH_TEXT_LENGTH]
    search = window.get_by_role("searchbox")

    with logging_requests(asking_bill.page) as log:
        search.press("Control+A")
        search.press_sequentially(term, delay=KEY_DELAY_MS)
        names = window.locator(LEDGER_NAME_CELL)
        expect(names.first).to_contain_text(term, ignore_case=True)

    shown = [name.lower() for name in names.all_inner_texts() if name.strip()]
    assert all(term.lower() in name for name in shown[1:]), f"Parties not matching '{term}': {shown}"
    assert log.count_url_containing("ledger") <= SEARCH_TEXT_LENGTH
