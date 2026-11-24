"""Sale > Stock Issue: stock sent out to a party without a bill (a different screen from Material Issue).

Factory `SaleStockIssueFactory` (Model/TransactionFactory/sale.stockissue.factory.ts): heading "Stock Issue",
party group Sundry Debtors / Cash (:34), number label "Challan No." (:42), save message "Stock Issue" +
`AlertMsg.BillSaved` (:31). The amount column is not calculated for a stock issue
(processout.transaction.component.ts:6603), so the price cell is not visited. Menu text and cells are
unverified live.
"""

from pages.sale.documents.challan import SaleChallan
from pages.sale.documents.document_requests import ProductLine


class StockIssue(SaleChallan):
    menu = ("Sale", "Stock Issue")
    number_label = "Challan No."

    def enter_price(self, row: int, line: ProductLine) -> None:
        """A stock issue carries quantities only."""
