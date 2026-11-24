"""Test data for J21 notifications-export (specs/notifications-export.md)."""

from dataclasses import dataclass
from decimal import Decimal

# A plain Devanagari word (no conjuncts), so each of its characters must reach a PDF as itself (NE-23).
HINDI_WORD = "खाता"
BILL_AMOUNT = Decimal("150.00")
# Reserved for documentation (RFC 2606) and a number no operator issues: a stubbed send can never reach
# a person even if a stub were missing (the send guard aborts it anyway).
QA_EMAIL = "qa-sink@example.com"
QA_WHATSAPP_NUMBER = "9000000001"


@dataclass(frozen=True)
class OwnedBill:
    party: str
    number: str
    amount: Decimal


@dataclass(frozen=True)
class PreviewedBill:
    number: str
    amount: Decimal
    preview_pdf: bytes
