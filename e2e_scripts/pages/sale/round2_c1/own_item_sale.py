"""Selling a test-made item (picked by its generated code, in its own batch) on the pharma sale bill."""

from decimal import Decimal

from pages.inventory.round2_c1.own_item import OwnItem
from pages.sale.manual.pharma_bill import PharmaBill


def start_with_item(bill: PharmaBill, item: OwnItem, quantity: Decimal) -> None:
    """New bill to Cash Account; product, batch and quantity of `item` on the first row."""
    bill.start()
    bill.document.grid.select_product(0, item.code)
    bill.document.grid.choose_batch(0, item.batch)
    bill.document.grid.enter_quantity(0, quantity)
