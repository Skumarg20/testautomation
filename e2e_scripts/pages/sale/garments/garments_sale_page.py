"""The garments sale bill window (Alt+N): party, then per line barcode, item, variant, quantity."""

import re
from decimal import Decimal

from playwright.sync_api import Locator, expect
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from pages.accounting.waiting import appears_within
from pages.base_page import BasePage
from pages.components.bill_totals import amount_pattern
from pages.components.shortcut import press_until_visible
from pages.grid.ag_grid import AgGrid
from test_data.money import parse_amount

OPEN_SHORTCUT = "Alt+N"
COMMIT_SHORTCUT = "F10"
SERIES_DIALOG_TITLE = "Select Series"
DEFAULT_SERIES = "Default"
SCREEN_TIMEOUT_MS = 30_000
STEP_TIMEOUT_MS = 15_000
PICK_ATTEMPTS = 3
PICK_ATTEMPT_TIMEOUT_MS = 10_000
PRODUCT = "itemLinkID"
RATE = "salePurchaseRate"
AMOUNT = "DisplayAmount"
DISCOUNT1 = "discount1"
PICKER_PRODUCT = "Product"
PARTY_PICKER_TITLE = "Select Party"
PARTY_KEY_DELAY_MS = 80
FIRST_CELL_SETTLE_MS = 5_000
# The variant (Design / Color / Size) window; only it has a balance quantity column.
VARIANT_BALANCE = "balanceQty"
# Unsavebill.component (careportal:309424): lists the bills a refresh or crash left unsaved.
UNSAVED_BILLS_TITLE = "Select Unsaved Bills"


class GarmentsSalePage(BasePage):
    def open_new_bill(self) -> None:
        series_dialog = self.page.get_by_text(SERIES_DIALOG_TITLE)
        press_until_visible(self.page, OPEN_SHORTCUT, series_dialog.or_(self._party))
        if series_dialog.is_visible():
            self.page.get_by_role("gridcell", name=DEFAULT_SERIES, exact=True).click()
            self.page.keyboard.press("Enter")
            expect(self._party).to_be_visible(timeout=SCREEN_TIMEOUT_MS)

    def choose_party(self, name: str) -> None:
        """The party is a plain textbox (since 2026-10-09); typing opens the "Select Party" window."""
        self._party.click()
        self._party.press_sequentially(name, delay=PARTY_KEY_DELAY_MS)
        picker = self.page.get_by_role("dialog").filter(has_text=PARTY_PICKER_TITLE)
        picker.get_by_role("gridcell", name=name, exact=True).click()
        self._reach_first_barcode_cell()

    def add_item(self, row: int, item_name: str, quantity: Decimal) -> None:
        self._open_item_picker(row)
        self._pick_highlighted_item(item_name)
        self._confirm_variant()
        self._commit_quantity(quantity)
        expect(self._barcode_cell(row + 1)).to_be_visible(timeout=STEP_TIMEOUT_MS)

    def change_rate(self, row: int, rate: Decimal) -> None:
        cell = self._grid.cell(row, RATE)
        cell.dblclick()
        editor = cell.locator("input")
        editor.press("Control+A")
        editor.press_sequentially(str(rate))
        editor.press("Enter")

    def change_item_discount(self, row: int, percent: Decimal) -> None:
        self._grid.cell(row, DISCOUNT1).click()
        self.page.keyboard.insert_text(str(percent))
        self.page.keyboard.press("Enter")

    def line_amount(self, row: int) -> Decimal:
        cell = self._grid.cell(row, AMOUNT)
        expect(cell).to_have_text(self._any_digit(), timeout=STEP_TIMEOUT_MS)
        return parse_amount(cell.inner_text())

    def expect_line_amount(self, row: int, expected: Decimal) -> None:
        cell = self._grid.cell(row, AMOUNT)
        expect(cell).to_have_text(re.compile(rf"^\s*{amount_pattern(expected)}\s*$"), timeout=STEP_TIMEOUT_MS)

    def enter_barcode(self, row: int, barcode: str) -> None:
        cell = self._barcode_cell(row)
        cell.click()
        cell.press_sequentially(barcode)
        cell.press("Enter")

    def expect_alert(self, message: str) -> None:
        expect(self.page.get_by_text(message)).to_be_visible(timeout=STEP_TIMEOUT_MS)

    def dismiss_alert(self) -> None:
        alert = self.page.get_by_role("dialog").filter(has_text="Alert!")
        alert.get_by_role("button", name="Close", exact=True).click()
        expect(alert).to_be_hidden(timeout=STEP_TIMEOUT_MS)

    def refresh(self) -> None:
        """Reloads the browser tab mid-bill; a "leave site?" prompt, if one is raised, is accepted."""
        self.page.once("dialog", lambda dialog: dialog.accept())
        self.page.reload()

    def expect_unsaved_bill_offered(self, party: str) -> None:
        """After a refresh, a new bill first lists the bills left unsaved, by party."""
        press_until_visible(self.page, OPEN_SHORTCUT, self._unsaved_bills_window)
        party_cell = self._unsaved_bills_window.get_by_role("gridcell", name=party, exact=True)
        expect(party_cell.first).to_be_visible(timeout=STEP_TIMEOUT_MS)

    def discard_unsaved_bills(self) -> None:
        """Closing the window deletes the bills not chosen (careportal:309424); a new bill is left open."""
        self.page.keyboard.press("Escape")
        expect(self._unsaved_bills_window).to_be_hidden(timeout=STEP_TIMEOUT_MS)
        self.open_new_bill()

    @property
    def _unsaved_bills_window(self) -> Locator:
        return self.page.get_by_role("dialog").filter(has_text=UNSAVED_BILLS_TITLE)

    def _open_item_picker(self, row: int) -> None:
        cell = self._barcode_cell(row)
        cell.click()
        cell.press("Enter")
        expect(self._item_search).to_be_visible(timeout=STEP_TIMEOUT_MS)

    def _pick_highlighted_item(self, item_name: str) -> None:
        self._item_search.press_sequentially(item_name)
        expect(self._highlighted_item(item_name)).to_be_visible(timeout=STEP_TIMEOUT_MS)
        self._press_enter_until_variants_listed()

    def _press_enter_until_variants_listed(self) -> None:
        """A cold app ignores the first Enter on the item list, so it is repeated until variants show."""
        for _ in range(PICK_ATTEMPTS):
            self._item_search.press("Enter")
            try:
                self._selected_variant.wait_for(state="visible", timeout=PICK_ATTEMPT_TIMEOUT_MS)
            except PlaywrightTimeoutError:
                continue
            return
        expect(self._selected_variant).to_be_visible(timeout=STEP_TIMEOUT_MS)

    def _confirm_variant(self) -> None:
        expect(self._selected_variant).to_be_visible(timeout=STEP_TIMEOUT_MS)
        self.page.keyboard.press("Enter")

    @property
    def _selected_variant(self) -> Locator:
        selected_variant = self.page.locator(f'.ag-row-selected [col-id="{VARIANT_BALANCE}"]')
        return selected_variant.filter(has_text=self._any_digit()).first

    def _commit_quantity(self, quantity: Decimal) -> None:
        editor = self.page.locator("#txt-qty-0")
        expect(editor).to_be_visible(timeout=STEP_TIMEOUT_MS)
        editor.press("Control+A")
        editor.press_sequentially(str(quantity))
        editor.press("Tab")
        self.page.keyboard.press(COMMIT_SHORTCUT)

    def _highlighted_item(self, item_name: str) -> Locator:
        marker = self.page.locator(f'[col-id="{PICKER_PRODUCT}"]').get_by_text(item_name, exact=True)
        return self.page.locator(".ag-row-selected").filter(has=marker)

    def _barcode_cell(self, row: int) -> Locator:
        return self.page.locator(f"#txt-tmp_barcode-{row}")

    @property
    def _grid(self) -> AgGrid:
        return AgGrid(self.page, PRODUCT)

    def _reach_first_barcode_cell(self) -> None:
        """After the party the focus sometimes stops on Store; Enter there moves it to the first line."""
        if not appears_within(self._barcode_cell(0), FIRST_CELL_SETTLE_MS):
            self._store.press("Enter")
        expect(self._barcode_cell(0)).to_be_visible(timeout=SCREEN_TIMEOUT_MS)

    @property
    def _party(self) -> Locator:
        # Why an id prefix: the inputs carry no labels; ids end in a per-tab number (txtLedgerName48),
        # and the newest tab is the last one.
        return self.page.locator("[id^=txtLedgerName]").last

    @property
    def _store(self) -> Locator:
        return self.page.locator("[id^=txtStore]").last

    @property
    def _item_search(self) -> Locator:
        return self.page.locator("#searchItems").first

    @staticmethod
    def _any_digit() -> re.Pattern[str]:
        return re.compile(r"\d")
