"""A test's working area in the pharma company: buy batches, save sale documents, read stock.

Everything it creates is registered for deletion in the reverse order, so a sale document is deleted
before the purchase that brought its batch in. A document's type and number make its undo key.
"""

from decimal import Decimal

from playwright.sync_api import Page

from pages.purchase.documents.bill_page import PurchaseBillEntryPage
from pages.purchase.documents.seed_documents import SeededBill, seed_bill, seed_draft
from pages.sale.documents.bill import SaleBillDocument
from pages.sale.documents.challan import SaleChallan
from pages.sale.documents.document import SaleDocument
from pages.sale.documents.document_requests import DocumentRequest
from pages.sale.documents.returns import SaleReturn
from pages.stock.sale_impact import documents
from pages.stock.sale_impact.batch_list import BatchList
from pages.stock.sale_impact.cleanup import Cleanup
from pages.stock.sale_impact.purchases import buy_batch_expiring_in
from pages.stock.sale_impact.return_challan import SaleReturnChallan
from pages.stock.sale_impact.stock_issue import StockIssue
from pages.stock.sale_impact.stock_views import StockViews, views_of


class Shop:
    def __init__(self, page: Page, cleanup: Cleanup) -> None:
        self.page = page
        self._cleanup = cleanup

    def buy_batch(self) -> str:
        """Buys a new batch of the test item (100 + 50 free); returns its name."""
        return self._bought(seed_bill(self.page)).batch

    def buy_batch_expiring_in(self, days: int) -> str:
        return self._bought(buy_batch_expiring_in(self.page, days)).batch

    def buy_again_under_the_name(self, batch: str) -> None:
        number = PurchaseBillEntryPage(self.page).create(seed_draft(batch))
        self._undo_purchase(number)

    def challan(self, request: DocumentRequest) -> str:
        return self._kept(SaleChallan(self.page), documents.save_challan(self.page, request))

    def bill(self, request: DocumentRequest) -> str:
        return self._kept(SaleBillDocument(self.page), documents.save_bill(self.page, request))

    def bill_from_challan(self, challan: str, request: DocumentRequest) -> str:
        number = documents.save_bill_from_challan(self.page, challan, request)
        key = _key(SaleBillDocument, number)
        self._cleanup.add(key, lambda: SaleBillDocument(self.page).delete_with_challan(number))
        return number

    def stock_issue(self, request: DocumentRequest) -> str:
        return self._kept(StockIssue(self.page), documents.save_stock_issue(self.page, request))

    def return_challan(self, request: DocumentRequest) -> str:
        return self._kept(SaleReturnChallan(self.page), documents.save_return_challan(self.page, request))

    def manual_return(self, request: DocumentRequest) -> str:
        return self._kept(SaleReturn(self.page), documents.save_manual_return(self.page, request))

    def return_to_empty_batch(self, request: DocumentRequest) -> str:
        return self._kept(SaleReturn(self.page), documents.save_return_of_empty_batch(self.page, request))

    def sell_everything(self, batch: str) -> Decimal:
        """One challan for all that is in the batch; returns the quantity sold."""
        in_stock = BatchList(self.page).quantity_of(documents.PRODUCT, batch)
        self.challan(documents.sale_request(batch, in_stock))
        return in_stock

    def delete_challan(self, number: str) -> None:
        SaleChallan(self.page).delete(number)
        self._cleanup.discard(_key(SaleChallan, number))

    def delete_stock_issue(self, number: str) -> None:
        StockIssue(self.page).delete(number)
        self._cleanup.discard(_key(StockIssue, number))

    def views(self, batch: str) -> StockViews:
        return views_of(self.page, batch)

    def _bought(self, bought: SeededBill) -> SeededBill:
        self._undo_purchase(bought.number)
        return bought

    def _undo_purchase(self, number: str) -> None:
        key = _key(PurchaseBillEntryPage, number)
        self._cleanup.add(key, lambda: PurchaseBillEntryPage(self.page).delete(number))

    def _kept(self, document: SaleDocument, number: str) -> str:
        """Registers the document's deletion and hands its number back."""
        self._cleanup.add(_key(type(document), number), lambda: document.delete(number))
        return number


def _key(document_type: type, number: str) -> str:
    """Numbers repeat between document types, so the type is part of the undo key."""
    return f"{document_type.__name__}:{number}"
