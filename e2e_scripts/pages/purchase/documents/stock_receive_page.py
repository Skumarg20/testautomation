"""Purchase > Stock Receive: goods taken in against a supplier invoice; like a bill without a payment step."""

from pages.purchase.documents import messages
from pages.purchase.documents.bill_page import PurchaseBillEntryPage
from pages.purchase.documents.navigation import PurchaseScreen


class StockReceivePage(PurchaseBillEntryPage):
    screen = PurchaseScreen.STOCK_RECEIVE
    saved_message = messages.STOCK_RECEIVE_SAVED
