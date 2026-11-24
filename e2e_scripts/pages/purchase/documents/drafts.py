"""Everything a test enters on a purchase document, as one value."""

from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal
from enum import Enum

from pages.purchase.documents.dates import resolve_date, todays_serial
from pages.purchase.documents.line_items import ZERO, PurchaseLineItem, line_items_for
from test_data.document_cases import DocumentCase

TEMPLATE_PLACEHOLDERS = {"order": "order number", "challan": "challan number", "bill": "bill number"}


class ReturnMode(Enum):
    """How a purchase return picks its products: from one bill, or by hand."""

    SINGLE = "Single"
    MANUAL = "Manual"


class Refusal(Enum):
    """Why a NEGATIVE sheet row is expected to be refused."""

    NO_PARTY = "no party"
    BACK_DATE = "back date"
    NO_PRODUCT = "no product"
    ZERO_QUANTITY = "zero quantity"


class UnrefusableDraftError(ValueError):
    def __init__(self, draft: PurchaseDraft) -> None:
        super().__init__(f"Nothing in this draft should be refused: {draft}")


@dataclass(frozen=True)
class PurchaseDraft:
    party: str
    entry_date: int
    lines: tuple[PurchaseLineItem, ...] = ()
    bill_discount: Decimal = ZERO
    invoice_date: int | None = None
    order_number: str = ""
    challan_number: str = ""
    quotation_number: str = ""
    bill_number: str = ""
    return_mode: ReturnMode = ReturnMode.MANUAL

    @classmethod
    def from_case(cls, case: DocumentCase) -> PurchaseDraft:
        inputs = case.inputs
        invoice_date = inputs.get("invoice_date")
        return cls(
            party=inputs.get("party_name", ""),
            entry_date=resolve_date(inputs["date"]),
            lines=tuple(line_items_for(case)),
            bill_discount=Decimal(inputs.get("bill_discount") or 0),
            invoice_date=resolve_date(invoice_date) if invoice_date else None,
            return_mode=ReturnMode(inputs.get("return_type") or ReturnMode.MANUAL.value),
        )

    def expected_refusal(self) -> Refusal:
        """The first bad value of the draft, in the order the screen meets them."""
        if not self.party:
            return Refusal.NO_PARTY
        if self.entry_date < todays_serial():
            return Refusal.BACK_DATE
        if not self.lines or any(not line.product for line in self.lines):
            return Refusal.NO_PRODUCT
        if any(line.quantity < 1 for line in self.lines):
            return Refusal.ZERO_QUANTITY
        raise UnrefusableDraftError(self)

    def with_batch(self, batch: str) -> PurchaseDraft:
        return replace(self, lines=tuple(line.with_batch(batch) for line in self.lines))

    def with_lines(self, lines: tuple[PurchaseLineItem, ...]) -> PurchaseDraft:
        return replace(self, lines=lines)

    def from_order(self, order_number: str) -> PurchaseDraft:
        return replace(self, order_number=order_number)

    def from_quotation(self, quotation_number: str) -> PurchaseDraft:
        return replace(self, quotation_number=quotation_number)

    def from_challan(self, challan_number: str) -> PurchaseDraft:
        return replace(self, challan_number=challan_number)

    def from_bill(self, bill_number: str) -> PurchaseDraft:
        return replace(self, bill_number=bill_number)


def needs(case: DocumentCase, document: str) -> bool:
    """True when the sheet row says the document is built from an earlier one (for example "order number")."""
    return case.inputs.get(f"{document}_number") == TEMPLATE_PLACEHOLDERS[document]


def is_yes(case: DocumentCase, column: str) -> bool:
    return case.inputs.get(column) == "Y"
