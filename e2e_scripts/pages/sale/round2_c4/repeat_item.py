"""Picking an item that is already on the sale bill, and the "Item Repeated" question the app may ask.

Rule, from the item window (`itemmaster.component.ts`, `setItemSelectionRules` :3169-3203) which the sale bill
opens for every product cell with the bill's own rows as `itemListForDuplicate`
(componentPlaceHolder.template.ts:266). The Sale Bill Setting "Indicate if Item Repeated in Bill"
(`IndicateIfItemRepeatedInBill`, salebill.setting.html:611-625) has three values:
- "0" Indicate: the window warns "Item already exists!" (global.ts:19021) and still returns the item;
- "1" Follow Strictly (the code calls it "Ask Forcefully"): the window opens the "Item Repeated" question
  (`ItemRepeatComponent`, itemrepeatask.component.html) saying "This item is already added on Row No. <n>."
  with Yes and No; Yes returns the item, No warns "Repeated item is not allowed. Kindly choose another item!"
  (global.ts:19022) and returns nothing (:3205-3232);
- "2" No: the item is returned without any message.
The rule looks at the item only, never at the batch, so the same batch twice is the same case.
"""

from decimal import Decimal

from playwright.sync_api import Locator, expect

from pages.accounting.waiting import appears_within
from pages.base_page import BasePage
from pages.sale.documents.item_grid import PRODUCT
from pages.sale.manual.pharma_bill import BATCH, ITEM, PharmaBill
from pages.stock.search_typing import type_search

INDICATE = "Indicate"
FOLLOW_STRICTLY = "Follow Strictly"
NOT_INDICATED = "No"
ITEM_ALREADY_EXISTS = "Item already exists!"
REPEATED_ITEM_REFUSED = "Repeated item is not allowed. Kindly choose another item!"
QUESTION_TITLE = "Item Repeated"
CELL_WAIT_MS = 1_000
QUESTION_TIMEOUT_MS = 15_000
LIST_TIMEOUT_MS = 90_000


class RepeatedItemBill(BasePage):
    """One sale bill (`PharmaBill`) on which the same item is picked again."""

    def __init__(self, bill: PharmaBill) -> None:
        super().__init__(bill.page)
        self._bill = bill

    def pick_item_again(self, row: int) -> None:
        """Opens the item window on `row`, finds the item by its code and clicks it; does not wait for the
        window to close, because with "Follow Strictly" it stays open behind the question."""
        cell = self._bill.document.grid.cell(row, PRODUCT)
        editor = cell.locator("input")
        if appears_within(editor, CELL_WAIT_MS):
            editor.press("Enter")
        else:
            cell.click()
        if not appears_within(self._window, CELL_WAIT_MS):
            editor.press("Space")
        expect(self._window).to_be_visible(timeout=QUESTION_TIMEOUT_MS)
        self._window.get_by_role("combobox").first.select_option("Itemcode")
        type_search(self._window.get_by_role("searchbox"), ITEM)
        listed = self.page.locator('[col-id="itemcode"]').filter(has_text=ITEM)
        expect(listed.first).to_be_visible(timeout=LIST_TIMEOUT_MS)
        listed.first.click()

    def complete_line(self, row: int, quantity: Decimal) -> None:
        """After the item was accepted: its batch and quantity, as the first row got them."""
        self._bill.document.grid.choose_batch(row, BATCH)
        self._bill.document.grid.enter_quantity(row, quantity)

    def expect_asked_about_row(self, number: int) -> None:
        expect(self._question).to_contain_text(f"Row No. {number}", timeout=QUESTION_TIMEOUT_MS)

    def answer_yes(self) -> None:
        self._question.get_by_role("button", name="Yes").click()
        expect(self._question).to_be_hidden(timeout=QUESTION_TIMEOUT_MS)

    def answer_no(self) -> None:
        self._question.get_by_role("button", name="No").click()
        expect(self._question).to_be_hidden(timeout=QUESTION_TIMEOUT_MS)

    def close_item_window(self) -> None:
        """The window stays open after a refused pick; its cross closes it."""
        self._window.get_by_text("×").first.click()
        expect(self._window).to_be_hidden(timeout=QUESTION_TIMEOUT_MS)

    @property
    def _question(self) -> Locator:
        # Why CSS: the question is a bare ng-bootstrap modal whose card is `div.modal-new.active`
        # (the class `ConfirmDialog` also relies on in DocumentScreen.active_dialog).
        return self.page.locator("div.modal-new.active").filter(has_text=QUESTION_TITLE)

    @property
    def _window(self) -> Locator:
        # Why CSS: the item window is a Bootstrap modal with no role or test id (SelectionWindow._window).
        return self.page.locator("div.modal-dialog.modal-lg")
