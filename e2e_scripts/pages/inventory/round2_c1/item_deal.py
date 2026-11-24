"""The "Free / Scheme" deal and "Scheme Type" of an item master, held for a test and put back.

Create Item form: `#txtFree` (buy quantity = scheme1), `#txtScheme` (free quantity = scheme2), `#Validfrom`
(Scheme Type; lookup type 1016: Full / Half / 1/3 / Qtr. / All / Whole / No Scheme), createitem.component.html
:922-945; shown for pharma/kirana/billing companies. The sale bill reads them as Free and Scheme
(processout.transaction.component.ts:13419-13424). The item is found in the list by its code and edited
with Edit/F3 (ItemListPage); a deal that is 0 + 0 is saved as it was.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass

from playwright.sync_api import Locator

from pages.accounting.waiting import appears_within
from pages.base_page import BasePage
from pages.inventory.create_item_page import CreateItemPage
from pages.purchase.documents.navigation import ModuleMenu

FORM_WAIT_MS = 30_000
LIST_WAIT_MS = 30_000
SEARCH_KEY_DELAY_MS = 50
SCHEME_LABELS = (
    "Full Scheme",
    "Half Scheme",
    "1/3 Scheme",
    "Qtr. Scheme",
    "All Scheme",
    "Whole Scheme",
    "No Scheme",
)


@dataclass(frozen=True)
class Deal:
    buy: str
    free: str
    scheme_type: str


class ItemDealForm(BasePage):
    def open_item(self, code: str) -> None:
        ModuleMenu(self.page).open_item_master()
        search = self.page.get_by_role("searchbox", name="Search", exact=True)
        search.click()
        self.page.keyboard.press("Control+A")
        self.page.keyboard.type(code, delay=SEARCH_KEY_DELAY_MS)
        row = self._row(code)
        appears_within(row, LIST_WAIT_MS)
        row.first.locator('[col-id="itemcode"]').click()
        row.first.get_by_role("button", name="Edit/F3").click()
        self.page.locator("#txtFree").wait_for(state="visible", timeout=FORM_WAIT_MS)

    def read(self) -> Deal:
        scheme = self.page.locator("#Validfrom")
        chosen = scheme.locator("option:checked").inner_text().strip() if scheme.count() else ""
        return Deal(
            self.page.locator("#txtFree").input_value(), self.page.locator("#txtScheme").input_value(), chosen
        )

    def write(self, deal: Deal) -> None:
        self.page.locator("#txtFree").fill(deal.buy)
        self.page.locator("#txtScheme").fill(deal.free)
        if deal.scheme_type:
            self.page.locator("#Validfrom").select_option(label=deal.scheme_type)

    def update(self) -> None:
        form = CreateItemPage(self.page)
        form.save()
        form.expect_updated()

    def _row(self, code: str) -> Locator:
        cell = self.page.locator('[col-id="itemcode"]').filter(has_text=code)
        return self.page.get_by_role("row").filter(has=cell)


@contextmanager
def deal_held(form: ItemDealForm, code: str, wanted: Deal) -> Iterator[Deal]:
    """Yields the item's own deal; it is always written back."""
    form.open_item(code)
    original = form.read()
    form.write(wanted)
    form.update()
    try:
        yield original
    finally:
        form.open_item(code)
        form.write(original)
        form.update()
