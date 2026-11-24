"""Sale > Quotation, written like `SaleOrder`: it posts no stock and is pulled into an order, challan or bill.

The screen is the sale bill component with `TransactionMapper.SaleQuotation` (processout:12639 treats
quotation and order alike: no stock check, no master update), and the bill's party window offers
"Pending Quotation" (`getLoadPendingQuotation`, processout:6035). Menu text "Sale > Quotation" and the
number label are taken from the order screen's pattern and are unverified live.
"""

from pages.sale.documents.order import SaleOrder


class SaleQuotation(SaleOrder):
    menu = ("Sale", "Quotation")
    number_label = "Quotation No."
