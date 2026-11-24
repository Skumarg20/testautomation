"""The transaction lock an approved data sync request puts on a company (J35 DS-20, DS-21).

While `DatasyncSetting.isDataSyncEnable` is true, Create/F2 on the sale bill list warns "Transaction locked
after datasync" and opens nothing (`processout.list.component.ts:1278-1280`); the bill screen refuses
F10/F3/Del/C the same way (`processout.transaction.component.ts:15094-15096`). Text: `global.ts:19714`.
DRAFT: written from the Angular source, not seen live.
"""

from playwright.sync_api import expect

from pages.base_page import BasePage
from pages.sale.documents.bill import SaleBillDocument

LOCKED = "Transaction locked after datasync"
CREATE = "Create/F2"
WARNING_TIMEOUT_MS = 15_000
# The new bill form shows its number under this label; the list does not.
BILL_FORM_MARK = SaleBillDocument.number_label


class TransactionLock(BasePage):
    def try_new_sale_bill(self) -> None:
        bill = SaleBillDocument(self.page)
        bill.screen.open_menu(bill.menu)
        bill.screen.press_button(CREATE)

    def expect_locked(self) -> None:
        expect(self.page.get_by_text(LOCKED).first).to_be_visible(timeout=WARNING_TIMEOUT_MS)
        expect(self.page.get_by_text(BILL_FORM_MARK, exact=True)).to_have_count(0)

    def expect_bill_form_opened(self) -> None:
        expect(self.page.get_by_text(BILL_FORM_MARK, exact=True).first).to_be_visible(
            timeout=WARNING_TIMEOUT_MS
        )
        expect(self.page.get_by_text(LOCKED)).to_have_count(0)
