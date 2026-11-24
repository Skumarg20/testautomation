"""J14 debit note voucher (Accounting Trans. > Debit Note): the list, search and delete.

Plan: specs/purchase-return-debit-note.md (DNV-01, DNV-02, DNV-06). Voucher entry itself and the ledger
effect for the existing DN-001..DN-006 cases are in tests/journeys/accounting/test_debit_note.py.
"""

from decimal import Decimal

import pytest
from playwright.sync_api import Page

from pages.accounting.entry_date import format_for_app
from pages.returns.debit_note_list import DebitNoteList
from test_data.app_clock import app_today
from test_data.purchase_returns import DEBIT_ACCOUNT, DEBIT_NOTE_AMOUNT

# Voucher numbers are tenant-wide, as in the existing debit note tests.
pytestmark = [
    pytest.mark.p1,
    pytest.mark.journey("purchase-return-debit-note"),
    pytest.mark.xdist_group("chemist-tenant"),
]


def test_debit_note_is_found_by_its_number_with_date_party_and_amount(
    returns_page: Page, saved_debit_note: str
) -> None:
    vouchers = DebitNoteList(returns_page)
    vouchers.find(saved_debit_note)

    vouchers.expect_listed(saved_debit_note)
    assert vouchers.date_text(saved_debit_note) == format_for_app(app_today())
    assert vouchers.party(saved_debit_note) == DEBIT_ACCOUNT
    assert vouchers.amount(saved_debit_note) == Decimal(DEBIT_NOTE_AMOUNT)


def test_deleted_debit_note_is_no_longer_listed(returns_page: Page, saved_debit_note: str) -> None:
    vouchers = DebitNoteList(returns_page)
    vouchers.delete(saved_debit_note)

    vouchers.find(saved_debit_note)
    vouchers.expect_not_listed(saved_debit_note)
