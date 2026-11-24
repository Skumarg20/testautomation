"""Test data of the J40 manufacturing journey: own items, one BOM and the stock figures of the pack.

The figures are the worked example of `scenarios/manufacturing-module.md` (data line above the table):
RM-A 100 and RM-B 50 opening, BOM "FG 1 = RM-A 2 + RM-B 1", issue for 10 sets, receive 10.
"""

from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum

from test_data.factory import DataFactory
from test_data.models import ItemMasterSpec

PRODUCTION_DEPARTMENT = "Production Department"
DATE_FORMAT = "%d-%m-%Y"
ONE_DAY = timedelta(days=1)

RM_A_OPENING = Decimal(100)
RM_B_OPENING = Decimal(50)
FINISHED_OPENING = Decimal(0)
BOM_QUANTITY = Decimal(1)
RM_A_PER_SET = Decimal(2)
RM_B_PER_SET = Decimal(1)
SETS_ISSUED = Decimal(10)
SETS_RECEIVED_IN_PART = Decimal(7)
SETS_MORE_THAN_ISSUED = Decimal(11)

BIG_OPENING = Decimal(80)
BIG_CONVERSION = Decimal(1)
# Not in the pack: the small items get stock of their own so Many to One can take them off.
SMALL_OPENING = Decimal(5)
SMALL_ONE_CONVERSION = Decimal(1)
SMALL_FIVE_CONVERSION = Decimal(5)
SMALLS_PER_ONE_TO_MANY = Decimal(5)
SMALL_FIVE_PER_MANY_TO_ONE = Decimal(1)

# MF-04: by-product 1 per set; the pack's example Additional Cost of 100.
BY_PRODUCT_PER_SET = Decimal(1)
ADDITIONAL_COST = Decimal(100)
# MF-06: the BOM Name input has minlength 4 and maxlength 50 (billofmaterialmaster.html:26).
BOM_NAME_MIN_LENGTH = 4
BOM_NAME_MAX_LENGTH = 50
# MF-13: a finished item sold in tens; the BOM saves Qty x Conversion (billofmaterialmaster.ts:698).
FINISHED_CONVERSION = Decimal(10)
# MF-17: more RM-A than its opening stock of 100, so the issue would take it to -20.
RM_A_BEYOND_STOCK = Decimal(120)
# MF-21: BOM "FG 2 = RM-A 4 + RM-B 2"; 1 set is below the BOM Qty, 3 sets give a factor of 1.5.
BOM_OF_TWO_QUANTITY = Decimal(2)
SETS_BELOW_BOM_QUANTITY = Decimal(1)
SETS_NOT_A_MULTIPLE = Decimal(3)
# MF-26: the issue changed from 10 to 15 sets.
SETS_ISSUED_AFTER_CHANGE = Decimal(15)
# MF-28: Production Planning for 10, then for 15.
PLANNED_SETS = Decimal(10)
PLANNED_SETS_CHANGED = Decimal(15)
# MF-32: the purchase of BIG that comes before the One to Many on the same day.
BIG_PURCHASED = Decimal(10)


@dataclass(frozen=True)
class StockItem:
    """An item of this run, the main-store quantity it opens with, and its Conversion (None: left as is)."""

    spec: ItemMasterSpec
    opening: Decimal
    conversion: Decimal | None = None

    @property
    def product(self) -> str:
        return self.spec.product


@dataclass(frozen=True)
class Component:
    item: ItemMasterSpec
    quantity_per_set: Decimal

    def for_sets(self, sets: Decimal) -> Decimal:
        return self.quantity_per_set * sets


@dataclass(frozen=True)
class BomSpec:
    name: str
    finished: ItemMasterSpec
    quantity: Decimal
    raw_materials: tuple[Component, ...]
    by_products: tuple[Component, ...] = ()

    def needed_for(self, component: Component, sets: Decimal) -> Decimal:
        """What a receive of `sets` finished items consumes: BOM qty x (sets / BOM Qty), as
        billofmaterialdetails.ts:215-219 computes it."""
        return component.quantity_per_set * sets / self.quantity


class ConversionDirection(Enum):
    ONE_TO_MANY = "One to many"
    MANY_TO_ONE = "Many to one"


@dataclass(frozen=True)
class ConversionItems:
    big: StockItem
    small_one: StockItem
    small_five: StockItem

    def all(self) -> tuple[StockItem, ...]:
        return (self.big, self.small_one, self.small_five)


@dataclass(frozen=True)
class ConversionLine:
    item: StockItem
    quantity: Decimal

    @property
    def big_item_quantity(self) -> Decimal:
        """How much of the big item this line stands for: quantity x the small item's Conversion."""
        return self.quantity * (self.item.conversion or Decimal(1))


@dataclass(frozen=True)
class ConversionEntry:
    direction: ConversionDirection
    big: StockItem
    lines: tuple[ConversionLine, ...]

    @property
    def big_item_quantity(self) -> Decimal:
        return sum((line.big_item_quantity for line in self.lines), Decimal(0))


class ManufacturingData:
    def __init__(self, data: DataFactory, run_id: str) -> None:
        self._data = data
        self._run_id = run_id

    def item(self, label: str) -> ItemMasterSpec:
        """A run-unique goods item, for example QA-<run>-RM-A, so no other session moves its stock."""
        return replace(self._data.item_master(), product=f"QA-{self._run_id}-{label}")

    def bom(self, finished: ItemMasterSpec, raw_a: ItemMasterSpec, raw_b: ItemMasterSpec) -> BomSpec:
        return BomSpec(
            name=f"BOM-{self._run_id}",
            finished=finished,
            quantity=BOM_QUANTITY,
            raw_materials=(Component(raw_a, RM_A_PER_SET), Component(raw_b, RM_B_PER_SET)),
        )

    def bom_of_two(self, finished: ItemMasterSpec, raw_a: ItemMasterSpec, raw_b: ItemMasterSpec) -> BomSpec:
        """MF-21: "FG 2 = RM-A 4 + RM-B 2", the pack's BOM for two finished items."""
        sets = BOM_OF_TWO_QUANTITY
        return BomSpec(
            name=f"BOM2-{self._run_id}",
            finished=finished,
            quantity=sets,
            raw_materials=(Component(raw_a, RM_A_PER_SET * sets), Component(raw_b, RM_B_PER_SET * sets)),
        )

    def name_of_length(self, length: int) -> str:
        """A run-unique BOM name padded with "X" to exactly `length` characters (MF-06)."""
        return f"B{self._run_id}".ljust(length, "X")[:length]

    @staticmethod
    def with_by_product(bom: BomSpec, by_product: ItemMasterSpec) -> BomSpec:
        return replace(bom, by_products=(Component(by_product, BY_PRODUCT_PER_SET),))

    @staticmethod
    def same_name_other_case(bom: BomSpec, finished: ItemMasterSpec) -> BomSpec:
        """A second BOM whose name differs only by case and spaces (MF-07), for another finished item."""
        return replace(bom, name=f"  {bom.name.lower()} ", finished=finished)

    @staticmethod
    def without_raw_materials(bom: BomSpec) -> BomSpec:
        return replace(bom, raw_materials=())


def one_to_many(items: ConversionItems) -> ConversionEntry:
    """Pack MF-30: BIG into S1 x 5 and S5 x 5, which takes 5 x 1 + 5 x 5 = 30 off BIG."""
    lines = (
        ConversionLine(items.small_one, SMALLS_PER_ONE_TO_MANY),
        ConversionLine(items.small_five, SMALLS_PER_ONE_TO_MANY),
    )
    return ConversionEntry(ConversionDirection.ONE_TO_MANY, items.big, lines)


def many_to_one(items: ConversionItems) -> ConversionEntry:
    """Pack MF-31: S1 x 5 and S5 x 1 into BIG, which adds 5 x 1 + 1 x 5 = 10 to BIG."""
    lines = (
        ConversionLine(items.small_one, SMALLS_PER_ONE_TO_MANY),
        ConversionLine(items.small_five, SMALL_FIVE_PER_MANY_TO_ONE),
    )
    return ConversionEntry(ConversionDirection.MANY_TO_ONE, items.big, lines)


@dataclass(frozen=True)
class OutsideBooksYear:
    """MF-36: the day before the books year starts and the day after it ends, as dd-MM-yyyy."""

    day_before: str
    day_after: str

    @classmethod
    def around(cls, books_period: str) -> "OutsideBooksYear":
        """From the header's "01-04-2026 to 31-03-2027"."""
        start_text, end_text = (part.strip() for part in books_period.split(" to "))
        start = datetime.strptime(start_text, DATE_FORMAT).date()
        end = datetime.strptime(end_text, DATE_FORMAT).date()
        return cls(
            (start - ONE_DAY).strftime(DATE_FORMAT),
            (end + ONE_DAY).strftime(DATE_FORMAT),
        )


@dataclass(frozen=True)
class SameDayEntries:
    """MF-32: the purchase of BIG and the One to Many saved after it on the same day."""

    big_product: str
    purchase_number: str
    conversion_number: str
