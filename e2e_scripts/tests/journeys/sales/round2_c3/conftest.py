"""Fixtures for the round-2 sale-checklist tests (part C3): the pharma company's sale bill, held settings,
and stock and customers the test creates for itself.

Teardown runs in the reverse of the order a test lists its fixtures, so a test names them in the order of
need: `stock_factory` first (its purchase bills can only go once no sale bill takes the stock), then
`customer_bills` (or `saved_bills`), then `bill`. The open bill is then left first, the Control Room switches
are put back (they need the dashboard), saved bills are deleted (they need the list), and last the
customer, the purchase bills and the item are removed.
"""

from collections.abc import Callable, Iterator
from contextlib import ExitStack

import pytest
from playwright.sync_api import Page

from config.settings import Account
from pages.dashboard_page import DashboardPage
from pages.sale.checklist.bill_screen import ChecklistBill
from pages.sale.documents.flows import open_sales_page
from pages.sale.manual.option_settings import HeldOptions
from pages.sale.manual.pharma_bill import PharmaBill
from pages.sale.manual.saved_bills import SavedBills
from pages.sale.round2_c3.configure_settings import ConfigureSettings
from pages.sale.round2_c3.control_room_choice import Choice, ControlRoomChoices, HoldChoice, choice_held
from pages.sale.round2_c3.owned_stock import OwnedStock, StockFactory
from pages.sale.round2_c3.sale_desk import SaleDesk
from pages.sale.round2_c3.stock_bill import OwnedCustomer, PartyBills, StockBill


@pytest.fixture
def pharma_page(page_as: Callable[[Account], Page]) -> Page:
    return open_sales_page(page_as)


@pytest.fixture
def stock_factory(pharma_page: Page, run_id: str) -> Iterator[StockFactory]:
    """`stock_factory(spec)` makes an item with its batches; whatever was made is removed at the end."""
    stock = OwnedStock(pharma_page, run_id)
    yield stock.create
    stock.dispose()


@pytest.fixture
def owned_customer(pharma_page: Page, run_id: str) -> Iterator[str]:
    """The name of a customer ledger made for this test (no special rate class, not the cash party)."""
    customer = OwnedCustomer(pharma_page, run_id)
    try:
        yield customer.create()
    finally:
        customer.remove()


@pytest.fixture
def customer_bills(pharma_page: Page, owned_customer: str) -> Iterator[PartyBills]:
    """Bills saved to the owned customer; every one is deleted afterwards."""
    bills = PartyBills(pharma_page, owned_customer)
    yield bills
    bills.delete_all()


@pytest.fixture
def saved_bills(pharma_page: Page) -> Iterator[SavedBills]:
    """Bills saved to Cash Account through `saved_bills.save(bill)`; every one is deleted afterwards."""
    saved = SavedBills(pharma_page)
    yield saved
    saved.delete_all()


@pytest.fixture
def control_room(pharma_page: Page) -> Iterator[HoldChoice]:
    """Holds a Dashboard Control Room option at a choice for the test; each is read first, put back after."""
    stack = ExitStack()
    choices = ControlRoomChoices(pharma_page)
    dashboard = DashboardPage(pharma_page)

    def hold(choice: Choice) -> None:
        dashboard.open()
        stack.enter_context(choice_held(choices, choice, dashboard.open))

    yield hold
    stack.close()


@pytest.fixture
def bill(pharma_page: Page, control_room: HoldChoice) -> Iterator[PharmaBill]:
    new_bill = PharmaBill(pharma_page)
    yield new_bill
    if new_bill.is_open():
        new_bill.leave_without_saving()


@pytest.fixture
def stock_bill(bill: PharmaBill) -> StockBill:
    return StockBill(bill)


@pytest.fixture
def options(pharma_page: Page, bill: PharmaBill) -> Iterator[HeldOptions]:
    """Sale Bill Setting window options held for the test; put back before the bill is left."""
    held = HeldOptions(ConfigureSettings(pharma_page), bill.document.open_new, bill.leave_without_saving)
    yield held
    held.close()


@pytest.fixture
def checklist_bill(pharma_page: Page, control_room: HoldChoice) -> Iterator[ChecklistBill]:
    """The checklist's view of a sale bill (header fields, focus); the test opens it. Left unsaved."""
    screen = ChecklistBill(pharma_page)
    yield screen
    if screen.is_open:
        screen.leave()


@pytest.fixture
def desk(request: pytest.FixtureRequest) -> SaleDesk:
    """Stock, a customer, held settings and the bill, set up in the order their teardown needs (see the
    module doc): asked for one by one, because a test may take three fixtures at most."""
    stock = request.getfixturevalue("stock_factory")
    customer = request.getfixturevalue("owned_customer")
    bills = request.getfixturevalue("customer_bills")
    choices = request.getfixturevalue("control_room")
    options = request.getfixturevalue("options")
    bill = request.getfixturevalue("stock_bill")
    return SaleDesk(stock, customer, options, choices, bill, bills)
