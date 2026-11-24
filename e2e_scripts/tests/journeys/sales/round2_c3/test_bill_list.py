"""Sale checklist rows 28 (save as draft) and 50 to 54 (the sale bill list), on bills the test saves itself.

Draft (row 28): the 'Save as draft' button (`[id^=btnDraft]`) exists while the Control Room option "Sale Bill
Draft Required" (field 4438, ControlRoomDesignData.cs:1370) is Yes (`SalebilldraftStartEnd == 'T'`,
processout html:1202). `saveToDraft` (processout:10382) saves with `draft = 1`, answers "Bill saved in draft
sucessfully" (:12005) and clears the bill; the bill is then in Sale > Draft and not in Sale > Bill. The draft
is deleted at the end of the test.

List (rows 50 to 54), `processout.list.component.html`: Custom range with Apply (:160-185); with a bill
selected, Print, Email, Whatsapp and Export appear (:33-86); each row has a menu with Delete and Logs.
Bills are saved to the owned customer and deleted by the `customer_bills` fixture.
"""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from playwright.sync_api import expect

from pages.sale.round2_c3.bill_list import MENU_ITEMS, SaleBillList, SaleDrafts
from pages.sale.round2_c3.control_room_choice import Choice
from pages.sale.round2_c3.owned_stock import BatchSpec, StockSpec
from pages.sale.round2_c3.sale_desk import SaleDesk
from pages.sale.round2_c3.stock_bill import StockLine

pytestmark = [
    pytest.mark.p2,
    pytest.mark.journey("sale-bill-creation"),
    pytest.mark.xdist_group("chemist-tenant"),
]

DRAFT_SETTING = "Sale Bill Draft Required"
DRAFT_SAVED = "Bill saved in draft sucessfully"  # processout.transaction.component.ts:12005 (sic)
ONE_BATCH = StockSpec(batches=(BatchSpec(Decimal(180), Decimal(120)),))


def save_one_bill(desk: SaleDesk) -> str:
    item = desk.make_stock(ONE_BATCH)
    desk.sell(StockLine(item, item.batch_names[0], Decimal(1)))
    return desk.bills.save(desk.bill.bill.save_and_confirm)


def test_saved_as_draft_is_in_the_draft_list_and_not_in_the_bill_list(desk: SaleDesk) -> None:
    """Row 28: Save as draft shows the draft toast; the customer has a draft and no bill."""
    desk.hold_choice(Choice(DRAFT_SETTING, "Yes"))
    item = desk.make_stock(ONE_BATCH)
    desk.sell(StockLine(item, item.batch_names[0], Decimal(1)))
    page = desk.bill.bill.page
    try:
        page.locator("[id^=btnDraft]").locator("visible=true").first.click()
        expect(page.get_by_text(DRAFT_SAVED).first).to_be_visible()
        desk.bill.bill.leave_without_saving()

        drafts = SaleDrafts(page)
        drafts.open()
        drafts.expect_listed(desk.customer)
        SaleBillList(page).open()
        SaleBillList(page).screen.search_list(desk.customer)
        expect(page.get_by_role("row").filter(has=page.get_by_text(desk.customer, exact=True))).to_have_count(
            0
        )
    finally:
        SaleDrafts(page).delete(desk.customer)


def test_custom_range_keeps_a_bill_only_inside_the_range(desk: SaleDesk) -> None:
    """Row 50: a bill saved today is listed for a range ending today and gone for a range ending yesterday."""
    number = save_one_bill(desk)
    page = desk.bill.bill.page
    listing = SaleBillList(page)
    listing.open()
    today = date.today()

    listing.apply_custom_range(today - timedelta(days=1), today)
    expect(listing.find(number)).to_be_visible()
    listing.apply_custom_range(today - timedelta(days=5), today - timedelta(days=1))
    listing.screen.search_list(number)

    expect(page.get_by_role("row").filter(has=page.get_by_text(number, exact=True))).to_have_count(0)


def test_selected_bill_offers_print_email_whatsapp_and_export(desk: SaleDesk) -> None:
    """Rows 51 and 54: ticking one bill shows the Print, Email, Whatsapp and Export controls."""
    number = save_one_bill(desk)
    listing = SaleBillList(desk.bill.bill.page)
    listing.open()

    listing.select(number)

    for name in ("Print", "Email", "Whatsapp"):
        expect(listing.button(name).first).to_be_visible()
    expect(listing.page.get_by_text("Export", exact=True).first).to_be_visible()


def test_export_of_the_selected_bill_downloads_a_file(desk: SaleDesk) -> None:
    """Row 51 (export): the first Export format produces a file; it is read nowhere and kept in the
    browser's temporary folder."""
    number = save_one_bill(desk)
    listing = SaleBillList(desk.bill.bill.page)
    listing.open()
    listing.select(number)

    download = listing.export_first_format()

    assert download.suggested_filename


def test_row_menu_offers_delete_and_logs_and_edit_opens_the_bill(desk: SaleDesk) -> None:
    """Row 54: the row menu of an own bill lists Delete and Logs; the edit button opens that bill."""
    number = save_one_bill(desk)
    page = desk.bill.bill.page
    listing = SaleBillList(page)
    listing.open()

    menu = listing.open_row_menu(number)
    for entry in MENU_ITEMS:
        expect(menu.get_by_text(entry).first).to_be_visible()
    page.keyboard.press("Escape")
    desk.bill.bill.reopen(number)

    assert desk.bill.bill.is_open()
    desk.bill.bill.leave_without_saving()


def test_bulk_action_window_opens_for_the_owned_bills(desk: SaleDesk) -> None:
    """Row 53: with a saved bill in the list, Bulk Action > Invoice Bulk Download opens its window. The
    download over ticked bills is the same server file as the Export test above."""
    save_one_bill(desk)
    page = desk.bill.bill.page
    SaleBillList(page).open()
    bulk = page.get_by_role("button", name="Bulk Action")
    expect(bulk).to_be_visible()

    bulk.click()
    page.get_by_role("link", name="Invoice Bulk Download").click()

    expect(page.locator("ngb-modal-window:not([aria-hidden='true'])").last).to_be_visible()
    page.keyboard.press("Escape")
