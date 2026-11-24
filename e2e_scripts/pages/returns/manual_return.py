"""Purchase > Return, items picked by hand by product name, for items that have no batches.

The shared `PurchaseReturnPage.create` picks products by item code ("3"); the QA company has no item
codes any more (seen live 2026-10-08), so this page picks the product by its name in "Select Item".
"""

import re
from dataclasses import dataclass
from decimal import Decimal

from playwright.sync_api import expect

from pages.accounting.waiting import appears_within
from pages.dashboard_page import DashboardPage
from pages.inventory.item_alert import ItemAlert
from pages.purchase.documents.dates import todays_serial
from pages.purchase.documents.drafts import PurchaseDraft, ReturnMode
from pages.returns.party_picker import PurchaseReturnScreen
from pages.returns.return_list import PurchaseReturnList
from pages.stock.item_picker import StockItemPicker

PICKER_LOOKUP_MS = 1_500
PAYMENT_TIMEOUT_MS = 20_000
PAYMENT_WINDOW = "Mode Of Payment"
ALREADY_EXISTS = "Already Exists"
REFUSAL_MS = 4_000
SAVE_BUTTON = re.compile(r"^\s*save\s*$", re.IGNORECASE)


@dataclass(frozen=True)
class ManualReturn:
    party: str
    product: str
    quantity: Decimal
    rate: Decimal

    @property
    def value(self) -> Decimal:
        """The sum of the returned line: quantity times rate (no discount is entered)."""
        return self.quantity * self.rate


class ManualPurchaseReturn(PurchaseReturnScreen):
    refused_proposal: str | None = None  # the number the app proposed and then refused as already used

    def create_manual(self, goods: ManualReturn, number: str) -> str:
        """Enters and saves the return dated today under `number`; returns that "Dr. Note" number.

        The number is typed because the app proposes "DN00001" again and refuses it with "Bill No. Already
        Exists!" (probe 2026-10-15), so the proposed number cannot be relied on."""
        draft = PurchaseDraft(party=goods.party, entry_date=todays_serial(), return_mode=ReturnMode.MANUAL)
        self.begin(draft)
        self.enter_entry_date(draft.entry_date)
        self._pick_product(goods.product)
        self.grid.enter_quantity(0, goods.quantity)
        self.grid.enter_rate(0, goods.rate)
        proposed = self._number_field.input_value()
        self._save_with_end_keys()
        if appears_within(
            self.page.locator("notifier-notification").filter(has_text=ALREADY_EXISTS), REFUSAL_MS
        ):
            self.refused_proposal = proposed
            self._number_field.fill(number)
            self._number_field.press("Tab")
            self._save_with_end_keys()
            return number
        return proposed

    def _save_with_end_keys(self) -> None:
        # Why keys: this screen's Save button is named "F10 / End Save", so the shared `save` (which clicks
        # "End Save") finds nothing; the first End moves to the bill value and the second opens
        # "Mode Of Payment" (probe 2026-10-15).
        self.page.keyboard.press("End")
        self.page.keyboard.press("End")
        self._save_payment_window()

    def proposed_number(self, party: str) -> str:
        """Starts a new manual return for the party and reads the Dr. Note number the app proposes."""
        draft = PurchaseDraft(party=party, entry_date=todays_serial(), return_mode=ReturnMode.MANUAL)
        # After a save the sidebar is half-collapsed; a fresh dashboard makes the menu clickable again.
        DashboardPage(self.page).open()
        self.begin(draft)
        return self._number_field.input_value()

    def delete_from_list(self, number: str) -> None:
        """Deletes the return from today's list and waits until the list no longer shows it.

        The row menu items are anchors without href (no link role), and the confirmation buttons carry
        aria-label "Close", so the shared `DocumentList.delete` cannot drive this list.
        """
        listing = PurchaseReturnList(self.page)
        listing.find(number)
        listing.open_row_menu(number)
        # Why CSS: the open Bootstrap menu has no role; its items are plain anchors.
        self.page.locator(".dropdown-menu.show").get_by_text("Delete", exact=True).click()
        ItemAlert(self.page).question.locator("#btnYes").click()
        self.feedback.wait_for_loader()
        listing.find(number)
        listing.expect_not_listed(number)

    def _confirm_save_prompt(self) -> None:
        """Nothing to do: `_save_with_end_keys` has already saved the payment window."""

    def _save_payment_window(self) -> None:
        """Saves the "Mode Of Payment" window that the second End opens (seen live 2026-10-08)."""
        self.feedback.wait_for_loader()
        # Why CSS: the window is an ngb modal; older modals stay in the DOM, so the newest is used.
        payment = self.page.locator("ngb-modal-window").filter(has_text=PAYMENT_WINDOW).last
        expect(payment).to_be_visible(timeout=PAYMENT_TIMEOUT_MS)
        payment.get_by_role("button", name=SAVE_BUTTON).click()

    def _pick_product(self, product: str) -> None:
        self.grid.click_product_cell(0)
        picker = StockItemPicker(self.page)
        if not picker.opens_within(PICKER_LOOKUP_MS):
            self.page.keyboard.press("Enter")
        picker.choose(product)
