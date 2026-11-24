"""Fixtures for the online-store journey (J37): the company's own Online Store on GANE29.

Orchestrator decision 2026-10-12: only the in-house store mode is automated; Marg Mart orders come from
margmart.com and stay manual. Orders are seeded through the app's own API (`pages/online_store/order_api.py`)
under QA-<run_id> names; the API has no delete, so they stay behind (spec N2).

Creating a store is permanent (no delete), so no fixture creates one (spec N1). The create-store tests need a
company without a store, the dashboard tests one with an own Online Store: each skips, naming the scenario and
the question, when GANE29 is in the other state. The Control Room "Store Setting" row is tenant-wide: the
fixture holds it at Yes and restores it, and the rate a test changes is put back (xdist group
"chemist-tenant").

Writes that would create a store, register on Marg Mart or change a store catalogue are stubbed
(`pages/online_store/store_endpoints.py`): the guard fixtures arm a `SendGuard` on the test's page before the
guarded screen opens, so a write no stub answers is aborted and fails the test. Only the tests marked
`permanent` let such a write through.
"""

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import replace

import pytest
from playwright.sync_api import Page

from config.settings import Account
from pages.company_switch_page import GARMENTS_COMPANY, PHARMA_COMPANY, CompanySwitchPage
from pages.components.send_guard import SendGuard
from pages.dashboard_page import DashboardPage
from pages.inventory.create_item_page import CreateItemPage
from pages.inventory.item_list_page import ItemListPage
from pages.masters.ledger_form import LedgerForm
from pages.online_store.create_store import CreateStorePage
from pages.online_store.entry import OnlineStoreEntry, StoreLanding
from pages.online_store.order_api import OnlineStoreApi
from pages.online_store.order_dashboard import OrderDashboard
from pages.online_store.store_endpoints import CATALOGUE_WRITES, STORE_CREATION_WRITES
from pages.online_store.store_items import StoreItemList
from pages.online_store.store_setting import StoreSettingWindow
from pages.purchase.documents.feedback import appears_within
from pages.sale.documents.bill import SaleBillDocument
from pages.settings.control_room_state import ControlRoomState
from pages.settings.control_room_switch import SwitchValue, switch_held
from test_data.factory import DataFactory
from test_data.masters import MasterDataFactory, PartyLedgerSpec
from test_data.models import ItemMasterSpec
from test_data.online_store import (
    PENDING,
    ConvertedSale,
    ListedOrder,
    OnlineStoreData,
    OrderLine,
    SeededOrder,
)

ONLINE_STORE_ACCOUNT: Account = "chemist"
STORE_SETTING_SWITCH = SwitchValue("Store Setting", "Yes")
NO_STORE_NEEDED = (
    f"OS-01/OS-03 need a company without any store, but {GARMENTS_COMPANY} has one. "
    "Which company keeps no store (spec N1)?"
)
OWN_STORE_NEEDED = (
    f"{GARMENTS_COMPANY} has no own Online Store and creating one is permanent. "
    "Which company gets one, created once by hand (spec N1)?"
)
OTHER_COMPANY = PHARMA_COMPANY
OTHER_STORE_NEEDED = (
    f"OS-28/OS-29: needs a second company with an own Online Store; {OTHER_COMPANY} has none (spec N1)"
)
MARG_MART_NEEDED = "OS-33: needs a company with a Marg Mart store; the dashboard opened in own-store mode"

MODE_PROBE_MS = 5_000

SeedOrder = Callable[[SeededOrder], None]


@pytest.fixture
def store_tab(page_as: Callable[[Account], Page]) -> Page:
    """The test's page, not yet navigated (so a guard can be armed first)."""
    return page_as(ONLINE_STORE_ACCOUNT)


@pytest.fixture
def creation_guard(store_tab: Page) -> Iterator[SendGuard]:
    """Aborts store creation and Marg Mart registration writes no stub answers."""
    yield from _guarded(store_tab, SendGuard(store_tab, STORE_CREATION_WRITES))


@pytest.fixture
def catalogue_guard(store_tab: Page) -> Iterator[SendGuard]:
    """Aborts store catalogue writes (own store and Marg Mart) no stub answers."""
    yield from _guarded(store_tab, SendGuard(store_tab, CATALOGUE_WRITES))


@pytest.fixture
def store_page(store_tab: Page) -> Page:
    DashboardPage(store_tab).open()
    # The login's company is shared state that other suites switch.
    CompanySwitchPage(store_tab).ensure_company(GARMENTS_COMPANY)
    return store_tab


@pytest.fixture
def create_store_page(store_page: Page) -> CreateStorePage:
    if OnlineStoreEntry(store_page).open() is not StoreLanding.CREATE_STORE:
        pytest.skip(NO_STORE_NEEDED)
    return CreateStorePage(store_page)


@pytest.fixture
def guarded_store_form(creation_guard: SendGuard, create_store_page: CreateStorePage) -> CreateStorePage:
    """The create-store form, opened, on a page whose creation writes are guarded."""
    create_store_page.start()
    return create_store_page


@pytest.fixture
def store_api(store_page: Page) -> OnlineStoreApi:
    """Opens the own store's dashboard and keeps the headers of its API call for seeding."""
    return OnlineStoreApi.captured_while(store_page, lambda: _open_own_store(store_page))


@pytest.fixture
def dashboard(store_page: Page, store_api: OnlineStoreApi) -> OrderDashboard:
    return OrderDashboard(store_page)


@pytest.fixture
def shop(run_id: str) -> OnlineStoreData:
    return OnlineStoreData(run_id)


@pytest.fixture
def seed(store_page: Page, store_api: OnlineStoreApi) -> SeedOrder:
    """Submits an order, then opens the dashboard again so the grid loads it (with the default filters)."""

    def submit(order: SeededOrder) -> None:
        store_api.submit_order(order)
        _open_own_store(store_page)

    return submit


@pytest.fixture
def seed_order_with_status(seed: SeedOrder, shop: OnlineStoreData) -> Callable[[str], SeededOrder]:
    """Seeds an order with the given status and a line on no real item (enough for the grid)."""

    def seed_with(status: str) -> SeededOrder:
        order = shop.order(status, shop.unmapped_line())
        seed(order)
        return order

    return seed_with


@pytest.fixture
def seed_priced_order(seed: SeedOrder, shop: OnlineStoreData) -> Callable[[OrderLine], SeededOrder]:
    """Seeds a Pending order with one given line (OS-26, OS-27)."""

    def seed_line(line: OrderLine) -> SeededOrder:
        order = shop.order(PENDING, line)
        seed(order)
        return order

    return seed_line


@pytest.fixture
def seeded_pending_order(seed_order_with_status: Callable[[str], SeededOrder]) -> SeededOrder:
    return seed_order_with_status(PENDING)


@pytest.fixture
def listed_pending_order(store_api: OnlineStoreApi, seeded_pending_order: SeededOrder) -> ListedOrder:
    return ListedOrder(seeded_pending_order, store_api.order_link_id(seeded_pending_order.order_no))


@pytest.fixture
def store_setting(store_page: Page) -> Iterator[StoreSettingWindow]:
    """The Control Room "Store Setting" row held at Yes, so its Configure button shows; restored after."""
    dashboard_page = DashboardPage(store_page)
    with switch_held(ControlRoomState(store_page), STORE_SETTING_SWITCH, dashboard_page.open):
        dashboard_page.open()
        yield StoreSettingWindow(store_page)


@pytest.fixture
def rate_restored(store_page: Page, store_setting: StoreSettingWindow) -> Iterator[StoreSettingWindow]:
    """The tenant's Rate Selection is read first and written back after the test if it changed."""
    original = _saved_rate(store_setting)
    yield store_setting
    DashboardPage(store_page).open()
    if _saved_rate(store_setting) != original:
        _save_rate(store_setting, original)


@pytest.fixture
def own_item(store_page: Page, data: DataFactory) -> Iterator[ItemMasterSpec]:
    """This test's item (Master > Item, no opening stock); deleted afterwards when the app allows it."""
    with _created_item(store_page, data.item_master()) as item:
        yield item


@pytest.fixture
def second_own_item(store_page: Page, own_item: ItemMasterSpec) -> Iterator[ItemMasterSpec]:
    """A second item of this test, for a multi-line order (OS-38)."""
    with _created_item(store_page, replace(own_item, product=f"{own_item.product}-2")) as item:
        yield item


@pytest.fixture
def own_item_link_id(store_api: OnlineStoreApi, own_item: ItemMasterSpec) -> str:
    return store_api.item_link_id(own_item.product)


@pytest.fixture
def own_item_line(own_item_link_id: str, own_item: ItemMasterSpec) -> OrderLine:
    """An order line on our own item (its linkid as productid), so a conversion can bill it."""
    return OnlineStoreData.line_for_item(own_item_link_id, own_item.product)


@pytest.fixture
def convertible_order(seed: SeedOrder, shop: OnlineStoreData, own_item_line: OrderLine) -> SeededOrder:
    order = shop.order(PENDING, own_item_line)
    seed(order)
    return order


@pytest.fixture
def second_item_line(store_api: OnlineStoreApi, second_own_item: ItemMasterSpec) -> OrderLine:
    return OnlineStoreData.line_for_item(
        store_api.item_link_id(second_own_item.product), second_own_item.product
    )


@pytest.fixture
def two_item_lines(own_item_line: OrderLine, second_item_line: OrderLine) -> tuple[OrderLine, ...]:
    return (own_item_line, second_item_line)


@pytest.fixture
def two_line_order(
    seed: SeedOrder, shop: OnlineStoreData, two_item_lines: tuple[OrderLine, ...]
) -> SeededOrder:
    """A Pending order with a line on each of this test's two items (OS-38)."""
    order = shop.order_with_lines(PENDING, two_item_lines)
    seed(order)
    return order


@pytest.fixture
def bill_cleanup(store_page: Page) -> Iterator[list[str]]:
    """Bill numbers a test saved; each is deleted afterwards."""
    numbers: list[str] = []
    yield numbers
    for number in numbers:
        SaleBillDocument(store_page).delete(number)


@pytest.fixture
def converted_sale(
    dashboard: OrderDashboard, convertible_order: SeededOrder, bill_cleanup: list[str]
) -> ConvertedSale:
    """The order converted and its sale bill saved (OS-19); the bill is deleted afterwards."""
    dashboard.show_every_vendor()
    dashboard.convert(convertible_order.order_no)
    bill = SaleBillDocument(dashboard.page)
    number = bill.document_number()
    bill.save()
    bill.expect_saved()
    bill_cleanup.append(number)
    _open_own_store(dashboard.page)
    return ConvertedSale(convertible_order, number)


@pytest.fixture
def converted_order(converted_sale: ConvertedSale) -> SeededOrder:
    return converted_sale.order


@pytest.fixture
def save_converted_bill(store_page: Page, bill_cleanup: list[str]) -> Callable[[], None]:
    """Saves the open converted bill (deleted after the test) and goes back to the order dashboard."""

    def save() -> None:
        bill = SaleBillDocument(store_page)
        bill_cleanup.append(bill.document_number())
        bill.save()
        bill.expect_saved()
        _open_own_store(store_page)

    return save


@pytest.fixture
def seed_order_from_mobile(
    seed: SeedOrder, shop: OnlineStoreData, own_item_line: OrderLine
) -> Callable[[str], SeededOrder]:
    """Seeds a convertible Pending order whose customer gave the given mobile (OS-24, OS-25)."""

    def seed_from(mobile: str) -> SeededOrder:
        order = shop.order_from_mobile(own_item_line, mobile)
        seed(order)
        return order

    return seed_from


@pytest.fixture
def known_customer(store_page: Page, run_id: str) -> PartyLedgerSpec:
    """A customer ledger of this test with its own mobile number (OS-25); left behind under its QA name."""
    customer = MasterDataFactory(run_id).customer()
    form = LedgerForm(store_page)
    form.open_new()
    form.enter_party(customer)
    form.save()
    form.expect_saved()
    return customer


@pytest.fixture
def choose_store_rate(rate_restored: StoreSettingWindow) -> Callable[[str], None]:
    """Saves a Rate Selection for the tenant; `rate_restored` puts the original back."""
    return lambda caption: _save_rate(rate_restored, caption)


@pytest.fixture
def open_item_list(store_page: Page) -> Callable[[], StoreItemList]:
    """Opens the own store's Manage Item list (after a test changed what it should show)."""

    def open_list() -> StoreItemList:
        _open_own_store(store_page)
        OrderDashboard(store_page).open_manage_items()
        items = StoreItemList(store_page)
        items.expect_open()
        return items

    return open_list


@pytest.fixture
def guarded_item_list(
    catalogue_guard: SendGuard, open_item_list: Callable[[], StoreItemList]
) -> StoreItemList:
    """The own store's item list on a page whose catalogue writes are guarded."""
    return open_item_list()


@pytest.fixture
def marg_mart_dashboard(catalogue_guard: SendGuard, store_page: Page) -> OrderDashboard:
    """The dashboard in Marg Mart mode; skips when the company has no Marg Mart store."""
    if OnlineStoreEntry(store_page).open() is StoreLanding.CREATE_STORE:
        pytest.skip(MARG_MART_NEEDED)
    dashboard = OrderDashboard(store_page)
    dashboard.expect_open()
    if not appears_within(dashboard.marg_mart_switch_button, MODE_PROBE_MS):
        pytest.skip(MARG_MART_NEEDED)
    return dashboard


@pytest.fixture
def open_other_company_store(store_page: Page) -> Iterator[Callable[[], OnlineStoreApi]]:
    """Switches to a second company and opens its own store (OS-28/29); switches back afterwards."""

    def open_other() -> OnlineStoreApi:
        DashboardPage(store_page).open()
        CompanySwitchPage(store_page).ensure_company(OTHER_COMPANY)
        if OnlineStoreEntry(store_page).open() is StoreLanding.CREATE_STORE:
            pytest.skip(OTHER_STORE_NEEDED)
        return OnlineStoreApi.captured_while(store_page, lambda: OrderDashboard(store_page).show_own_store())

    yield open_other
    DashboardPage(store_page).open()
    CompanySwitchPage(store_page).ensure_company(GARMENTS_COMPANY)


@pytest.fixture
def reopen_own_store(store_page: Page) -> Callable[[], OrderDashboard]:
    """Back on GANE29's own store dashboard, e.g. after a test looked at another company."""

    def reopen() -> OrderDashboard:
        DashboardPage(store_page).open()
        CompanySwitchPage(store_page).ensure_company(GARMENTS_COMPANY)
        _open_own_store(store_page)
        return OrderDashboard(store_page)

    return reopen


def _guarded(page: Page, guard: SendGuard) -> Iterator[SendGuard]:
    guard.arm()
    yield guard
    guard.expect_nothing_sent()


@contextmanager
def _created_item(page: Page, item: ItemMasterSpec) -> Iterator[ItemMasterSpec]:
    screen = CreateItemPage(page)
    screen.open()
    screen.fill(item)
    screen.save()
    screen.expect_saved()
    screen.decline_opening_stock()
    yield item
    DashboardPage(page).open()
    item_list = ItemListPage(page)
    item_list.open()
    if item_list.has_item(item.product):
        item_list.delete(item.product)


def _open_own_store(page: Page) -> None:
    if OnlineStoreEntry(page).open() is StoreLanding.CREATE_STORE:
        pytest.skip(OWN_STORE_NEEDED)
    OrderDashboard(page).show_own_store()


def _saved_rate(window: StoreSettingWindow) -> str:
    window.open()
    rate = window.chosen_rate()
    window.close_with_cross()
    window.leave_control_room()
    return rate


def _save_rate(window: StoreSettingWindow, caption: str) -> None:
    window.open()
    window.choose_rate(caption)
    window.close_with_cross()
    window.save_control_room()
