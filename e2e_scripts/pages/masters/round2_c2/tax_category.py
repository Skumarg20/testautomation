"""Master > Tax Category: a category of the test's own with a zero-rate type (Exempted, Zero Rated, Nil
Rated).

Source: UI/Master/TaxCategory/add.taxcategory.component.html (name `#name`, GST rate `#igst`, "Zero-Type"
`#zerotaxtype` with option values 0 Exempted, 1 Zero Rated, 2 Nil Rated, Save `#btnSave`); the list is the
route
`mstr/taxcategory` (Modules/other.masters.module.ts:155). In the item form a "Tax Category" is a sale type
(Component/Master/Item/createitem.component.ts:3945-3950), so the item picks the new category by its name.
Part C2 owns this helper.
"""

import re
from enum import Enum

from playwright.sync_api import Page, expect

from pages.accounting.toasts import Toasts
from pages.base_page import BasePage
from pages.masters.master_list import MasterList

SAVED_MESSAGE = re.compile("Record Saved Successfully", re.IGNORECASE)
PAGE_TIMEOUT_MS = 120_000
FORM_TIMEOUT_MS = 30_000
LIST_PATH = "/mstr/taxcategory"


class ZeroTaxType(Enum):
    """Option values of `#zerotaxtype`."""

    EXEMPTED = "0"
    ZERO_RATED = "1"
    NIL_RATED = "2"


class TaxCategoryList(MasterList):
    def open(self) -> None:
        self.page.goto(LIST_PATH, wait_until="domcontentloaded", timeout=PAGE_TIMEOUT_MS)
        self._wait_until_loaded()


class TaxCategoryForm(BasePage):
    def create(self, name: str, zero_type: ZeroTaxType) -> None:
        TaxCategoryList(self.page).open()
        self.page.get_by_role("button", name="Create/F2").click()
        field = self.page.locator("#name")
        expect(field).to_be_visible(timeout=FORM_TIMEOUT_MS)
        field.fill(name)
        self.page.locator("#igst").fill("0")
        self.page.locator("#zerotaxtype").select_option(zero_type.value)
        self.page.locator("#btnSave").click()
        Toasts(self.page).expect_success_saying(SAVED_MESSAGE)


class OwnedTaxCategories:
    """Categories made by one test; deleted at the end (items using them must be deleted first)."""

    def __init__(self, page: Page, run_id: str) -> None:
        self._page = page
        self._run_id = run_id
        self._names: list[str] = []

    def saved(self, zero_type: ZeroTaxType) -> str:
        name = f"QA-{self._run_id}-{zero_type.name.title().replace('_', '')}"
        self._names.append(name)
        TaxCategoryForm(self._page).create(name, zero_type)
        return name

    def delete_all(self) -> None:
        categories = TaxCategoryList(self._page)
        categories.open()
        for name in self._names:
            if categories.is_listed(name):
                categories.delete(name)
        self._names.clear()
