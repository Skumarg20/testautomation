"""Entering one purchase line up to the point where the Batch Details window opens."""

from pages.purchase.checklist.batch_details_window import BatchDetailsWindow
from pages.purchase.documents.bill_page import PurchaseBillEntryPage
from pages.purchase.documents.line_items import PurchaseLineItem


def open_batch_details(bills: PurchaseBillEntryPage, line: PurchaseLineItem) -> BatchDetailsWindow:
    """Product, new batch, expiry, quantity, free, rate and discounts, then the window (sheet row 33)."""
    grid = bills.grid
    grid.select_product(0, line.product)
    grid.type_batch(0, line.batch)
    grid.enter_expiry(0, line.expiry_serial)
    grid.enter_quantity(0, line.quantity)
    grid.enter_free(0, line.free)
    grid.enter_rate(0, line.rate)
    grid.enter_discounts(0, line)
    window = BatchDetailsWindow(bills.page)
    window.expect_open()
    return window
