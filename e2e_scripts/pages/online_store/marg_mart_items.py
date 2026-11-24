"""Marg Mart's "Manage Item" list (`Component/Online-Store/ItemList/OnlineStoreItemList.html`), OS-33.

Opened from the order dashboard in Marg Mart mode. Rows are a mat-table with a mat-checkbox each (`:137`);
"Upload Item" (`:12-24`) posts `Item/onlinestoredata` for the ticked rows, then uploads them to margmart.com
in lots (`OnlineStoreItemList.ts:376-420, 700-779`) and records the mapping with
`Item/UploadMargMartItemdata`.
The upload only starts when the session holds a "MargMartToken" (Marg Mart login). Both writes are stubbed by
the tests. Not seen live.
"""

from playwright.sync_api import Locator, expect

from pages.base_page import BasePage
from pages.purchase.documents.feedback import AppFeedback

PAGE_TIMEOUT_MS = 30_000


class MargMartItemList(BasePage):
    def expect_open(self) -> None:
        expect(self.upload_button).to_be_visible(timeout=PAGE_TIMEOUT_MS)
        AppFeedback(self.page).wait_for_loader()

    @property
    def upload_button(self) -> Locator:
        return self.page.get_by_role("button", name="Upload Item")

    def tick(self, product: str) -> None:
        row = self.page.get_by_role("row").filter(has=self.page.get_by_text(product, exact=True))
        row.get_by_role("checkbox").check()

    def upload(self) -> None:
        self.upload_button.click()
