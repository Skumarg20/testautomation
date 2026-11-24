"""A sale document (order, challan, bill or return): the steps all of them share."""

from abc import ABC, abstractmethod
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from playwright.sync_api import Locator, Page, expect

from pages.base_page import BasePage
from pages.sale.documents.document_requests import DocumentRequest, ProductLine, plain
from pages.sale.documents.header import DocumentHeader
from pages.sale.documents.invoice_totals import InvoiceTotals
from pages.sale.documents.item_grid import (
    FIRST_DISCOUNT,
    FIRST_VOLUME_DISCOUNT,
    SECOND_DISCOUNT,
    SECOND_VOLUME_DISCOUNT,
    DocumentItemGrid,
)
from pages.sale.documents.pending_windows import NO_TEMPLATES, PendingWindows, Templates
from pages.sale.documents.screen import DocumentScreen, is_shown_within
from pages.sale.documents.selection_window import SelectionWindow

WARNING_WAIT_MS = 500
SAVE_WINDOW_TIMEOUT_MS = 20_000
WHOLE_UNITS = Decimal(1)
PREFERENCES_WINDOW_WAIT_MS = 2_000
UNSAVED_PROMPT_WAIT_MS = 1_000
ITEM_DETAILS_WAIT_MS = 2_000


class AmountMismatchError(AssertionError):
    def __init__(self, expected: Decimal, actual: Decimal) -> None:
        super().__init__(f"Amount mismatched: expected {expected}, but got {actual}")


class SaleDocument(BasePage, ABC):
    menu: tuple[str, ...]
    number_label: str

    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self.screen = DocumentScreen(page)
        self.header = DocumentHeader(page)
        self.grid = DocumentItemGrid(page)
        self.pending = PendingWindows(page)
        self.selection = SelectionWindow(page)
        self._totals = InvoiceTotals(page)

    def open_new(self) -> None:
        self.screen.open_menu(self.menu)
        self.screen.press_button("Create/F2")
        self.screen.wait_for_loader()
        self._accept_transaction_preferences()

    def choose_party(self, name: str) -> None:
        self.choose_party_from(name, NO_TEMPLATES)

    def choose_party_from(self, name: str, templates: Templates) -> None:
        self.pending.resolve(NO_TEMPLATES)
        self.header.choose_party(name)
        self.screen.wait_for_loader()
        self.pending.resolve(templates)
        self._dismiss_unsaved_prompt()

    def enter_date(self, day: date) -> None:
        self.header.enter_date(day)

    def expect_date_rejected(self) -> None:
        """A date other than today is refused with a warning once the grid is touched."""
        warning = self.page.locator("notifier-notification.notifier__notification--warning").first
        self.grid.open_first_product_cell()
        if not is_shown_within(warning, WARNING_WAIT_MS):
            self.grid.open_first_product_cell()
        self.screen.expect_toast("warning")

    def enter_people(self, request: DocumentRequest) -> None:
        self.header.choose_patient(request.patient)
        self.header.fill_address(request.address)
        self.header.choose_doctor(request.doctor)

    def add_line(self, row: int, line: ProductLine) -> None:
        self.grid.select_product(row, line.product)
        self.choose_batch(row, line)
        self.grid.enter_quantity(row, line.quantity)
        if not line.has_sellable_quantity:
            self.screen.expect_toast("warning")
            return
        self.enter_price(row, line)
        self._enter_discounts(row, line)
        self._verify_row_total(row, line)

    def choose_batch(self, row: int, line: ProductLine) -> None:
        self.grid.choose_batch(row, line.batch)

    def enter_price(self, row: int, line: ProductLine) -> None:
        floor = self._price_floor(row)
        self.grid.type_price(row, line.price)
        if not line.price or line.price < floor:
            self._accept_low_price(row)
        else:
            self.grid.finish_price(row)
            self._verify_price_entry(row, line)

    def enter_bill_discount(self, amount: Decimal) -> None:
        self.close_item_details()
        field = self.header.field("Bill Discount")
        field.click()
        field.press_sequentially(plain(amount))
        field.press("Enter")
        self.screen.wait_for_loader()

    def verify_invoice_total(self, *, has_lines: bool) -> None:
        self._totals.expect_consistent(has_lines=has_lines)

    def document_number(self) -> str:
        return self.header.number(self.number_label)

    def save(self) -> None:
        self.page.keyboard.press("End")
        if self.header.field("Bill Discount").evaluate("el => el === document.activeElement"):
            self.page.keyboard.press("End")

    def expect_rejected(self) -> None:
        self.screen.expect_toast("warning")
        self.leave_to_list()

    @abstractmethod
    def expect_saved(self) -> None: ...

    def delete(self, number: str) -> None:
        self.screen.open_menu(self.menu)
        self.screen.delete_listed_record(number)

    def confirm_save_window(self) -> None:
        window = self.save_window
        expect(window).to_be_visible(timeout=SAVE_WINDOW_TIMEOUT_MS)
        window.get_by_role("button", name="save").click()

    @property
    def save_window(self) -> Locator:
        return self.page.locator(".frameModal")

    def leave_to_list(self) -> None:
        self.screen.close_print_window_if_shown()
        self.screen.confirm_if_asked()
        if self.selection.is_shown():
            self.selection.close()
        self.pending.close_all()
        self.screen.confirm_if_asked()

    def _price_floor(self, row: int) -> Decimal:
        return self.grid.displayed_price(row)

    def _accept_low_price(self, row: int) -> None:
        self.grid.confirm_low_price(row)
        expect(self.screen.active_dialog).to_be_visible()
        self.screen.confirm_yes()

    def _verify_price_entry(self, row: int, line: ProductLine) -> None:
        amount = self.grid.amount(row)
        if amount > 0:
            grid_quantity = self.grid.quantity_in_grid(row)
            quantity = grid_quantity if grid_quantity > 0 else line.quantity
            expect_amount_to_round_to(amount, quantity * line.price)

    def _verify_row_total(self, row: int, line: ProductLine) -> None:
        """Hook: documents that check the row amount against quantity x price override this."""

    def _enter_discounts(self, row: int, line: ProductLine) -> None:
        discounts = (
            (FIRST_DISCOUNT, line.discount1),
            (SECOND_DISCOUNT, line.discount2),
            (FIRST_VOLUME_DISCOUNT, line.volume_discount1),
            (SECOND_VOLUME_DISCOUNT, line.volume_discount2),
        )
        for column, value in discounts:
            self.grid.enter_discount(row, column, value)

    def _accept_transaction_preferences(self) -> None:
        self._dismiss_unsaved_prompt()
        if is_shown_within(self.save_window, PREFERENCES_WINDOW_WAIT_MS):
            self.screen.press_button("save")
            self.screen.wait_for_loader()
        self._dismiss_unsaved_prompt()

    def _dismiss_unsaved_prompt(self) -> None:
        prompt = self.page.locator("ngb-modal-window:not([aria-hidden='true']) unsave-bill .modal-header")
        if is_shown_within(prompt, UNSAVED_PROMPT_WAIT_MS):
            prompt.get_by_text("×").click()

    def close_item_details(self) -> None:
        popup = self.page.locator("div.dragPopuppp").filter(has=self.page.locator("item-details"))
        if is_shown_within(popup, ITEM_DETAILS_WAIT_MS):
            popup.get_by_text("×").click()


def expect_amount_to_round_to(actual: Decimal, expected: Decimal) -> None:
    """Whole-unit comparison, as the source did, so paise from tax rounding do not fail it."""
    if actual.quantize(WHOLE_UNITS, ROUND_HALF_UP) != expected.quantize(WHOLE_UNITS, ROUND_HALF_UP):
        raise AmountMismatchError(expected, actual)


def expect_amount_equals(actual: Decimal, expected: Decimal) -> None:
    if actual != expected:
        raise AmountMismatchError(expected, actual)


class TemplatedDocument(SaleDocument, ABC):
    """Challans and bills can be built from earlier documents; their pop-up windows get in the way."""

    def enter_people(self, request: DocumentRequest) -> None:
        self.pending.close_all()
        self.header.choose_patient(request.patient)
        self.pending.close_all()
        self.header.fill_address(request.address)
        self.pending.close_all()
        self.header.choose_doctor(request.doctor)
        self.page.locator("body").click()
