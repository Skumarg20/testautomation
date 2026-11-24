"""Saving this run's raw-material, finished, service and conversion items through Master > Item.

Reuses the item form and its "add item Opening?" window (pages/stock/opening_stock.py). Added here, from
the Angular source and unverified live:
- the Conversion field `#txtunitConversion` (createitem.component.html:193-205). It shows when Control Room
  field 4505 is on (createitem.component.ts:863-864) and is read-only once the item has been used in a
  conversion (`isMultiUnitItemUsed`, createitem.component.ts:1763). The older `#txtconversion` sits in a
  commented-out block (createitem.component.html:2094-2109) and is not rendered;
- the supply type select `#typeofSupply` with the option "Service" (createitem.component.html:112).
"""

from playwright.sync_api import Locator, Page, expect

from pages.inventory.create_item_page import CreateItemPage
from pages.inventory.item_alert import ItemAlert
from pages.inventory.item_list_page import ItemListPage
from pages.stock.opening_stock import OpeningStockWindow
from test_data.manufacturing import StockItem
from test_data.models import ItemMasterSpec

SERVICE_SUPPLY = "Service"
FORM_TIMEOUT_MS = 30_000


def save_stock_item(page: Page, item: StockItem) -> None:
    form = CreateItemPage(page)
    form.open()
    form.fill(item.spec)
    if item.conversion is not None:
        conversion_field(page).fill(str(item.conversion))
    form.save()
    form.expect_saved()
    form.expect_opening_stock_offered()
    if item.opening:
        _enter_opening(page, item)
    else:
        form.decline_opening_stock()


def save_service_item(page: Page, spec: ItemMasterSpec) -> None:
    """MF-11: an item whose supply type is Service, which the raw-material picker must refuse."""
    form = CreateItemPage(page)
    form.open()
    form.fill(spec)
    # Why id: the item form's labels are not tied to their inputs (as in CreateItemPage).
    page.locator("#typeofSupply").select_option(label=SERVICE_SUPPLY)
    form.save()
    form.expect_saved()
    form.expect_opening_stock_offered()
    form.decline_opening_stock()


def open_item_for_change(page: Page, product: str) -> None:
    item_list = ItemListPage(page)
    item_list.open()
    item_list.edit(product)
    CreateItemPage(page).expect_editing(product)


def expect_conversion_locked(page: Page) -> None:
    """MF-33: an item used in a conversion keeps its Conversion (read-only and disabled)."""
    field = conversion_field(page)
    expect(field).to_be_visible(timeout=FORM_TIMEOUT_MS)
    expect(field).not_to_be_editable()


def conversion_field(page: Page) -> Locator:
    # Why id: the item form's labels are not tied to their inputs (as in CreateItemPage).
    return page.locator("#txtunitConversion")


def _enter_opening(page: Page, item: StockItem) -> None:
    # Not ItemAlert.answer_yes: the Opening window that follows uses the same box classes.
    ItemAlert(page).question.locator("#btnYes").click()
    opening = OpeningStockWindow(page)
    opening.enter(item.opening)
    opening.expect_saved()
