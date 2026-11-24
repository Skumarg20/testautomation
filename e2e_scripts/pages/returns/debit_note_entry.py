"""A debit note voucher of one amount between two ledgers, entered and saved on the Debit Note screen."""

from dataclasses import dataclass
from datetime import date

from pages.accounting.debit_note_page import DebitNotePage
from pages.accounting.voucher_cases import Leg


@dataclass(frozen=True)
class DebitNoteVoucher:
    debit_account: str
    credit_account: str
    amount: str
    narration: str


def save_debit_note(screen: DebitNotePage, voucher: DebitNoteVoucher) -> str:
    """Enters the voucher dated today (debit row first, as the existing DN cases do); returns its number."""
    screen.open_new_voucher()
    screen.enter_date(date.today())
    screen.select_account(0, voucher.debit_account)
    screen.enter_leg_amount(0, Leg("debit", voucher.debit_account, voucher.amount))
    screen.select_account(1, voucher.credit_account)
    screen.enter_leg_amount(1, Leg("credit", voucher.credit_account, voucher.amount))
    screen.enter_narration(voucher.narration)
    number = screen.voucher_number()
    screen.save()
    screen.expect_saved()
    return number
