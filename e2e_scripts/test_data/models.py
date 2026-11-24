"""Typed test-data records ported from the original suite's TypeScript types."""

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum

HOME_STATE_CODE = "07"  # the garments company's own state; confirm against its GSTIN before trusting


class HeaderTag(str, Enum):
    BASE = "base"
    FUTURE_DATE_ALLOWED = "future_date_allowed"
    BACK_DATE_ALLOWED = "back_date_allowed"
    FUTURE_DATE_NOT_ALLOWED = "future_date_not_allowed"
    BACK_DATE_NOT_ALLOWED = "back_date_not_allowed"
    SPECIAL_DISCOUNT = "special_discount"
    MASTER_DISCOUNT = "master_discount"
    AGENCY_DISCOUNT = "agency_discount"
    PARTY_WISE_AGENCY_DISCOUNT = "party_wise_agency_discount"
    NO_PATIENT_OR_DOCTOR = "no_patient_or_doctor"
    STORE = "store"
    CONVERSION = "conversion"
    ALL_FIELDS = "all_fields"
    BILL_BY_BILL_SALE = "bill_by_bill_sale"
    ON_ACCOUNT_SALE = "on_account_sale"


@dataclass(frozen=True)
class BillHeader:
    """Sale-bill header values. `date_offset_days` is relative to today (-1 = yesterday)."""

    party_name: str | None = None
    patient_name: str | None = None
    doctor: str | None = None
    store: str | None = None
    sale_type: str | None = None
    mr: str | None = None
    address: str | None = None
    date_offset_days: int | None = None


@dataclass(frozen=True)
class ItemEntry:
    """One row typed into the sale-bill grid. Needs a barcode, itemcode or description."""

    barcode: int | None = None
    itemcode: int | None = None
    description: str | None = None
    quantity: int | None = None
    expiry_type: str | None = None
    free: int | None = None
    sale_rate: float | None = None
    discount1: float | None = None
    discount2: float | None = None
    volume_discount1: float | None = None
    volume_discount2: float | None = None


@dataclass(frozen=True)
class SaleItem:
    """An item that exists in the QA tenant's stock, with the facts the tests rely on."""

    description: str
    barcode: int | None = None
    itemcode: int | None = None
    batch_barcode: int | None = None
    multiple_barcode: int | None = None
    expiry: str | None = None
    quantity: int | None = None
    gst_percent: int | None = None

    def by_barcode(self) -> ItemEntry:
        return ItemEntry(barcode=self.barcode, quantity=self.quantity)

    def by_item_code(self) -> ItemEntry:
        return ItemEntry(itemcode=self.itemcode, quantity=self.quantity)

    def by_description(self) -> ItemEntry:
        return ItemEntry(description=self.description, quantity=self.quantity)

    def by_batch_barcode(self) -> ItemEntry:
        return ItemEntry(barcode=self.batch_barcode, quantity=self.quantity)

    def entry(self) -> ItemEntry:
        """Uses the first identifier the item has: barcode, then item code, then description."""
        if self.barcode is not None:
            return self.by_barcode()
        if self.itemcode is not None:
            return self.by_item_code()
        return self.by_description()


@dataclass(frozen=True)
class PartySpec:
    """A customer or supplier to create. `gstin` is None for an unregistered party."""

    name: str
    state_code: str
    gstin: str | None = None

    @property
    def registered(self) -> bool:
        return self.gstin is not None

    @property
    def intra_state(self) -> bool:
        return self.state_code == HOME_STATE_CODE


@dataclass(frozen=True)
class ItemSpec:
    """An item to create for one GST slab. Rates are percent, prices are rupees, both Decimal."""

    description: str
    gst_rate: Decimal
    price: Decimal


@dataclass(frozen=True)
class ItemMasterSpec:
    """An item typed into Create Item. Unit, HSN, tax category and company name existing masters."""

    product: str
    unit: str
    hsn: str
    tax_category: str
    gst_rate: Decimal
    company: str
    mrp: Decimal
    sale_rate: Decimal

    @property
    def half_gst_rate(self) -> Decimal:
        """CGST and SGST each carry half of the item's GST rate."""
        return self.gst_rate / 2


@dataclass(frozen=True)
class PurchaseLine:
    item: ItemSpec
    quantity: int
    rate: Decimal

    @property
    def taxable_value(self) -> Decimal:
        return self.rate * self.quantity


@dataclass(frozen=True)
class PurchaseBillSpec:
    supplier: PartySpec
    invoice_number: str
    lines: tuple[PurchaseLine, ...]

    @property
    def taxable_value(self) -> Decimal:
        return sum((line.taxable_value for line in self.lines), Decimal(0))
