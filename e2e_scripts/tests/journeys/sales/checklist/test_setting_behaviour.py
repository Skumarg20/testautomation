"""Sale checklist rows 57, 61, 62, 63, 69, 72: what a Sale Bill Setting changes on a new bill.

Option codes come from the Angular source, not from the screen: Ask Party "0" Don't Ask / "1" Ask / "2"
Ask on Spacebar (`processout.transaction.component.ts` PO:2186, PO:3228); Ask Bill No. "2" Yes / "3" No
(PO:2205, PO:2244); Indicate if Item Repeated "0" Indicate / "1" Ask Forcefully / "2" No
(`itemmaster.component.ts:3172-3188`). Every setting is read first and put back (`setting_held`); nothing
is saved. A1 owns Ajay rows 197-199, 220-221 and 210-211; the tests here assert the cursor, which those do
not."""

from decimal import Decimal

import pytest
from playwright.sync_api import expect

from pages.sale.checklist.bill_screen import STANDARD_LINE, ChecklistBill
from pages.sale.checklist.focus import BILL_NUMBER, PARTY, SALE_TYPE, STORE, grid_column
from pages.sale.checklist.holds import held_or_skip
from pages.sale.checklist.sale_setting import (
    AMOUNT_CALCULATION,
    ASK_BILL_NO,
    ASK_NET_RATE,
    ASK_PARTY,
    ASK_SALE_TYPE,
    FREE_QUANTITY,
    ITEM_REPEATED,
    MR_REQUIRED,
    setting_held,
)
from pages.sale.documents.item_grid import FIRST_DISCOUNT

pytestmark = [
    pytest.mark.p1,
    pytest.mark.journey("sale-bill-creation"),
    pytest.mark.xdist_group("chemist-tenant"),
]

ASK = "1"
REPEATED_ITEM_TEXT = "Item already exists!"  # global.ts AlertMsg.itemRepeated
TEN_PERCENT = Decimal(10)


def test_ask_party_ask_opens_the_party_window(bill: ChecklistBill) -> None:
    """Row 57 (Ask): PO:2186 opens the party window when Ask Party in Retail Billing is not "0"."""
    with setting_held(bill, ASK_PARTY, "1"):
        bill.reopen()

        bill.press_enter_on_date()

        expect(bill.pick_list).to_be_visible(timeout=20_000)


def test_ask_party_dont_ask_takes_the_cash_party_without_a_window(bill: ChecklistBill) -> None:
    """Row 57 (Don't Ask): the cash party is filled in and no window opens (PO:2228 and askbillsetting
    PO:6009-6017 set the cash ledger, fixedID 26)."""
    with setting_held(bill, ASK_PARTY, "0"):
        bill.reopen()

        bill.press_enter_on_date()

        expect(bill.party_input).not_to_have_value("")
        expect(bill.pick_list).to_be_hidden()


def test_ask_party_on_spacebar_waits_on_the_party_until_space_is_pressed(bill: ChecklistBill) -> None:
    """Row 57 (Ask on Spacebar): the cursor rests on the party (PO:3228) and Space opens the window."""
    with setting_held(bill, ASK_PARTY, "2"):
        bill.reopen()
        bill.press_enter_on_date()
        bill.focus.expect_at(PARTY)
        expect(bill.pick_list).to_be_hidden()

        bill.page.keyboard.press("Space")

        expect(bill.pick_list).to_be_visible(timeout=20_000)


def test_ask_bill_no_yes_puts_the_cursor_on_the_bill_number_after_the_party(bill: ChecklistBill) -> None:
    """Row 62 (Yes): PO:2205 `askBillNo == "2"` focuses the bill number as soon as the party is chosen."""
    with setting_held(bill, ASK_PARTY, ASK), held_or_skip(bill, ASK_BILL_NO, "2"):
        bill.reopen()

        bill.choose_standard_party()

        bill.focus.expect_at(BILL_NUMBER)


def test_ask_bill_no_no_skips_the_bill_number_after_the_party(bill: ChecklistBill) -> None:
    """Row 62 (No): any other choice leaves the bill number out of the walk (PO:2205 tests only "2")."""
    with setting_held(bill, ASK_PARTY, ASK), held_or_skip(bill, ASK_BILL_NO, "3"):
        bill.reopen()

        bill.choose_standard_party()

        bill.page.wait_for_function("() => document.activeElement !== document.body")
        assert not bill.focus.is_at(BILL_NUMBER)


def test_ask_sale_type_yes_puts_the_cursor_on_the_sale_type(bill: ChecklistBill) -> None:
    """Rows 63: with Ask Sale Type at the time of Billing = Yes the walk after the party reaches the sale
    type field before the grid (PO:2236-2237 and PO:5992-5994 focus txtSaleType when
    isSaleTypeForBilling == 'T')."""
    with setting_held(bill, ASK_PARTY, ASK), held_or_skip(bill, ASK_SALE_TYPE, "T"):
        bill.reopen()
        if not bill.page.locator("[id^=txtSaleType]").first.is_visible():
            pytest.skip("row 63: the sale type field is not on this company's sale bill")

        bill.choose_standard_party()

        bill.focus.press_until("Enter", (SALE_TYPE, grid_column("itemLinkID")), limit=6)
        assert bill.focus.is_at(SALE_TYPE)


def test_store_field_is_a_stop_only_when_there_are_several_stores(bill: ChecklistBill) -> None:
    """Row 63 companion: the store stop exists only while isCursorWaitOnStore() (PO:5990); the field must not
    be listed on a single-store company."""
    with setting_held(bill, ASK_PARTY, ASK):
        bill.reopen()

        assert bill.store_input.count() <= 1
        if bill.store_input.count() == 0:
            pytest.skip("row 63: single-store company, no store stop to check")
        bill.choose_standard_party()
        bill.focus.press_until("Enter", (STORE, grid_column("itemLinkID")), limit=6)


@pytest.mark.parametrize(
    ("choice", "warns"),
    [("0", True), ("2", False)],
    ids=["indicate", "no-indication"],
)
def test_repeating_an_item_warns_only_when_the_setting_indicates(
    bill: ChecklistBill, choice: str, warns: bool
) -> None:
    """Row 69: choosing an item already in the bill shows "Item already exists!" with Indicate and
    nothing with No (`itemmaster.component.ts:3172-3188` setItemSelectionRules)."""
    with held_or_skip(bill, ITEM_REPEATED, choice):
        bill.reopen()
        bill.choose_standard_party()
        bill.add_standard_line(0)

        bill.document.grid.select_product(1, STANDARD_LINE.product)

        message = bill.page.get_by_text(REPEATED_ITEM_TEXT)
        if warns:
            expect(message.first).to_be_visible(timeout=10_000)
        else:
            expect(message).to_have_count(0)


def test_repeating_an_item_asks_for_a_decision_when_the_setting_is_ask_forcefully(
    bill: ChecklistBill,
) -> None:
    """Row 69 (Ask Forcefully): a window must answer the repeat (`checkItemRepetitionForceFully`,
    IM:3178-3181); its wording is not in the source, so only its presence is asserted."""
    with held_or_skip(bill, ITEM_REPEATED, "1"):
        bill.reopen()
        bill.choose_standard_party()
        bill.add_standard_line(0)

        bill.document.grid.select_product(1, STANDARD_LINE.product)

        expect(bill.page.locator("ngb-modal-window:not([aria-hidden='true'])").last).to_be_visible()


@pytest.mark.parametrize(
    ("label", "discounted"),
    [("Rate * Quantity", False), ("Rate * Quantity - Discount", True)],
    ids=["gross", "less-discount"],
)
def test_row_amount_follows_the_amount_calculation_setting(
    bill: ChecklistBill, label: str, discounted: bool
) -> None:
    """Row 61: with Amount Calculation On Billing = "Rate * Quantity" the line amount is rate x quantity; with
    "Rate * Quantity - Discount" a 10% item discount comes off (specs/manual-sale-gst-discount.md, Q on the
    grid Amount column). "Net Amount" is not asserted: its formula is not stated anywhere."""
    with held_or_skip(bill, AMOUNT_CALCULATION, label):
        bill.reopen()
        bill.choose_standard_party()
        grid = bill.document.grid
        grid.select_product(0, STANDARD_LINE.product)
        grid.choose_batch(0, STANDARD_LINE.batch)
        grid.enter_quantity(0, STANDARD_LINE.quantity)
        gross = grid.displayed_price(0) * STANDARD_LINE.quantity
        grid.enter_discount(0, FIRST_DISCOUNT, TEN_PERCENT)

        expected = gross - gross * TEN_PERCENT / 100 if discounted else gross

        assert grid.amount(0) == expected


def test_free_column_shows_only_when_free_quantity_is_required(bill: ChecklistBill) -> None:
    """Row 72: Free Quantity Required in Sale = Yes shows the Free column in the grid; No hides it (the grid
    drops `free` from allDisplayedColumns, multiunit.chemist.component.ts:595-598)."""
    free_header = bill.page.locator('.ag-header-cell[col-id="free"]')
    with held_or_skip(bill, FREE_QUANTITY, "true"):
        bill.reopen()
        shown = free_header.count() > 0
    with held_or_skip(bill, FREE_QUANTITY, "false"):
        bill.reopen()
        hidden = free_header.count() == 0

    assert shown, "Free column missing with Free Quantity Required = Yes"
    assert hidden, "Free column still shown with Free Quantity Required = No"


@pytest.mark.parametrize(("choice", "shown"), [("T", True), ("F", False)], ids=["mr-yes", "mr-no"])
def test_mr_field_is_on_the_bill_only_when_mr_is_required(
    bill: ChecklistBill, choice: str, shown: bool
) -> None:
    """Row 67: the MR field is drawn only when "MR required?" = Yes (`isMrRequired`, PO:1065-1073 sets it
    from MrfromSale == 'T'; the template draws txtmrname under *ngIf="isMrRequired"). The required-
    ness of the field is a separate setting (mrmandatoryinsale, PO:1531) and is not asserted here."""
    with held_or_skip(bill, MR_REQUIRED, choice):
        bill.reopen()

        mr_field = bill.page.locator("[id^=txtmrname]")

        if shown:
            expect(mr_field.first).to_be_visible()
        else:
            expect(mr_field).to_have_count(0)


@pytest.mark.parametrize(("choice", "box_shown"), [("1", True), ("No", False)], ids=["ask-always", "no"])
def test_net_rate_box_opens_on_the_rate_only_when_net_rate_is_asked(
    bill: ChecklistBill, choice: str, box_shown: bool
) -> None:
    """Row 64: with Ask Net Rate = "1" (ask always, `netrateask.component.ts:69`) the rate cell editor
    carries a net-rate box (`<controlId>-netRate`, template line 18); with No it does not. The "ask on
    * key" choice is not asserted: its option code and the key handling are not in the source read."""
    with held_or_skip(bill, ASK_NET_RATE, choice):
        bill.reopen()
        bill.choose_standard_party()
        grid = bill.document.grid
        grid.select_product(0, STANDARD_LINE.product)
        grid.choose_batch(0, STANDARD_LINE.batch)
        grid.enter_quantity(0, STANDARD_LINE.quantity)

        grid.cell(0, "salePurchaseRate").click()

        net_rate_box = bill.page.locator('input[id$="-netRate"]')
        if box_shown:
            expect(net_rate_box.first).to_be_visible()
        else:
            expect(net_rate_box).to_have_count(0)
