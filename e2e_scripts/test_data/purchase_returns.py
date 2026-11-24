"""Test data of the J14 purchase return / debit note journey."""

from dataclasses import replace
from decimal import Decimal

from pages.returns.debit_note_entry import DebitNoteVoucher
from pages.returns.manual_return import ManualReturn
from test_data.factory import DataFactory
from test_data.models import ItemMasterSpec

CASH_PARTY = "Cash Account"
OPENING_QUANTITY = Decimal(10)
RETURNED_QUANTITY = Decimal(3)
RETURN_RATE = Decimal(100)
DEBIT_NOTE_AMOUNT = "500"
# The two ledgers the existing DN-001 case uses; both exist on the QA company.
DEBIT_ACCOUNT = "Cash Account"
CREDIT_ACCOUNT = "Additional Charges On Free Items"


def returnable_item(data: DataFactory, run_id: str) -> ItemMasterSpec:
    return replace(data.item_master(), product=f"QA-{run_id}-Return")


def manual_return_of(item: ItemMasterSpec) -> ManualReturn:
    return ManualReturn(CASH_PARTY, item.product, RETURNED_QUANTITY, RETURN_RATE)


def debit_note_voucher(run_id: str) -> DebitNoteVoucher:
    return DebitNoteVoucher(DEBIT_ACCOUNT, CREDIT_ACCOUNT, DEBIT_NOTE_AMOUNT, f"QA-{run_id} debit note")
