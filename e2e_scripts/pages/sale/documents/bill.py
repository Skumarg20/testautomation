"""Sale > Bill: create, delete, and delete or convert back when built from a challan."""

from playwright.sync_api import Locator, Page, expect

from pages.sale.documents.document import TemplatedDocument

SAVE_ATTEMPTS = 10
SUCCESS_TIMEOUT_MS = 50_000
CONFIRMATION_TIMEOUT_MS = 90_000
CHOICE_TIMEOUT_MS = 5_000
CHALLAN_MENU = ("Sale", "Challan")
# The focused editor still on the bill form, described for an error message; "" once focus has left
# every editable field or moved into a window the save opened (Mode Of Payment focuses #txt-amount-0).
FOCUSED_FORM_EDITOR = """() => {
    const el = document.activeElement;
    if (!el || el === document.body) return '';
    if (['button', 'a'].includes(el.tagName.toLowerCase())) return '';
    if (el.closest('ngb-modal-window')) return '';
    const box = el.getBoundingClientRect();
    const visible = box.width > 0 && box.height > 0 && box.top >= 0 && box.left >= 0
        && box.bottom <= window.innerHeight && box.right <= window.innerWidth;
    return visible ? el.tagName.toLowerCase() + (el.id ? '#' + el.id : '') : '';
}"""


class SaveNotStartedError(AssertionError):
    def __init__(self, focused: str) -> None:
        super().__init__(
            f"End did not start the save after {SAVE_ATTEMPTS} presses; focus stayed on {focused}"
        )


def press_end_until_saving(page: Page) -> None:
    """End saves, but only once focus has left every editable field; keep pressing until it has.

    It stops as soon as focus is in a window the save opened, so no End reaches Mode Of Payment.
    """
    focused = ""
    for _ in range(SAVE_ATTEMPTS):
        page.keyboard.press("End")
        focused = page.evaluate(FOCUSED_FORM_EDITOR)
        if not focused:
            return
    raise SaveNotStartedError(focused)


class SaleBillDocument(TemplatedDocument):
    menu = ("Sale", "Bill")
    number_label = "Bill No."

    def save(self) -> None:
        press_end_until_saving(self.page)

    def expect_saved(self) -> None:
        self.screen.wait_for_loader()
        self.confirm_save_window()
        self.screen.wait_for_loader()
        self.leave_to_list()

    def delete(self, number: str) -> None:
        self._start_delete(number)
        expect(self._bill_named(number)).to_be_visible(timeout=CONFIRMATION_TIMEOUT_MS)
        self.screen.confirm_if_asked()
        self.screen.expect_toast("success")

    def delete_with_challan(self, number: str) -> None:
        self._start_delete(number)
        self._expect_challan_choice()
        self.screen.press_button("Delete Bill & Challan")
        self.screen.confirm_if_asked()
        self.screen.expect_toast("success")

    def convert_back_to_challan(self, number: str, challan_number: str) -> None:
        self._start_delete(number)
        self._expect_challan_choice()
        self.screen.press_button("Re-Convert into Challan")
        self.screen.confirm_if_asked()
        self.screen.expect_toast("success", SUCCESS_TIMEOUT_MS)
        self.screen.wait_for_loader()
        self._expect_challan_listed(challan_number)

    def _start_delete(self, number: str) -> None:
        self.screen.open_menu(self.menu)
        self.screen.search_list(number)
        self.screen.row_action(number, "Delete")
        self.screen.wait_for_loader()

    def _expect_challan_choice(self) -> None:
        expect(self.page.locator("delete-load-challan-window")).to_be_visible(timeout=CHOICE_TIMEOUT_MS)

    def _expect_challan_listed(self, challan_number: str) -> None:
        self.screen.open_menu(CHALLAN_MENU)
        self.screen.filter_list_this_week()
        self.screen.search_list(challan_number)
        expect(self.screen.list_row(challan_number)).to_be_visible()

    def _bill_named(self, number: str) -> Locator:
        return self.page.locator("i", has_text=number)
