"""Typed sale-document data built from the imported phase-1 cases, and the one place that resolves dates."""

import re
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

from test_data.document_cases import DocumentCase

TODAY = "today"
EXCEL_DAY_ZERO = date(1899, 12, 30)
YES = "Y"
NUMBER_PATTERN = re.compile(r"\d+\.?\d*")

# The Excel line-item sheet lists one row under a comma-separated tc_id; the importer does not split it,
# so these cases arrive without line items. The row's values are copied from the source (TD_SO_001).
SHARED_LINE_CASES = frozenset({"TC_SM_001", "TC_SM_002", "TC_SM_003", "TC_SM_004", "TC_SM_009"})
SHARED_LINE_SHEETS = frozenset({"order", "challan", "bill"})
# Why 44646015, not "3": the QA tenant has no item "3"; this item replaced it (user choice 2026-10-14).
SHARED_LINE = {"product_name": "44646015", "batch": "1231231123", "product_qty": "1", "product_price": "100"}


@dataclass(frozen=True)
class ProductLine:
    product: str
    batch: str
    quantity: Decimal
    price: Decimal
    discount1: Decimal = Decimal(0)
    discount2: Decimal = Decimal(0)
    volume_discount1: Decimal = Decimal(0)
    volume_discount2: Decimal = Decimal(0)

    @property
    def amount(self) -> Decimal:
        return self.quantity * self.price

    @property
    def has_sellable_quantity(self) -> bool:
        return self.quantity >= 1


@dataclass(frozen=True)
class Person:
    mobile: str
    name: str


@dataclass(frozen=True)
class DocumentRequest:
    party: str
    day: date
    patient: Person
    doctor: Person
    address: str
    bill_discount: Decimal
    lines: tuple[ProductLine, ...]

    @property
    def is_dated_today(self) -> bool:
        return self.day == resolve_date(TODAY)

    @property
    def has_unsellable_quantity(self) -> bool:
        return any(not line.has_sellable_quantity for line in self.lines)


def resolve_date(raw: str) -> date:
    """`today`, or an Excel day serial such as 46128, as a calendar date."""
    if raw == TODAY:
        return date.today()
    return EXCEL_DAY_ZERO + timedelta(days=int(Decimal(raw)))


def parse_decimal(text: str | None) -> Decimal:
    cleaned = (text or "").replace(",", "").strip()
    try:
        return Decimal(cleaned) if cleaned else Decimal(0)
    except InvalidOperation as error:
        raise ValueError(f"Not a number: {text!r}") from error


def last_number(text: str) -> Decimal:
    """The last figure in a text such as "Total Disc : 1,200.50"; zero when there is none."""
    figures = NUMBER_PATTERN.findall(text.replace(",", ""))
    return Decimal(figures[-1]) if figures else Decimal(0)


def plain(value: Decimal) -> str:
    return format(value, "f")


def wants(case: DocumentCase, flag: str) -> bool:
    """True when the case row asks for the follow-up action (a Y in that column)."""
    return case.inputs.get(flag, "") == YES


def uses_earlier_document(case: DocumentCase, column: str) -> bool:
    """The row names a template column (for example order_number) when the document is built from another."""
    return bool(case.inputs.get(column))


def request_from(case: DocumentCase) -> DocumentRequest:
    inputs = case.inputs
    return DocumentRequest(
        party=inputs.get("party_name", ""),
        day=resolve_date(inputs.get("date", TODAY)),
        patient=Person(inputs.get("patient_mobile", ""), inputs.get("patient_name", "")),
        doctor=Person(inputs.get("doctor_mobile", ""), inputs.get("doctor_name", "")),
        address=inputs.get("address", ""),
        bill_discount=parse_decimal(inputs.get("bill_discount")),
        lines=_lines_of(case),
    )


def _lines_of(case: DocumentCase) -> tuple[ProductLine, ...]:
    rows = case.line_items
    if not rows and case.sheet in SHARED_LINE_SHEETS and case.id in SHARED_LINE_CASES:
        rows = (SHARED_LINE,)
    return tuple(_line_from(row) for row in rows)


def _line_from(row: dict[str, str]) -> ProductLine:
    return ProductLine(
        product=row.get("product_name", ""),
        batch=row.get("batch", ""),
        quantity=parse_decimal(row.get("product_qty")),
        price=parse_decimal(row.get("product_price")),
        discount1=parse_decimal(row.get("discount_1")),
        discount2=parse_decimal(row.get("discount_2")),
        volume_discount1=parse_decimal(row.get("vol_discount_1")),
        volume_discount2=parse_decimal(row.get("vol_discount_2")),
    )
