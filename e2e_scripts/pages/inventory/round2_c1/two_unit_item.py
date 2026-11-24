"""An item with a second (bigger) unit, made through the Create Item form and its Multi Unit window.

`#btnMultiUnit` shows only while Multi Unit is Yes (createitem.component.html:234-238). The window is the
ag-Grid `#multiUnit` (multiunit.component.html): row 1 holds the unit select `#drp-FromUnitLinkId-1`
(MultiUnitSelectTemplate: `drp-<col>-<row>`) and the Quantity cell (conversion: 1 bigger unit = N base units,
multiunit.component.ts:333-345); Save/Close buttons end it. The base unit (row 0) is the item's own unit.
"""

from playwright.sync_api import Locator, expect

from pages.base_page import BasePage
from pages.inventory.create_item_page import CreateItemPage

WINDOW_TIMEOUT_MS = 15_000


class UnitOffer:
    """The units a Multi Unit window lets row 1 choose from."""

    def __init__(self, names: list[str]) -> None:
        self.names = names

    def other_than(self, base: str) -> str:
        for name in self.names:
            if name.strip() and name.strip().lower() != base.lower():
                return name.strip()
        raise LookupError(f"The Multi Unit window offers no unit besides {base}")


class ItemMultiUnitWindow(BasePage):
    def open(self) -> None:
        self.page.locator("#btnMultiUnit").click()
        expect(self._cell(1, "FromUnitLinkId")).to_be_visible(timeout=WINDOW_TIMEOUT_MS)

    def offered_units(self) -> UnitOffer:
        self._cell(1, "FromUnitLinkId").click()
        select = self.page.locator("#drp-FromUnitLinkId-1")
        expect(select).to_be_visible(timeout=WINDOW_TIMEOUT_MS)
        return UnitOffer(select.locator("option").all_inner_texts())

    def set_second_unit(self, unit: str, pieces: int) -> None:
        self.page.locator("#drp-FromUnitLinkId-1").select_option(label=unit)
        quantity = self._cell(1, "Quantity")
        quantity.click()
        quantity.locator("input").fill(str(pieces))
        quantity.locator("input").press("Enter")

    def save(self) -> None:
        self.page.locator("#multiUnit").locator("xpath=ancestor::form").get_by_role(
            "button", name="Save"
        ).click()

    def _cell(self, row: int, column: str) -> Locator:
        return self.page.locator(f'#multiUnit [row-id="{row}"] [col-id="{column}"]')


def give_second_unit(page_item: CreateItemPage, pieces: int) -> str:
    """On an open Create Item form: adds a bigger unit worth `pieces` base units; returns its name."""
    window = ItemMultiUnitWindow(page_item.page)
    window.open()
    unit = window.offered_units().other_than("PCS")
    window.set_second_unit(unit, pieces)
    window.save()
    return unit
