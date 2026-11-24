"""One product line of a purchase document, read from the ProductDetails sheet of the phase-1 workbook."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from decimal import Decimal
from enum import Enum

from test_data.document_cases import DocumentCase

ZERO = Decimal(0)
STANDARD_EXPIRY = 46478  # the expiry the workbook gives its standard line
Row = Mapping[str, str | None]


class DiscountColumn(Enum):
    """Grid column ids of the four per-line discount fields."""

    DISCOUNT_1 = "discount1"
    DISCOUNT_2 = "discount2"
    VOLUME_1 = "volumediscount"
    VOLUME_2 = "volumediscount2"


SHEET_COLUMNS = {
    DiscountColumn.DISCOUNT_1: "discount_1",
    DiscountColumn.DISCOUNT_2: "discount_2",
    DiscountColumn.VOLUME_1: "vol_discount_1",
    DiscountColumn.VOLUME_2: "vol_discount_2",
}


@dataclass(frozen=True)
class PurchaseLineItem:
    product: str
    quantity: Decimal
    free: Decimal = ZERO
    rate: Decimal = ZERO
    expiry_serial: int | None = None
    batch: str = ""
    discounts: dict[DiscountColumn, Decimal] = field(default_factory=dict)

    @classmethod
    def from_row(cls, row: Row) -> PurchaseLineItem:
        expiry = _text(row, "exp_date")
        return cls(
            product=_text(row, "product_name"),
            quantity=_decimal(_text(row, "product_qty")),
            free=_decimal(_text(row, "product_free")),
            rate=_decimal(_text(row, "product_rate")),
            expiry_serial=int(Decimal(expiry)) if expiry else None,
            discounts={column: _decimal(_text(row, name)) for column, name in SHEET_COLUMNS.items()},
        )

    def with_batch(self, batch: str) -> PurchaseLineItem:
        return replace(self, batch=batch)

    def discount(self, column: DiscountColumn) -> Decimal:
        return self.discounts.get(column, ZERO)


def line_items_for(case: DocumentCase) -> list[PurchaseLineItem]:
    return [PurchaseLineItem.from_row(row) for row in case.line_items]


# Why not item "3": the QA tenant has no such item; this pharma item replaced it (user choice 2026-10-14).
STANDARD_ITEM_CODE = "44646015"


def standard_line() -> PurchaseLineItem:
    """The line the original uses for every document that is only a prerequisite (100 + 50 free at 100)."""
    return PurchaseLineItem(
        STANDARD_ITEM_CODE, Decimal(100), free=Decimal(50), rate=Decimal(100), expiry_serial=STANDARD_EXPIRY
    )


def _text(row: Row, column: str) -> str:
    return row.get(column) or ""


def _decimal(text: str) -> Decimal:
    return Decimal(text) if text else ZERO
