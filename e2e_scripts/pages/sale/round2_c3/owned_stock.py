"""An item the test creates and stocks itself in the pharma company, so a sale rule can be tried on data whose
every figure is known (rates, M.R.P., expiry, minimum level, cess) without touching item 44646015.

Built through the screens a person would use: Master > Item > Create (item code, M.R.P., sale rate, optional
cess and minimum quantity), then one Purchase > Bill per batch (`RatedPurchaseBill` types the batch's M.R.P.
and sale rate A in the Batch Details window). The purchase makes the item master follow the last batch's rates
(sheet row 48 of the purchase checklist), so the master's sale rate A is written back afterwards to the value
the item was created with; that is what lets a test tell "rate from master" from "rate from batch".

`OwnedStock.dispose` removes what was made, last first: the purchase bills, then the item. A refusal to delete
the item is raised, naming the item, because a QA company must not collect orphans silently.

Selectors: the Create Item form's ids (`#txtItemCode`, `#txtcessper`, `#txtcessper2`, `#txtMinimumQuantity`)
are from `UI/Master/Item/createitem.component.html:40,356,373,2034`; the "Quantity" tab is the tab titled
'Quantity' (:2006). All are unverified live.
"""

from collections.abc import Callable
from dataclasses import dataclass, field, replace
from datetime import date, timedelta
from decimal import Decimal

from playwright.sync_api import Page, expect

from pages.dashboard_page import DashboardPage
from pages.inventory.create_item_page import CreateItemPage
from pages.inventory.item_list_page import ItemListPage
from pages.purchase.checklist.rated_bill import RatedPurchaseBill
from pages.purchase.documents.bill_page import PurchaseBillEntryPage
from pages.purchase.documents.dates import EXCEL_EPOCH, timestamp_label, todays_serial
from pages.purchase.documents.line_items import PurchaseLineItem
from pages.purchase.documents.seed_documents import seed_draft
from pages.sale.chemist.rate_validation_page import RateValidationPage
from test_data.models import ItemMasterSpec

DEFAULT_UNIT = "PCS"
DEFAULT_HSN = "12345678"
DEFAULT_TAX_CATEGORY = "GST Sale - 12%"
DEFAULT_COMPANY = "Others"
PURCHASE_RATE = Decimal(100)
MASTER_MRP = Decimal(200)
MASTER_RATE_A = Decimal(150)
BATCH_QUANTITY = Decimal(100)
QUANTITY_TAB = "Quantity"
CODE_MODULUS = 10**8


class OwnedItemNotRemovedError(AssertionError):
    def __init__(self, product: str, reason: str) -> None:
        super().__init__(f'QA item "{product}" is still in the pharma company ({reason}); delete it by hand')


def serial_in(days: int) -> int:
    """The day number (Excel serial) of `days` from today, the way the purchase bill's expiry is typed."""
    return (date.today() + timedelta(days=days) - EXCEL_EPOCH).days


@dataclass(frozen=True)
class BatchSpec:
    """One batch bought for the item. `expiry_in_days` is counted from today; `entry_days_ago` dates the
    purchase back (the first-in-first-out order of the batch window), which needs back billing allowed."""

    mrp: Decimal
    rate_a: Decimal
    expiry_in_days: int = 730
    quantity: Decimal = BATCH_QUANTITY
    free: Decimal = Decimal(0)
    name: str = field(default_factory=timestamp_label)
    entry_days_ago: int = 0


@dataclass(frozen=True)
class StockSpec:
    """The item and its batches. Optional master fields are only typed when given."""

    batches: tuple[BatchSpec, ...]
    master_mrp: Decimal = MASTER_MRP
    master_rate_a: Decimal = MASTER_RATE_A
    cess_percent: Decimal | None = None
    cess_per_unit: Decimal | None = None
    minimum_quantity: int | None = None
    with_barcode: bool = False


@dataclass(frozen=True)
class OwnedItem:
    code: str
    product: str
    spec: StockSpec

    @property
    def batch_names(self) -> list[str]:
        return [batch.name for batch in self.spec.batches]


class ExtendedCreateItem(CreateItemPage):
    """The Create Item form with the fields the sale rules need."""

    def type_code(self, code: str) -> None:
        self.page.locator("#txtItemCode").fill(code)

    def type_barcode(self, barcode: str) -> None:
        """Master-wise barcode (`#txtBarcode`, createitem.component.html:67); shown while Barcode Required is
        Master wise."""
        self.page.locator("#txtBarcode").fill(barcode)

    def type_cess(self, percent: Decimal | None, per_unit: Decimal | None) -> None:
        if percent is not None:
            self.page.locator("#txtcessper").fill(format(percent, "f"))
        if per_unit is not None:
            self.page.locator("#txtcessper2").fill(format(per_unit, "f"))

    def type_minimum_quantity(self, minimum: int | None) -> None:
        if minimum is None:
            return
        # Why CSS: the form's tabs are plain list items without a role (same locator as RateValidationPage).
        self.page.locator("tabs ul li").filter(has_text=QUANTITY_TAB).first.click()
        field_ = self.page.locator("#txtMinimumQuantity")
        expect(field_).to_be_visible()
        field_.fill(str(minimum))


class OwnedStock:
    """Creates and later removes one item with its batches in the pharma company."""

    def __init__(self, page: Page, run_id: str) -> None:
        self._page = page
        self._run_id = run_id
        self._purchases: list[str] = []
        self._items: list[str] = []
        self._counter = 0

    def create(self, spec: StockSpec) -> OwnedItem:
        self._counter += 1
        code = self._unique_code()
        product = f"QA-{self._run_id}-Stock{self._counter}"
        item = OwnedItem(code, product, spec)
        self._create_master(item)
        for batch in spec.batches:
            self._buy(item, batch)
        self._restore_master_rate(item)
        return item

    def dispose(self) -> None:
        """Purchase bills first (they hold the stock), then the items."""
        failures: list[str] = []
        for number in reversed(self._purchases):
            DashboardPage(self._page).open()
            PurchaseBillEntryPage(self._page).delete(number)
        self._purchases.clear()
        for product in reversed(self._items):
            DashboardPage(self._page).open()
            try:
                ItemListPage(self._page).open()
                if ItemListPage(self._page).has_item(product):
                    ItemListPage(self._page).delete(product)
            except AssertionError as refused:
                failures.append(f"{product}: {refused}")
        self._items.clear()
        if failures:
            raise OwnedItemNotRemovedError("; ".join(failures), "delete refused")

    def _unique_code(self) -> str:
        """A numeric code no other run shares: the run id is hexadecimal, the counter tells items apart."""
        return f"9{int(self._run_id, 16) % CODE_MODULUS:08d}{self._counter}"

    def _create_master(self, item: OwnedItem) -> None:
        spec = item.spec
        master = ItemMasterSpec(
            product=item.product,
            unit=DEFAULT_UNIT,
            hsn=DEFAULT_HSN,
            tax_category=DEFAULT_TAX_CATEGORY,
            gst_rate=Decimal(12),
            company=DEFAULT_COMPANY,
            mrp=spec.master_mrp,
            sale_rate=spec.master_rate_a,
        )
        form = ExtendedCreateItem(self._page)
        form.open()
        form.fill(master)
        form.type_code(item.code)
        if spec.with_barcode:
            form.type_barcode(item.code)
        form.type_cess(spec.cess_percent, spec.cess_per_unit)
        form.type_minimum_quantity(spec.minimum_quantity)
        form.save()
        form.expect_saved()
        form.decline_opening_stock()
        self._items.append(item.product)

    def _buy(self, item: OwnedItem, batch: BatchSpec) -> None:
        line = PurchaseLineItem(
            item.code,
            batch.quantity,
            free=batch.free,
            rate=PURCHASE_RATE,
            expiry_serial=serial_in(batch.expiry_in_days),
            batch=batch.name,
        )
        entry = todays_serial() - batch.entry_days_ago
        draft = replace(seed_draft(batch.name), lines=(line,), entry_date=entry, invoice_date=entry)
        number = RatedPurchaseBill(self._page, batch.mrp, batch.rate_a).create(draft)
        self._purchases.append(number)

    def _restore_master_rate(self, item: OwnedItem) -> None:
        """The purchase moved the master's sale rate A to the last batch's; the spec's value goes back."""
        DashboardPage(self._page).open()
        RateValidationPage(self._page).change_item_rate(item.product, "a", item.spec.master_rate_a)


StockFactory = Callable[[StockSpec], OwnedItem]
