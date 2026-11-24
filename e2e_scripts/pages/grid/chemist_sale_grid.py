"""The item grid of a chemist sale bill: add items, edit saved rows, read cell values."""

from decimal import Decimal

from playwright.sync_api import Locator, Page

from pages.grid.ag_grid import AgGrid
from pages.grid.batch_window import BatchWindow
from pages.grid.item_picker import ItemPicker
from test_data.models import ItemEntry

PRODUCT = "itemLinkID"
BARCODE = "tmp_barcode"
QUANTITY = "unitToEnteredValue"
SALE_RATE = "salePurchaseRate"
BATCH = "batchLinkID"
DISCOUNT_COLUMNS = ("discount1", "discount2", "volumediscount", "volumediscount2")
DISCOUNT_1, DISCOUNT_2, VOLUME_DISCOUNT_1, VOLUME_DISCOUNT_2 = DISCOUNT_COLUMNS
# Money comes as Decimal; float is still accepted because ItemEntry and SaleBill pass floats (to migrate).
Amount = Decimal | float | int


def grid_text(value: Amount) -> str:
    """How a value is typed into the grid: plain decimal notation, never a float's exponent form (1e-05)."""
    return format(Decimal(str(value)), "f")


class MissingItemKeyError(ValueError):
    def __init__(self) -> None:
        super().__init__("An item needs a barcode, itemcode or description")


class ChemistSaleGrid:
    def __init__(self, page: Page) -> None:
        self._page = page
        self._grid = AgGrid(page, PRODUCT)
        self._picker = ItemPicker(page)
        self._batches = BatchWindow(page)

    def add_item(self, row: int, entry: ItemEntry) -> None:
        self._select_item(row, entry)
        self._resolve_prompts(row, entry)
        self._enter_values(row, entry)

    def add_items(self, entries: list[ItemEntry]) -> None:
        for row, entry in enumerate(entries):
            self.add_item(row, entry)

    def replace_item(self, row: int, entry: ItemEntry) -> None:
        self._grid.cell(row, PRODUCT).click()
        self._grid.cell_input(row, PRODUCT).press("Space")
        self._select_by_description_or_code(entry)
        self._resolve_prompts(row, entry)
        self._enter_values(row, entry)

    def change_quantity(self, row: int, quantity: int) -> None:
        self._edit_cell(row, QUANTITY, quantity)

    def change_sale_rate(self, row: int, rate: Amount) -> None:
        self._edit_cell(row, SALE_RATE, rate)

    def change_discounts(self, row: int, entry: ItemEntry) -> None:
        for column, value in zip(DISCOUNT_COLUMNS, self._discount_values(entry), strict=True):
            if value is not None:
                self._edit_cell(row, column, value)

    def change_batch(self, row: int, batch_name: str) -> None:
        self._grid.cell(row, BATCH).click()
        self._page.locator("input#searchItems").fill(batch_name)
        self._page.get_by_text(batch_name, exact=True).click()
        self._page.keyboard.press("Enter")

    def value_of(self, row: int, column: str) -> Decimal:
        text = self._grid.cell(row, column).inner_text()
        return Decimal(text.replace(",", "").strip())

    def quantity_of(self, row: int) -> Decimal:
        return self.value_of(row, QUANTITY)

    def sale_rate_of(self, row: int) -> Decimal:
        return self.value_of(row, SALE_RATE)

    def discount1_of(self, row: int) -> Decimal:
        return self.value_of(row, DISCOUNT_1)

    def discount2_of(self, row: int) -> Decimal:
        return self.value_of(row, DISCOUNT_2)

    def volume_discount1_of(self, row: int) -> Decimal:
        return self.value_of(row, VOLUME_DISCOUNT_1)

    def volume_discount2_of(self, row: int) -> Decimal:
        return self.value_of(row, VOLUME_DISCOUNT_2)

    def product_of(self, row: int) -> str:
        return self._grid.cell(row, PRODUCT).inner_text().strip()

    def _select_item(self, row: int, entry: ItemEntry) -> None:
        if entry.barcode is not None:
            self._grid.cell(row, BARCODE).click()
            self._type_and_confirm(self._grid.cell_input(row, BARCODE), entry.barcode)
        else:
            self._grid.cell(row, PRODUCT).click()
            self._select_by_description_or_code(entry)

    def _select_by_description_or_code(self, entry: ItemEntry) -> None:
        if entry.itemcode is not None:
            self._picker.choose_by_item_code(entry.itemcode)
        elif entry.description is not None:
            self._picker.choose_by_description(entry.description)
        else:
            raise MissingItemKeyError

    def _resolve_prompts(self, row: int, entry: ItemEntry) -> None:
        quantity_cell = self._grid.cell_input(row, QUANTITY)
        self._batches.wait_for_next_step(quantity_cell)
        if self._batches.is_yes_popup_shown():
            self._batches.confirm_yes()
            self._batches.wait_for_next_step(quantity_cell)
        if self._batches.is_batch_window_shown():
            self._batches.choose_batch(entry.expiry_type)

    def _enter_values(self, row: int, entry: ItemEntry) -> None:
        if entry.quantity is None:
            return
        self._type_and_confirm(self._grid.cell_input(row, QUANTITY), entry.quantity)
        if entry.quantity <= 0:
            return
        self._enter_sale_rate(row, entry.sale_rate)
        self._enter_discounts(row, entry)

    def _enter_sale_rate(self, row: int, rate: Amount | None) -> None:
        field = self._grid.cell_input(row, SALE_RATE)
        if rate is None:
            field.press("Enter")
        else:
            self._type_and_confirm(field, rate)

    def _enter_discounts(self, row: int, entry: ItemEntry) -> None:
        values = self._discount_values(entry)
        last_given = max((i for i, value in enumerate(values) if value is not None), default=-1)
        for column, value in list(zip(DISCOUNT_COLUMNS, values, strict=True))[: last_given + 1]:
            field = self._grid.cell_input(row, column)
            if not field.is_visible():
                continue
            if value is not None:
                field.fill(grid_text(value))
            field.press("Enter")

    def _edit_cell(self, row: int, column: str, value: Amount) -> None:
        self._grid.cell(row, column).click()
        self._type_and_confirm(self._grid.cell_input(row, column), value)

    @staticmethod
    def _discount_values(entry: ItemEntry) -> tuple[Amount | None, ...]:
        return (entry.discount1, entry.discount2, entry.volume_discount1, entry.volume_discount2)

    @staticmethod
    def _type_and_confirm(field: Locator, value: Amount) -> None:
        field.fill(grid_text(value))
        field.press("Enter")
