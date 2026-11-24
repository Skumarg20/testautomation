"""Stock Management > Bill of Materials > Material Master: the BOM list and the BOM editor.

Seen live 2026-10-12 (`/transaction/billofmaterial`, GANE29): heading "Material Master", button "Create/F2",
grid columns S.No, Date, BOM Name, Product, Qty, By Product Qty., Action. The editor could not be opened
with the BOM switch off, so its locators come from the Angular source (`billofmaterialmaster.html:26-50`,
`bom.itemselection.ts:21`) and are unverified live; see specs/manufacturing-module.md.
"""

import re
from decimal import Decimal
from enum import Enum

from playwright.sync_api import Locator, expect

from pages.base_page import BasePage
from pages.components.confirm_dialog import ConfirmDialog
from pages.manufacturing.menu import ManufacturingMenu, ManufacturingScreen
from pages.purchase.documents.feedback import AppFeedback
from pages.purchase.documents.selection_window import SelectionWindow
from pages.stock.messages import StockMessages
from test_data.manufacturing import BomSpec, Component

ROW_TIMEOUT_MS = 20_000
LIST_PATH = "/transaction/billofmaterial"
SAVED = re.compile(r"Record saved successfully\.")
UPDATED = re.compile(r"Record updated successfully\.")
DELETED_AS_UPDATED = UPDATED
ALREADY_USED = re.compile(r"Bill of Material Already Used")


class HeaderField(Enum):
    """The editor's header inputs; their `validation-message` labels are "BOM Name", "Item Name" and
    "Quantity" (billofmaterialmaster.html:30-53)."""

    NAME = "#txtbomname"
    ITEM = "#txtitemname"
    QUANTITY = "#txtqty"


class BomMasterList(BasePage):
    def open(self) -> None:
        ManufacturingMenu(self.page).open_screen(ManufacturingScreen.MATERIAL_MASTER)
        expect(self.page.get_by_role("heading", name="Material Master")).to_be_visible()

    def open_by_url(self) -> None:
        """The list opens by URL even with the BOM switch off (spec N3), so a company without it works."""
        self.goto(LIST_PATH)
        expect(self.page.get_by_role("heading", name="Material Master")).to_be_visible()

    def create(self) -> None:
        self.page.get_by_role("button", name="Create/F2").click()
        AppFeedback(self.page).wait_for_loader()

    def edit(self, name: str) -> None:
        """Opens "Update Material Master" (billofmaterialmasterlist.ts:211-212)."""
        self._row(name).get_by_role("button", name="Edit").click()
        AppFeedback(self.page).wait_for_loader()

    def expect_listed(self, bom: BomSpec) -> None:
        row = self._row(bom.name)
        expect(row).to_be_visible(timeout=ROW_TIMEOUT_MS)
        expect(row.get_by_text(bom.finished.product, exact=True)).to_be_visible()

    def has(self, name: str) -> bool:
        return self._row(name).count() > 0

    def expect_not_listed(self, name: str) -> None:
        expect(self._row(name)).to_have_count(0, timeout=ROW_TIMEOUT_MS)

    def quantity_of(self, name: str) -> str:
        return self._cell(name, "quantity").inner_text().strip()

    def by_product_quantity_of(self, name: str) -> str:
        return self._cell(name, "byproductQuantity").inner_text().strip()

    def delete(self, name: str) -> None:
        """Delete, then Yes. The app answers "Record updated successfully." (pack K3)."""
        self._row(name).get_by_role("button", name="Delete").click()
        ConfirmDialog(self.page).answer_yes()

    def expect_deleted(self) -> None:
        StockMessages(self.page).expect_shown(DELETED_AS_UPDATED)

    def expect_delete_refused_as_used(self) -> None:
        StockMessages(self.page).expect_shown(ALREADY_USED)

    def _row(self, name: str) -> Locator:
        return self.page.get_by_role("row").filter(has=self.page.get_by_text(name, exact=True))

    def _cell(self, name: str, column: str) -> Locator:
        # Why col-id: the BOM list is an ag-Grid whose cells are told apart only by col-id.
        return self._row(name).locator(f'[col-id="{column}"]')


class BomMasterForm(BasePage):
    def fill(self, bom: BomSpec) -> None:
        self.enter_header(bom)
        for row, component in enumerate(bom.raw_materials):
            self.add_raw_material(row, component)

    def enter_header(self, bom: BomSpec) -> None:
        self._name.fill(bom.name)
        self.choose_item(bom.finished.product)
        self.type_quantity(bom.quantity)
        self._field(HeaderField.QUANTITY).press("Enter")

    def choose_item(self, product: str) -> None:
        self._field(HeaderField.ITEM).click()
        SelectionWindow(self.page).choose_cell_text(product)

    def type_quantity(self, quantity: Decimal) -> None:
        self._field(HeaderField.QUANTITY).fill(str(quantity))

    def leave_blank(self, field: HeaderField) -> None:
        """Focus the field and leave it empty, which marks it touched (the Item field opens its window)."""
        if field is HeaderField.ITEM:
            self.leave_item_unchosen()
            return
        self._field(field).click()
        self._field(field).fill("")
        self._field(field).blur()

    def add_raw_material(self, row: int, component: Component) -> None:
        item_editor = self.page.locator(f"#txt-itemLinkID-{row}")
        if not item_editor.is_visible():
            self._raw_cell(row, "itemLinkID").click()
        item_editor.press("Space")
        SelectionWindow(self.page).choose_cell_text(component.item.product)
        self._enter_raw_quantity(row, component.quantity_per_set)

    def type_name(self, name: str) -> None:
        self._name.fill("")
        self._name.press_sequentially(name)

    def name_typed(self) -> str:
        return self._name.input_value()

    def leave_item_unchosen(self) -> None:
        """Focus on Item to Produce opens "Select Item"; Escape closes it with nothing chosen."""
        self._field(HeaderField.ITEM).click()
        SelectionWindow(self.page).close_without_choosing()

    def press_tab_on_quantity(self) -> None:
        self._field(HeaderField.QUANTITY).press("Tab")

    def leave_name(self) -> None:
        self._name.blur()

    def save(self) -> None:
        self.page.get_by_role("button", name="Save").click()

    def update(self) -> None:
        """The editor's button reads "Update" when a saved BOM is open (billofmaterialmaster.html:128)."""
        self.page.get_by_role("button", name="Update").click()

    def expect_saved(self) -> None:
        StockMessages(self.page).expect_shown(SAVED)
        expect(self.page).to_have_url(re.compile(f"{LIST_PATH}$"))

    def expect_updated(self) -> None:
        StockMessages(self.page).expect_shown(UPDATED)
        expect(self.page).to_have_url(re.compile(f"{LIST_PATH}$"))

    def expect_refused(self, message: re.Pattern[str]) -> None:
        StockMessages(self.page).expect_shown(message)
        expect(self._name).to_be_visible()

    def expect_field_message(self, message: re.Pattern[str]) -> None:
        """The red text a `validation-message` puts under a header field, e.g. "BOM Name required !"
        (validation.component.html:17-53)."""
        expect(self.page.get_by_text(message).first).to_be_visible()
        expect(self._name).to_be_visible()

    def expect_no_field_message(self, message: re.Pattern[str]) -> None:
        expect(self.page.get_by_text(message)).to_have_count(0)

    def expect_raw_material_listed(self, row: int, product: str) -> None:
        """MBC-16368: a saved BOM opened for change shows its raw materials."""
        expect(self._raw_cell(row, "itemLinkID")).to_have_text(re.compile(rf"^\s*{re.escape(product)}\s*$"))

    def change_raw_quantity(self, row: int, quantity: Decimal) -> None:
        self._enter_raw_quantity(row, quantity)

    @property
    def _name(self) -> Locator:
        return self._field(HeaderField.NAME)

    def _field(self, field: HeaderField) -> Locator:
        # Why ids: the editor's labels are not tied to their inputs (billofmaterialmaster.html:26-50).
        return self.page.locator(field.value)

    def _enter_raw_quantity(self, row: int, quantity: Decimal) -> None:
        self._raw_cell(row, "quantity").click()
        field = self._raw_cell(row, "quantity").locator("input")
        field.fill(str(quantity))
        field.press("Enter")

    def _raw_cell(self, row: int, column: str) -> Locator:
        # Why CSS: the raw-material grid (#rmcproduct) is an ag-Grid; rows and cells have no names.
        grid = self.page.locator("#rmcproduct")
        return grid.locator(f'.ag-row[row-index="{row}"] [col-id="{column}"]').first
