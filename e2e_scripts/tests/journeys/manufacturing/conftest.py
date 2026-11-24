"""Fixtures for the manufacturing journey (J40): BOM, Material Issue/Receive and Conversion on GANE29.

The screens appear only when their Control Room switch is Yes: "Bill Of Material(BOM)" (S.No 367) and
"One To Many & Many To One required?" (S.No 21), both No on GANE29 when seen on 2026-10-12. Decision N1
(2026-10-12): each test turns the switch it needs on and puts the original value back in teardown, even
when the test fails, so the tests run in xdist group "chemist-tenant" (CLAUDE.md rule 0). If the menu is
still missing with the switch on, the test fails: that is no longer a missing precondition.

Teardown runs in reverse dependency order: receive, issue, BOM, finished item, then the switch. Items with
opening stock stay behind under the run id: the app refuses to delete them (specs/inventory.md, D4).
"""

from collections.abc import Callable, Iterator
from decimal import Decimal

import pytest
from playwright.sync_api import Page

from config.settings import Account
from pages.accounting.waiting import appears_within
from pages.company_switch_page import GARMENTS_COMPANY, PHARMA_COMPANY, CompanySwitchPage
from pages.dashboard_page import DashboardPage
from pages.inventory.item_list_page import ItemListPage
from pages.manufacturing.bom_master import BomMasterForm, BomMasterList
from pages.manufacturing.items import save_service_item, save_stock_item
from pages.manufacturing.menu import ManufacturingMenu, ManufacturingScreen
from pages.manufacturing.purchase_in import PurchaseIn, delete_purchase, save_purchase
from pages.manufacturing.stock_vouchers import (
    CONVERSION_VOUCHERS,
    MaterialIssue,
    MaterialReceive,
    OneToMany,
    RawMaterialsConsumedWindow,
    SavedVoucher,
    StockUpdateWindow,
)
from pages.purchase.garments.purchase_bill_page import GarmentsPurchaseLine
from pages.settings.control_room import YesNo
from pages.settings.control_room_state import ControlRoomState
from pages.settings.control_room_switch import SwitchValue, switch_held
from pages.settings.stock_negative_setting import STOCK_NEGATIVE_ALLOWED, StockNegativeSetting
from pages.stock.item_stock_balance import ItemStockBalance
from test_data.factory import DataFactory
from test_data.manufacturing import (
    BIG_CONVERSION,
    BIG_OPENING,
    BIG_PURCHASED,
    FINISHED_CONVERSION,
    FINISHED_OPENING,
    RM_A_BEYOND_STOCK,
    RM_A_OPENING,
    RM_B_OPENING,
    SETS_ISSUED,
    SMALL_FIVE_CONVERSION,
    SMALL_ONE_CONVERSION,
    SMALL_OPENING,
    BomSpec,
    ConversionEntry,
    ConversionItems,
    ManufacturingData,
    SameDayEntries,
    StockItem,
    one_to_many,
)
from test_data.models import ItemMasterSpec

MANUFACTURING_ACCOUNT: Account = "chemist"
# MF-34: the suite's limited login (config/settings.py Role); the plan assumes it lacks "MaterialIssue" (N8).
LIMITED_ACCOUNT: Account = "operator"
COMPANY_LOOKUP_MS = 10_000
INVOICE_DIGITS = 8
BOM_SWITCH = SwitchValue("Bill Of Material(BOM)", "Yes")
CONVERSION_SWITCH = SwitchValue("One To Many & Many To One required?", "Yes")


class ScreenNotOfferedError(AssertionError):
    def __init__(self, screen: ManufacturingScreen, switch: SwitchValue) -> None:
        super().__init__(
            f"Stock Management > {screen.submenu} is missing on {GARMENTS_COMPANY} although Control Room "
            f'"{switch.name}" was set to {switch.wanted} (MF-01 / MF-29)'
        )


ReceiveSets = Callable[[Decimal], RawMaterialsConsumedWindow]


@pytest.fixture
def manufacturing_page(page_as: Callable[[Account], Page]) -> Page:
    page = page_as(MANUFACTURING_ACCOUNT)
    DashboardPage(page).open()
    # The login's company is shared state that other suites switch; the plan was observed on this one.
    CompanySwitchPage(page).ensure_company(GARMENTS_COMPANY)
    return page


@pytest.fixture
def bom_page(manufacturing_page: Page) -> Iterator[Page]:
    """Bill of Materials switched on for this test; the tenant's original value is put back after (N1)."""
    yield from _with_switch_on(manufacturing_page, BOM_SWITCH, ManufacturingScreen.MATERIAL_MASTER)


@pytest.fixture
def conversion_page(manufacturing_page: Page) -> Iterator[Page]:
    """One To Many & Many To One switched on for this test; the original value is put back after (N1)."""
    yield from _with_switch_on(manufacturing_page, CONVERSION_SWITCH, ManufacturingScreen.ONE_TO_MANY)


@pytest.fixture
def conversion_stock(conversion_page: Page) -> ItemStockBalance:
    return ItemStockBalance(conversion_page)


@pytest.fixture
def mf_data(data: DataFactory, run_id: str) -> ManufacturingData:
    return ManufacturingData(data, run_id)


@pytest.fixture
def bom_list(bom_page: Page) -> BomMasterList:
    """The Material Master list; tests open it once their data is saved (saving items leaves the list)."""
    return BomMasterList(bom_page)


@pytest.fixture
def stock(bom_page: Page) -> ItemStockBalance:
    return ItemStockBalance(bom_page)


@pytest.fixture
def finished_item(bom_page: Page, mf_data: ManufacturingData) -> Iterator[StockItem]:
    item = StockItem(mf_data.item("FG"), FINISHED_OPENING)
    save_stock_item(bom_page, item)
    yield item
    _delete_item(bom_page, item)


@pytest.fixture
def raw_materials(bom_page: Page, mf_data: ManufacturingData) -> tuple[StockItem, StockItem]:
    """RM-A and RM-B with the pack's opening stock, so no other session can change their figures."""
    raw_a = StockItem(mf_data.item("RM-A"), RM_A_OPENING)
    raw_b = StockItem(mf_data.item("RM-B"), RM_B_OPENING)
    save_stock_item(bom_page, raw_a)
    save_stock_item(bom_page, raw_b)
    return raw_a, raw_b


@pytest.fixture
def pack_bom(
    mf_data: ManufacturingData,
    finished_item: StockItem,
    raw_materials: tuple[StockItem, StockItem],
) -> BomSpec:
    """The pack's BOM: FG 1 = RM-A 2 + RM-B 1; not saved."""
    raw_a, raw_b = raw_materials
    return mf_data.bom(finished_item.spec, raw_a.spec, raw_b.spec)


@pytest.fixture
def other_finished_item(bom_page: Page, mf_data: ManufacturingData) -> Iterator[StockItem]:
    item = StockItem(mf_data.item("FG-2"), FINISHED_OPENING)
    save_stock_item(bom_page, item)
    yield item
    _delete_item(bom_page, item)


@pytest.fixture
def pack_bom_removed_afterwards(bom_page: Page, pack_bom: BomSpec) -> Iterator[BomSpec]:
    """The pack's BOM, deleted after the test if the test saved it and did not delete it itself."""
    yield pack_bom
    _remove_bom_if_listed(bom_page, pack_bom.name)


@pytest.fixture
def saved_bom(bom_page: Page, pack_bom_removed_afterwards: BomSpec) -> BomSpec:
    _save_bom(bom_page, pack_bom_removed_afterwards)
    return pack_bom_removed_afterwards


@pytest.fixture
def material_issue(bom_page: Page, saved_bom: BomSpec) -> Iterator[MaterialIssue]:
    """Material Issue of SETS_ISSUED sets of the BOM's raw materials to Production Department (MF-14)."""
    issue = MaterialIssue(bom_page)
    issue.open_new()
    for row, component in enumerate(saved_bom.raw_materials):
        issue.add_line(row, component.item.product, component.for_sets(SETS_ISSUED))
    number = issue.number()
    issue.save()
    issue.expect_saved()
    yield issue
    issue.delete(number)


@pytest.fixture
def start_receive(bom_page: Page, saved_bom: BomSpec, material_issue: MaterialIssue) -> ReceiveSets:
    """Starts a Material Receive of n finished items and returns the Raw Materials Consumed window."""

    def start(sets: Decimal) -> RawMaterialsConsumedWindow:
        receive = MaterialReceive(bom_page)
        receive.open_new()
        receive.add_line(0, saved_bom.finished.product, sets)
        return RawMaterialsConsumedWindow(bom_page)

    return start


@pytest.fixture
def receive(start_receive: ReceiveSets, bom_page: Page) -> Iterator[Callable[[Decimal], None]]:
    """Receives n finished items (accept the window, save); the receives are deleted afterwards (MF-18)."""
    voucher = MaterialReceive(bom_page)
    numbers: list[str] = []

    def receive_sets(sets: Decimal) -> None:
        start_receive(sets).accept()
        numbers.append(voucher.number())
        voucher.save()
        voucher.expect_saved()

    yield receive_sets
    for number in reversed(numbers):
        voucher.delete(number)


@pytest.fixture
def conversion_items(conversion_page: Page, mf_data: ManufacturingData) -> ConversionItems:
    """BIG (Conversion 1, opening 80), S1 (Conversion 1) and S5 (Conversion 5), each with SMALL_OPENING."""
    items = ConversionItems(
        big=StockItem(mf_data.item("BIG"), BIG_OPENING, BIG_CONVERSION),
        small_one=StockItem(mf_data.item("S1"), SMALL_OPENING, SMALL_ONE_CONVERSION),
        small_five=StockItem(mf_data.item("S5"), SMALL_OPENING, SMALL_FIVE_CONVERSION),
    )
    for item in items.all():
        save_stock_item(conversion_page, item)
    return items


@pytest.fixture
def convert(conversion_page: Page) -> Iterator[Callable[[ConversionEntry], str]]:
    """Saves a One to Many or Many to One entry, accepts the Stock Update window and returns its number;
    the entries are deleted afterwards."""
    saved: list[tuple[OneToMany, str]] = []

    def save(entry: ConversionEntry) -> str:
        voucher = CONVERSION_VOUCHERS[entry.direction](conversion_page)
        voucher.open_new()
        voucher.choose_big_item(entry.big.product)
        for row, line in enumerate(entry.lines):
            voucher.add_line(row, line.item.product, line.quantity)
        number = voucher.number()
        saved.append((voucher, number))
        voucher.save()
        StockUpdateWindow(conversion_page).accept()
        voucher.expect_saved()
        return number

    yield save
    for voucher, number in reversed(saved):
        voucher.delete(number)


@pytest.fixture
def bom_editor(bom_list: BomMasterList) -> BomMasterForm:
    """A new, empty Material Master. Ask for it after the item fixtures: saving an item leaves the list."""
    bom_list.open()
    bom_list.create()
    return BomMasterForm(bom_list.page)


@pytest.fixture
def bom_and_conversion_page(bom_page: Page) -> Iterator[Page]:
    """Both switches on (MF-13): the item form shows Conversion only with Control Room field 4505 on
    (createitem.component.ts:863-864), which the plan takes to be the conversion switch."""
    yield from _with_switch_on(bom_page, CONVERSION_SWITCH, ManufacturingScreen.ONE_TO_MANY)


@pytest.fixture
def service_item(bom_page: Page, mf_data: ManufacturingData) -> Iterator[ItemMasterSpec]:
    spec = mf_data.item("SVC")
    save_service_item(bom_page, spec)
    yield spec
    _delete_item(bom_page, StockItem(spec, FINISHED_OPENING))


@pytest.fixture
def by_product_item(bom_page: Page, mf_data: ManufacturingData) -> Iterator[StockItem]:
    item = StockItem(mf_data.item("BY"), FINISHED_OPENING)
    save_stock_item(bom_page, item)
    yield item
    _delete_item(bom_page, item)


@pytest.fixture
def finished_item_in_tens(bom_and_conversion_page: Page, mf_data: ManufacturingData) -> Iterator[StockItem]:
    item = StockItem(mf_data.item("FG-10"), FINISHED_OPENING, FINISHED_CONVERSION)
    save_stock_item(bom_and_conversion_page, item)
    yield item
    _delete_item(bom_and_conversion_page, item)


class RunBoms:
    """This run's BOMs over its own RM-A and RM-B, for any finished item."""

    def __init__(self, mf_data: ManufacturingData, raw_materials: tuple[StockItem, StockItem]) -> None:
        self._data = mf_data
        self._raw_a, self._raw_b = raw_materials

    def pack(self, finished: StockItem) -> BomSpec:
        return self._data.bom(finished.spec, self._raw_a.spec, self._raw_b.spec)

    def of_two(self, finished: StockItem) -> BomSpec:
        return self._data.bom_of_two(finished.spec, self._raw_a.spec, self._raw_b.spec)


@pytest.fixture
def run_boms(mf_data: ManufacturingData, raw_materials: tuple[StockItem, StockItem]) -> RunBoms:
    return RunBoms(mf_data, raw_materials)


@pytest.fixture
def bom_in_tens(
    bom_and_conversion_page: Page, run_boms: RunBoms, finished_item_in_tens: StockItem
) -> Iterator[BomSpec]:
    """The pack's BOM for a finished item with Conversion 10; removed afterwards if it was saved."""
    bom = run_boms.pack(finished_item_in_tens)
    yield bom
    _remove_bom_if_listed(bom_and_conversion_page, bom.name)


@pytest.fixture
def saved_bom_of_two(bom_page: Page, run_boms: RunBoms, finished_item: StockItem) -> Iterator[BomSpec]:
    """MF-21: "FG 2 = RM-A 4 + RM-B 2", saved; removed afterwards."""
    bom = run_boms.of_two(finished_item)
    _save_bom(bom_page, bom)
    yield bom
    _remove_bom_if_listed(bom_page, bom.name)


@pytest.fixture
def receive_window(bom_page: Page) -> Callable[[BomSpec, Decimal], RawMaterialsConsumedWindow]:
    """Starts a Material Receive of n finished items of any BOM, whether or not anything was issued."""

    def start(bom: BomSpec, sets: Decimal) -> RawMaterialsConsumedWindow:
        receive = MaterialReceive(bom_page)
        receive.open_new()
        receive.add_line(0, bom.finished.product, sets)
        return RawMaterialsConsumedWindow(bom_page)

    return start


@pytest.fixture
def own_issue(bom_page: Page, saved_bom: BomSpec) -> Iterator[SavedVoucher]:
    """A Material Issue of SETS_ISSUED sets the test may change or delete itself (MF-26)."""
    issue = MaterialIssue(bom_page)
    issue.open_new()
    for row, component in enumerate(saved_bom.raw_materials):
        issue.add_line(row, component.item.product, component.for_sets(SETS_ISSUED))
    saved = SavedVoucher(issue, issue.number())
    issue.save()
    issue.expect_saved()
    yield saved
    saved.delete_if_left()


@pytest.fixture
def own_receive(bom_page: Page, saved_bom: BomSpec, material_issue: MaterialIssue) -> Iterator[SavedVoucher]:
    """A Material Receive of SETS_ISSUED finished items the test may change or delete itself (MF-26)."""
    receive = MaterialReceive(bom_page)
    receive.open_new()
    receive.add_line(0, saved_bom.finished.product, SETS_ISSUED)
    RawMaterialsConsumedWindow(bom_page).accept()
    saved = SavedVoucher(receive, receive.number())
    receive.save()
    receive.expect_saved()
    yield saved
    saved.delete_if_left()


@pytest.fixture
def negative_stock_refused(bom_page: Page) -> Iterator[Page]:
    """MF-17: Control Room "Stock Negative allowed" held at No for the test, the original put back after."""
    yield from _with_stock_negative(bom_page, "No")


@pytest.fixture
def negative_stock_allowed(bom_page: Page) -> Iterator[Page]:
    yield from _with_stock_negative(bom_page, "Yes")


@pytest.fixture
def issue_beyond_stock(
    raw_materials: tuple[StockItem, StockItem], negative_stock_allowed: Page
) -> Iterator[SavedVoucher]:
    """MF-17: a Material Issue of RM-A 120 against its stock of 100, saved with negative stock allowed."""
    issue = MaterialIssue(negative_stock_allowed)
    issue.open_new()
    issue.add_line(0, raw_materials[0].product, RM_A_BEYOND_STOCK)
    saved = SavedVoucher(issue, issue.number())
    issue.save()
    issue.expect_saved()
    yield saved
    saved.delete_if_left()


@pytest.fixture
def in_second_company(bom_page: Page, saved_bom: BomSpec) -> Iterator[Page]:
    """MF-35: the login switched to the pharma company after the BOM was saved on GANE29, and back after."""
    companies = CompanySwitchPage(bom_page)
    companies.switch_company(PHARMA_COMPANY)
    companies.expect_header_company(PHARMA_COMPANY)
    yield bom_page
    companies.ensure_company(GARMENTS_COMPANY)


@pytest.fixture
def operator_page(page_as: Callable[[Account], Page], bom_page: Page) -> Page:
    """MF-34: the operator login on GANE29 while the BOM switch is on; skips if it cannot reach GANE29."""
    page = page_as(LIMITED_ACCOUNT)
    DashboardPage(page).open()
    companies = CompanySwitchPage(page)
    if not companies.current_company().startswith(GARMENTS_COMPANY):
        _switch_or_skip(companies)
    return page


@pytest.fixture
def big_purchased(
    conversion_page: Page, conversion_items: ConversionItems, run_id: str
) -> Iterator[PurchaseIn]:
    """MF-32: a purchase of BIG +10, saved before the conversion of the same day; deleted afterwards."""
    purchase = PurchaseIn(
        invoice_number=_digits_of(run_id),
        line=GarmentsPurchaseLine(
            conversion_items.big.product, BIG_PURCHASED, conversion_items.big.spec.sale_rate
        ),
    )
    save_purchase(conversion_page, purchase)
    yield purchase
    delete_purchase(conversion_page, purchase)


@pytest.fixture
def one_to_many_after_purchase(
    big_purchased: PurchaseIn, conversion_items: ConversionItems, convert: Callable[[ConversionEntry], str]
) -> SameDayEntries:
    conversion_number = convert(one_to_many(conversion_items))
    return SameDayEntries(conversion_items.big.product, big_purchased.invoice_number, conversion_number)


def _remove_bom_if_listed(page: Page, name: str) -> None:
    bom_list = BomMasterList(page)
    bom_list.open()
    if bom_list.has(name):
        bom_list.delete(name)
        bom_list.expect_deleted()


def _save_bom(page: Page, bom: BomSpec) -> None:
    bom_list = BomMasterList(page)
    bom_list.open()
    bom_list.create()
    form = BomMasterForm(page)
    form.fill(bom)
    form.save()
    form.expect_saved()


def _with_switch_on(page: Page, switch: SwitchValue, screen: ManufacturingScreen) -> Iterator[Page]:
    dashboard = DashboardPage(page)
    # The restore starts from the dashboard: a test may leave a voucher or a window open.
    with switch_held(ControlRoomState(page), switch, dashboard.open):
        dashboard.open()  # a fresh load, so the menu is built from the saved setting
        _expect_offered(page, screen, switch)
        yield page


def _with_stock_negative(page: Page, value: YesNo) -> Iterator[Page]:
    dashboard = DashboardPage(page)
    switch = SwitchValue(STOCK_NEGATIVE_ALLOWED, value)
    with switch_held(StockNegativeSetting(page), switch, dashboard.open):
        dashboard.open()
        yield page


def _switch_or_skip(companies: CompanySwitchPage) -> None:
    companies.open()
    companies.search(GARMENTS_COMPANY)
    listed = companies.page.get_by_role("row").filter(has_text=GARMENTS_COMPANY)
    if not appears_within(listed.first, COMPANY_LOOKUP_MS):
        pytest.skip(f"MF-34: needs the {LIMITED_ACCOUNT} login to reach {GARMENTS_COMPANY}")
    companies.switch_company(GARMENTS_COMPANY)


def _digits_of(run_id: str) -> str:
    """The garments purchase window takes a digits-only invoice number (purchase_bill_page.py:58)."""
    digits = "".join(character for character in run_id if character.isdigit())
    return digits[-INVOICE_DIGITS:] or "1"


def _expect_offered(page: Page, screen: ManufacturingScreen, switch: SwitchValue) -> None:
    if not ManufacturingMenu(page).offers(screen):
        raise ScreenNotOfferedError(screen, switch)


def _delete_item(page: Page, item: StockItem) -> None:
    item_list = ItemListPage(page)
    item_list.open()
    item_list.delete(item.product)
