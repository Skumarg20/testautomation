"""The own Online Store's item list (`/other/onlineStore/onlinestoreitemlist`), opened from "Manage Item".

From `Component/Online-Store/ProductList/OnlineStoreProductList.component.html`: heading "Item List"; a
"Search..." box (`:71`); radio filters "All Item (n)", "Mapped Item (n)", "Un-Mapped Item (n)" (`:85-87`); a
table with a tick box per row (`:149`); "Upload Item" (`:15-28`, not in the Mapped view) and "Un-Map Item"
(`:29-42`, Mapped view only), both disabled while no row is ticked; per row an "Edit Product" link (`:209`)
and a hide/show link (`:217`, no title, the row's last link). Upload, unmap and hide ask first in the app's
"Confirmation" dialog. Not seen live.
"""

import re
from decimal import Decimal

from playwright.sync_api import Locator, expect

from pages.base_page import BasePage
from pages.components.confirm_dialog import ConfirmDialog
from pages.purchase.documents.feedback import AppFeedback

PAGE_TIMEOUT_MS = 30_000
SEARCH_PLACEHOLDER = "Search..."
MAPPED_FILTER = re.compile(r"^\s*Mapped Item \((\d+)\)")
EDIT_TITLE = "Edit Product"


class StoreItemList(BasePage):
    def expect_open(self) -> None:
        expect(self.page.get_by_role("heading", name="Item List")).to_be_visible(timeout=PAGE_TIMEOUT_MS)

    @property
    def upload_button(self) -> Locator:
        return self.page.get_by_role("button", name="Upload Item")

    @property
    def unmap_button(self) -> Locator:
        return self.page.get_by_role("button", name="Un-Map Item")

    def search(self, product: str) -> None:
        self.page.get_by_placeholder(SEARCH_PLACEHOLDER, exact=True).fill(product)
        AppFeedback(self.page).wait_for_loader()

    def tick(self, product: str) -> None:
        self._row(product).get_by_role("checkbox").check()

    def tick_first_row(self) -> None:
        self._body_rows.first.get_by_role("checkbox").check()

    def show_mapped(self) -> None:
        self.page.get_by_role("radio", name=MAPPED_FILTER).check()
        AppFeedback(self.page).wait_for_loader()

    def mapped_count(self) -> int:
        label = self.page.get_by_text(MAPPED_FILTER).first
        expect(label).to_be_visible(timeout=PAGE_TIMEOUT_MS)
        found = MAPPED_FILTER.search(label.inner_text())
        return int(found.group(1)) if found else 0

    def has_rows(self) -> bool:
        return self._body_rows.count() > 0

    def ask_to_upload(self) -> ConfirmDialog:
        self.upload_button.click()
        return ConfirmDialog(self.page)

    def ask_to_unmap(self) -> ConfirmDialog:
        self.unmap_button.click()
        return ConfirmDialog(self.page)

    def ask_to_hide_first_row(self) -> ConfirmDialog:
        self._body_rows.first.get_by_role("link").last.click()
        return ConfirmDialog(self.page)

    def edit(self, product: str) -> "StoreItemEditWindow":
        self._row(product).get_by_title(EDIT_TITLE).click()
        window = StoreItemEditWindow(self.page)
        window.expect_open()
        return window

    def _row(self, product: str) -> Locator:
        cell = self.page.get_by_role("cell", name=product, exact=True)
        return self._body_rows.filter(has=cell)

    @property
    def _body_rows(self) -> Locator:
        # Why CSS: the header row also has role row; only tbody holds the items.
        return self.page.locator("tbody").get_by_role("row")


class StoreItemEditWindow(BasePage):
    """`OnlineStoreImageEdit` as "Edit Product" opens it: the sale price field is captioned with the Store
    Setting's Rate Selection (`ItemList/OnlineStoreImageEdit.html:41-48`) and prefilled with that rate
    (`OnlineStoreImageEdit.ts:363`; `OnlineStoreProductList.component.ts:284, 318`)."""

    def expect_open(self) -> None:
        expect(self._price).to_be_visible(timeout=PAGE_TIMEOUT_MS)

    def price_caption(self) -> str:
        return self._price_group.locator(".label").inner_text().strip()

    def price(self) -> Decimal:
        return Decimal(self._price.input_value().replace(",", ""))

    @property
    def _price(self) -> Locator:
        # Why CSS: the caption is a div, not a label tied to the input; the input's id is the only handle.
        return self.page.get_by_role("dialog").locator("#price")

    @property
    def _price_group(self) -> Locator:
        # Why CSS: the caption sits in the same plain .form-group div as the input (`.html:41-48`).
        return self.page.locator(".form-group").filter(has=self._price)
