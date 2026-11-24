"""The one 0% GST item the outstanding cases sell, so a bill's amount is exactly its line rate.

No item on the garments company had 0% GST (5%, 12% and 28% seen 2026-10-09), so it is created once with
tax category "GST Sale-Exempt" and then reused by every run; it is never deleted, because bills use it.
"""

from decimal import Decimal

from pages.base_page import BasePage
from pages.inventory.create_item_page import CreateItemPage
from pages.inventory.item_list_page import ItemListPage
from test_data.models import ItemMasterSpec

EXEMPT_ITEM = ItemMasterSpec(
    product="QA Outstanding Exempt Item",
    unit="PCS",
    hsn="12345678",
    tax_category="GST Sale-Exempt",
    gst_rate=Decimal(0),
    company="Others",
    mrp=Decimal(100_000),
    sale_rate=Decimal(1),
)


class ExemptItem(BasePage):
    def ensure_exists(self) -> str:
        items = ItemListPage(self.page)
        items.open()
        if not items.has_item(EXEMPT_ITEM.product):
            self._create()
        return EXEMPT_ITEM.product

    def _create(self) -> None:
        form = CreateItemPage(self.page)
        form.open()
        form.fill(EXEMPT_ITEM)
        form.save()
        form.expect_opening_stock_offered()
        form.decline_opening_stock()
