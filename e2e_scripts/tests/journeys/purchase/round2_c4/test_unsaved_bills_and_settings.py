"""Purchase checklist rows 2, 15 and 40.

Row 2. A purchase line entered on a new bill is stored as a hold bill (`saveTransaction(true)` posts
`TempBillHold/Save`, transactionin.component.ts:6285-7454). Closing the bill deletes it
(afterCloseAlert, :8992),
so the bill is abandoned by reloading the page. Create/F2 then offers "Select Unsaved Bills"
(Unsavebill.component.html); closing that window deletes the listed bills
(Unsavebill.component.ts:115-122), which
is the clean-up. Hold bills of the last 3 days: the age limit is the API's and is not tested.
Row 15. With "Expiry Date Required?" = No (Expiry & MFG configure window) there is no expiry cell, so the
batch name is followed by the quantity at once.
Row 40. With "Mode of Payment" = Yes in the purchase bill setting, a purchase bill's save opens the "Mode Of
Payment" window (transactionin.component.ts:9773-9787, not for challan/order/return challan).
"""

import pytest
from playwright.sync_api import Page, expect

from pages.purchase.checklist.cell_focus import CellFocus
from pages.purchase.documents.bill_page import PurchaseBillEntryPage
from pages.purchase.documents.dates import timestamp_label
from pages.purchase.documents.drafts import PurchaseDraft
from pages.purchase.documents.line_items import STANDARD_ITEM_CODE
from pages.purchase.documents.seed_documents import SEED_PARTY, seed_draft
from pages.purchase.round2_c4.purchase_settings import EXPIRY_REQUIRED, MODE_OF_PAYMENT, PurchaseBillSettings
from pages.sale.documents.mode_of_payment import ModeOfPayment

pytestmark = [pytest.mark.p2, pytest.mark.journey("purchase-itc"), pytest.mark.xdist_group("chemist-tenant")]

UNSAVED_TITLE = "Select Unsaved Bills"
WINDOW_MS = 20_000
MAX_SAVE_PRESSES = 4
PAYMENT_LOOKUP_MS = 4_000


def test_a_bill_abandoned_with_a_line_is_offered_again_as_an_unsaved_bill(
    pharma_page: Page, new_bill: PurchaseBillEntryPage
) -> None:
    draft = seed_draft(timestamp_label())
    new_bill.fill_lines(draft)
    pharma_page.reload()
    bills = PurchaseBillEntryPage(pharma_page)

    bills.menu.open_purchase(bills.screen)
    bills.documents.create()

    window = pharma_page.locator("ngb-modal-window").filter(has_text=UNSAVED_TITLE)
    expect(window).to_be_visible(timeout=WINDOW_MS)
    expect(window.locator(".ag-center-cols-container .ag-row").first).to_be_visible()
    window.get_by_text("×").first.click()  # deletes the listed hold bills
    bills.discard()


def test_cursor_goes_from_the_batch_to_the_quantity_when_expiry_is_not_asked(
    pharma_page: Page, new_bill: PurchaseBillEntryPage
) -> None:
    settings = PurchaseBillSettings(pharma_page)
    with settings.held(EXPIRY_REQUIRED, "No"):
        new_bill.grid.select_product(0, STANDARD_ITEM_CODE)
        new_bill.grid.type_batch(0, timestamp_label())

        CellFocus(pharma_page).expect_on_quantity(0)


def test_purchase_bill_save_opens_mode_of_payment_when_the_setting_is_yes(
    pharma_page: Page, new_bill: PurchaseBillEntryPage
) -> None:
    draft: PurchaseDraft = seed_draft(timestamp_label())
    assert draft.party == SEED_PARTY
    settings = PurchaseBillSettings(pharma_page)
    with settings.held(MODE_OF_PAYMENT, "Yes"):
        new_bill.fill_lines(draft)
        payment = ModeOfPayment(pharma_page)
        for _ in range(MAX_SAVE_PRESSES):
            new_bill.press_save()
            if payment.is_open(PAYMENT_LOOKUP_MS):
                break

        payment.expect_open()
        pharma_page.keyboard.press("Escape")
