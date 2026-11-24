"""Purchase > Quotation: a price offer from a supplier. It posts no stock and can be pulled into an order."""

from pages.purchase.documents import messages
from pages.purchase.documents.navigation import PurchaseScreen
from pages.purchase.documents.order_page import PurchaseOrderPage


class PurchaseQuotationPage(PurchaseOrderPage):
    screen = PurchaseScreen.QUOTATION
    number_label = "Quotation No."
    saved_message = messages.QUOTATION_SAVED
