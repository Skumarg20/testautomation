"""The purchase bill entry window (Alt+P): supplier, invoice number, item lines, totals and save."""

import re
from dataclasses import dataclass
from decimal import Decimal

from playwright.sync_api import Locator, expect

from pages.base_page import BasePage
from pages.components.shortcut import press_until_visible
from pages.grid.ag_grid import AgGrid
from pages.grid.item_picker import ItemPicker
from test_data.models import PurchaseLine
from test_data.money import parse_amount

OPEN_SHORTCUT = "Alt+P"
OPEN_TIMEOUT_MS = 30_000
STEP_TIMEOUT_MS = 15_000
PRODUCT = "itemLinkID"
QUANTITY = "quantity"
RATE = "salePurchaseRate"
AMOUNT = "DisplayAmount"
PURCHASE_RATE = "purchaseRate"
MAX_TABS_TO_QUANTITY = 4
TAX_LINE = re.compile(r"(CGST|SGST|IGST)\s+[\d.]+%\s*:?\s*([\d.,]+)")


@dataclass(frozen=True)
class GarmentsPurchaseLine:
    item_name: str
    quantity: Decimal
    rate: Decimal


class PurchaseBillPage(BasePage):
    def open(self) -> None:
        press_until_visible(self.page, OPEN_SHORTCUT, self._supplier)

    def choose_supplier(self, name: str) -> None:
        search = self.page.get_by_role("searchbox", name="Search", exact=True)
        search.click()
        search.press_sequentially(name)
        self._supplier_row(name).click()
        expect(self._supplier).to_have_value(name, timeout=OPEN_TIMEOUT_MS)

    def start_manual_entry(self) -> None:
        self._manual_entry_button.click()

    def set_invoice_number(self, invoice_number: str) -> None:
        self._invoice_number.fill(invoice_number)

    def enter_invoice_number_and_date(self, invoice_number: str) -> None:
        """The app accepts digits only; Enter twice moves from Invoice No. over Invoice Date to the grid."""
        self._invoice_number.fill(invoice_number)
        self._invoice_number.press("Enter")
        self.page.locator("[id^=txtisInvoiceDate]").press("Enter")
        expect(self._barcode_cell(0)).to_be_visible(timeout=STEP_TIMEOUT_MS)

    def add_garments_line(self, row: int, line: GarmentsPurchaseLine) -> None:
        self._open_item_picker(row)
        self._pick_highlighted_item(line.item_name)
        self._enter_quantity_and_rate(line.quantity, line.rate)
        expect(self._barcode_cell(row + 1)).to_be_visible(timeout=STEP_TIMEOUT_MS)

    def expect_toast(self, message: str) -> None:
        expect(self.page.get_by_text(message)).to_be_visible(timeout=STEP_TIMEOUT_MS)

    def add_line(self, row: int, line: PurchaseLine) -> None:
        grid = AgGrid(self.page, PRODUCT)
        grid.cell(row, PRODUCT).click()
        ItemPicker(self.page).choose_by_description(line.item.description)
        self._type_and_confirm(grid.cell_input(row, QUANTITY), str(line.quantity))
        self._type_and_confirm(grid.cell_input(row, RATE), str(line.rate))

    def line_amount(self, row: int) -> Decimal:
        return parse_amount(AgGrid(self.page, PRODUCT).cell(row, AMOUNT).inner_text())

    def bill_value(self) -> Decimal:
        return parse_amount(self._bill_value.input_value())

    def tax_amounts(self) -> dict[str, Decimal]:
        """CGST, SGST and IGST amounts from the Tax Info panel; the panel lists only the taxes that apply."""
        panel_text = self._tax_info_panel.inner_text()
        return {tax: parse_amount(amount) for tax, amount in TAX_LINE.findall(panel_text)}

    def save(self) -> None:
        self._save_button.click()

    def _open_item_picker(self, row: int) -> None:
        cell = self._barcode_cell(row)
        cell.click()
        cell.press("Enter")
        expect(self._item_search).to_be_visible(timeout=STEP_TIMEOUT_MS)

    def _pick_highlighted_item(self, item_name: str) -> None:
        self._item_search.press_sequentially(item_name)
        marker = self.page.locator('[col-id="Product"]').get_by_text(item_name, exact=True)
        expect(self.page.locator(".ag-row-selected").filter(has=marker)).to_be_visible(
            timeout=STEP_TIMEOUT_MS
        )
        self._item_search.press("Enter")

    def _enter_quantity_and_rate(self, quantity: Decimal, rate: Decimal) -> None:
        """The variant window opens on its first column; Tab reaches Qty. P.Rate is edited by double-click.

        The first column follows the company's variant settings: Barcode before, Design since 2026-10-09.
        """
        expect(self.page.locator(".ag-cell input:focus")).to_have_count(1, timeout=STEP_TIMEOUT_MS)
        quantity_cell = self.page.locator("#txt-qty-0")
        for _ in range(MAX_TABS_TO_QUANTITY):
            self.page.keyboard.press("Tab")
            expect(self.page.locator(".ag-cell input:focus")).to_have_count(1, timeout=STEP_TIMEOUT_MS)
            if self.page.locator("#txt-qty-0:focus").count():
                break
        expect(quantity_cell).to_be_focused(timeout=STEP_TIMEOUT_MS)
        quantity_cell.press("Control+A")
        quantity_cell.press_sequentially(str(quantity))
        quantity_cell.press("Tab")
        expect(self._variant_amount_cell).to_have_text(re.compile(r"\d"), timeout=STEP_TIMEOUT_MS)
        self._variant_rate_cell.dblclick()
        rate_cell = self.page.locator("#txt-purchaseRate-0")
        expect(rate_cell).to_be_visible(timeout=STEP_TIMEOUT_MS)
        rate_cell.press("Control+A")
        rate_cell.press_sequentially(str(rate))
        rate_cell.press("Tab")
        expect(self._variant_rate_cell).to_have_text(f"{rate:.3f}", timeout=STEP_TIMEOUT_MS)
        self.page.keyboard.press("F10")

    def _barcode_cell(self, row: int) -> Locator:
        return self.page.locator(f"#txt-tmp_barcode-{row}")

    @property
    def _variant_rate_cell(self) -> Locator:
        return self.page.locator(f'ngb-modal-window .ag-row[row-index="0"] [col-id="{PURCHASE_RATE}"]').first

    @property
    def _variant_amount_cell(self) -> Locator:
        return self.page.locator('ngb-modal-window .ag-row[row-index="0"] [col-id="amount"]').first

    @property
    def _item_search(self) -> Locator:
        return self.page.locator("#searchItems").first

    @property
    def _supplier(self) -> Locator:
        return self.page.locator('input[formcontrolname="ledgerName"]')

    @property
    def _invoice_number(self) -> Locator:
        return self.page.locator('input[formcontrolname="entryNo"]')

    @property
    def _bill_value(self) -> Locator:
        return self.page.locator('input[formcontrolname="BillValueAmount"]')

    @property
    def _manual_entry_button(self) -> Locator:
        return self.page.get_by_role("button", name="Start Manual Entry")

    @property
    def _save_button(self) -> Locator:
        return self.page.locator("[id^=btnSave]")

    @property
    def _tax_info_panel(self) -> Locator:
        titled = self.page.locator("div").filter(has=self.page.get_by_text("Tax Info", exact=True))
        return titled.filter(has_text=TAX_LINE).last

    def _supplier_row(self, name: str) -> Locator:
        marker = self.page.locator('[col-id="LedgerName"]').get_by_text(name, exact=True)
        return self.page.get_by_role("row").filter(has=marker).first

    @staticmethod
    def _type_and_confirm(field: Locator, value: str) -> None:
        field.fill(value)
        field.press("Enter")
