"""Everything a stock-based sale test needs, in one object (a test may take at most three arguments).

`make_stock` builds an item with batches, `customer` is a ledger made for the test, `options` holds Sale Bill
Setting fields and `hold_choice` holds Dashboard Control Room options (both are put back at teardown),
`bill` drives the sale bill and `bills` saves and later deletes the test's bills.
"""

from dataclasses import dataclass

from pages.sale.manual.option_settings import HeldOptions
from pages.sale.round2_c3.control_room_choice import HoldChoice
from pages.sale.round2_c3.owned_stock import StockFactory
from pages.sale.round2_c3.stock_bill import PartyBills, StockBill, StockLine


@dataclass(frozen=True)
class SaleDesk:
    make_stock: StockFactory
    customer: str
    options: HeldOptions
    hold_choice: HoldChoice
    bill: StockBill
    bills: PartyBills

    def sell(self, line: StockLine) -> None:
        """A new bill for the test's customer with `line` as its first row; the rate is the app's."""
        self.bill.start_for(self.customer)
        self.bill.pick(0, line)
