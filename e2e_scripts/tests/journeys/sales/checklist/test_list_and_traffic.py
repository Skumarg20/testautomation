"""Sale checklist rows 43, 50, 53, 54: the sale bill list screen, and the calls a new bill makes.

List component: `processout.list.component.ts` / `.html` (PL). Nothing is created, changed or downloaded:
menus are opened and closed again."""

import pytest
from playwright.sync_api import expect

from pages.sale.checklist.bill_screen import ChecklistBill
from pages.sale.checklist.request_log import logging_requests
from pages.sale.documents.bill import SaleBillDocument
from pages.sale.documents.screen import DocumentScreen

pytestmark = [
    pytest.mark.p2,
    pytest.mark.journey("sale-bill-creation"),
    pytest.mark.xdist_group("chemist-tenant"),
]

LIST_TIMEOUT_MS = 30_000


@pytest.fixture
def bill_list(screen: ChecklistBill) -> DocumentScreen:
    """The Sale > Bill list (no new bill opened)."""
    list_screen = DocumentScreen(screen.page)
    list_screen.open_menu(SaleBillDocument.menu)
    list_screen.wait_for_loader()
    return list_screen


def test_row_action_menu_offers_delete(bill_list: DocumentScreen) -> None:
    """Row 54: each listed bill has an action menu that includes Delete (the link the delete flow of
    `SaleBillDocument` already uses). Only the menu is opened."""
    first_row = bill_list.page.locator(".ag-row").filter(
        has=bill_list.page.locator('button[data-toggle="dropdown"]')
    )
    if first_row.count() == 0:
        pytest.skip("row 54: the sale bill list has no bill to open an action menu on")

    first_row.first.locator('button[data-toggle="dropdown"]').click()

    expect(bill_list.page.get_by_role("link", name="Delete").first).to_be_visible(timeout=LIST_TIMEOUT_MS)


def test_bulk_action_offers_invoice_bulk_download(bill_list: DocumentScreen) -> None:
    """Row 53: the Bulk Action button (shown to the super admin or when profile field 83 allows,
    PL:317-325) lists "Invoice Bulk Download", which opens the bulk-download window (PL:2771-2773).
    Nothing is downloaded."""
    bulk = bill_list.page.get_by_role("button", name="Bulk Action")
    if bulk.count() == 0:
        pytest.skip("row 53: this user is not allowed the Bulk Action button (profile field 83)")

    bulk.click()
    bill_list.page.get_by_role("link", name="Invoice Bulk Download").click()

    expect(bill_list.page.locator("ngb-modal-window:not([aria-hidden='true'])").last).to_be_visible()
    bill_list.page.keyboard.press("Escape")


def test_list_filter_offers_a_custom_date_range_with_apply(bill_list: DocumentScreen) -> None:
    """Row 50: the filter menu has a Custom range with an Apply button (PL template, CustomDate())."""
    bill_list.page.locator("button.default-btn.dropdown-toggle").click()

    bill_list.page.get_by_text("Custom", exact=True).click()

    expect(bill_list.page.get_by_role("button", name="Apply")).to_be_visible()


def test_opening_a_bill_and_choosing_a_party_repeats_no_api_call(screen: ChecklistBill) -> None:
    """Row 43: while a new bill opens and its party is chosen, no API call (same method, address and body) is
    sent twice. The checklist gives no allowed count, so the strict reading "never twice" is asserted."""
    with logging_requests(screen.page) as log:
        screen.open_new()
        screen.choose_standard_party()

    assert log.repeated_calls() == {}
