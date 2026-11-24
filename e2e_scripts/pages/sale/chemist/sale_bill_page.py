"""Actions on a saved sale bill: reopen it for modification, delete it, delete a grid row."""

from playwright.sync_api import Locator, expect

from pages.base_page import BasePage

LOAD_BILL_TIMEOUT_MS = 20_000


class SaleBillPage(BasePage):
    def expect_print_preview_shown(self) -> None:
        expect(self._print_preview_close).to_be_visible(timeout=LOAD_BILL_TIMEOUT_MS)

    def reopen_for_modification(self, entry_number: str) -> None:
        self._print_preview_close.click()
        self._open_saved_bill_search(entry_number)
        # Select the searched bill first: Enter opens whichever row has the focus.
        self._bill_row(entry_number).click()
        self.page.keyboard.press("Enter")
        self.page.wait_for_load_state("load")
        expect(self._entry_number).to_have_value(entry_number)
        self._modify_save_button.click()
        self.page.wait_for_load_state("load")

    def close_modification(self) -> None:
        self.page.wait_for_load_state("load")
        self._close_button.click()
        self._close_button.click()
        self._yes_button.click()
        self.page.wait_for_load_state("load")

    def delete_bill(self, entry_number: str) -> None:
        self._print_preview_close.click()
        self._open_saved_bill_search(entry_number)
        self._bill_row(entry_number).dblclick()
        expect(self._entry_number).to_have_value(entry_number)
        self.page.locator('[title="Delete"]').click()
        self._yes_button.click()
        self.page.wait_for_load_state("load")

    def delete_grid_row(self, position: int) -> None:
        confirmation = self.page.locator("div.modal-new.active")
        self.page.locator("[id^=Griddeletetbtn]").nth(position - 1).click()
        confirmation.wait_for(state="visible")
        self._yes_button.click()
        confirmation.wait_for(state="hidden")

    def _open_saved_bill_search(self, entry_number: str) -> None:
        self.page.evaluate("() => document.activeElement?.blur()")
        self.page.keyboard.press("Alt+M")
        self._yes_button.click()
        search = self.page.get_by_role("searchbox", name="Search", exact=True)
        search.click()
        search.press_sequentially(entry_number)
        expect(self._bill_row(entry_number)).to_be_visible(timeout=LOAD_BILL_TIMEOUT_MS)

    def _bill_row(self, entry_number: str) -> Locator:
        entry_cell = self.page.locator(f'[col-id="entryNo"] span:text-is("{entry_number}")')
        return self.page.get_by_role("row").filter(has=entry_cell)

    @property
    def _print_preview_close(self) -> Locator:
        return self.page.locator("#btn-Close")

    @property
    def _entry_number(self) -> Locator:
        return self.page.locator('input[formcontrolname="entryNo"]')

    @property
    def _modify_save_button(self) -> Locator:
        return self.page.locator("button.blue-btn.btn").first

    @property
    def _close_button(self) -> Locator:
        return self.page.locator("#btnEsc1")

    @property
    def _yes_button(self) -> Locator:
        return self.page.locator("#btnYes")
