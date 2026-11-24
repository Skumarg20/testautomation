"""End-to-end voucher scenarios shared by the sheets.

A negative case ends as soon as the app shows the warning it expects; a positive case must save,
move the ledger balances as the voucher says and, when the sheet asks, delete and restore them.
"""

from decimal import Decimal

from pages.accounting.entry_date import is_today
from pages.accounting.ledger_balances import LedgerPair
from pages.accounting.receipt_payment_voucher import ReceiptPaymentVoucher
from pages.accounting.two_sided_voucher import TwoSidedVoucher
from pages.accounting.voucher_cases import Leg, SingleSidedCase, TwoSidedCase
from pages.accounting.voucher_screen import VoucherScreen

NO_BALANCE = Decimal(0)
CASH_MODE = "Cash Account"


def _named(*accounts: str) -> tuple[str, ...]:
    """The accounts a case actually names; a case may leave one empty."""
    return tuple(account for account in accounts if account)


def _finish_outcome(screen: VoucherScreen, is_negative: bool) -> None:
    if is_negative:
        screen.expect_rejected()
    else:
        screen.expect_saved()


class SingleSidedFlow:
    def __init__(self, screen: ReceiptPaymentVoucher, case: SingleSidedCase) -> None:
        self._screen = screen
        self._case = case

    @property
    def _account(self) -> str:
        return self._case.leg.account

    @property
    def _deletes_after_saving(self) -> bool:
        return not self._case.is_negative and self._case.delete_after

    def run(self) -> None:
        balance_before = self._balance_before()
        self._open_voucher()
        self._screen.choose_mode(CASH_MODE)
        self._screen.select_account(0, self._account)
        if self._account and self._fill_entry_stops_early():
            return
        voucher_number = self._screen.voucher_number() if self._deletes_after_saving else ""
        self._screen.save()
        _finish_outcome(self._screen, self._case.is_negative)
        if not self._case.is_negative:
            self._verify_and_delete(balance_before, voucher_number)

    def _open_voucher(self) -> None:
        """A case that deletes its voucher needs the voucher number shown. The Control Room shows the
        settings of the open document, so the setting is switched on a voucher, then a new one is opened."""
        self._screen.open_new_voucher()
        if self._deletes_after_saving and not self._screen.shows_voucher_number():
            self._screen.turn_on_voucher_numbers()
            self._screen.open_new_voucher()

    def _balance_before(self) -> Decimal:
        if self._case.is_negative or not self._account:
            return NO_BALANCE
        return self._screen.ledgers.balance_of(self._account)

    def _fill_entry_stops_early(self) -> bool:
        case, screen = self._case, self._screen
        screen.enter_row_date(case.day)
        if not is_today(case.day):
            screen.expect_date_warning()
            if case.is_negative:
                return True
        screen.enter_amount(case.leg.amount)
        if case.leg.is_below_minimum:
            screen.toasts.expect_warning()
            if case.is_negative:
                return True
        screen.enter_short_amount(case.short_amount)
        screen.enter_narration(case.narration)
        return False

    def _verify_and_delete(self, balance_before: Decimal, voucher_number: str) -> None:
        ledgers = self._screen.ledgers
        if self._account:
            expected = balance_before + self._screen.BALANCE_SIGN * self._case.total
            ledgers.expect_balance(self._account, expected)
        if self._case.delete_after:
            self._screen.delete_voucher(voucher_number, _named(self._account))
            if self._account:
                ledgers.expect_balance(self._account, balance_before)


class TwoSidedFlow:
    def __init__(self, screen: TwoSidedVoucher, case: TwoSidedCase) -> None:
        self._screen = screen
        self._case = case

    def run(self) -> None:
        balance_before = self._balances_before()
        self._screen.open_new_voucher()
        if self._header_stops_early() or self._legs_stop_early():
            return
        voucher_number = self._screen.voucher_number()
        self._screen.save()
        _finish_outcome(self._screen, self._case.is_negative)
        if not self._case.is_negative:
            self._verify_and_delete(balance_before, voucher_number)

    @property
    def _names(self) -> tuple[str, str]:
        return self._case.debit_leg.account, self._case.credit_leg.account

    def _balances_before(self) -> LedgerPair:
        if self._case.is_negative or not self._case.has_both_accounts:
            return LedgerPair(NO_BALANCE, NO_BALANCE)
        return self._screen.ledgers.refreshed_pair(*self._names)

    def _header_stops_early(self) -> bool:
        self._screen.enter_date(self._case.day)
        if is_today(self._case.day):
            return False
        self._screen.expect_date_warning()
        return self._case.is_negative

    def _legs_stop_early(self) -> bool:
        first, second = self._case.first, self._case.second
        self._screen.choose_side(0, first.side)
        self._screen.select_account(0, first.account)
        if self._acknowledge_account_warning():
            return True
        if not first.account:
            return False
        if self._amount_stops_early(0, first):
            return True
        if second.account and self._second_leg_stops_early(second):
            return True
        self._screen.enter_narration(self._case.narration)
        return False

    def _second_leg_stops_early(self, second: Leg) -> bool:
        self._screen.choose_side(1, second.side)
        self._screen.select_account(1, second.account)
        return self._acknowledge_account_warning() or self._amount_stops_early(1, second)

    def _acknowledge_account_warning(self) -> bool:
        """True when this negative case is over because the app refused the account."""
        if not self._screen.account_warning_shown():
            return False
        self._screen.toasts.expect_warning()
        return self._case.is_negative

    def _amount_stops_early(self, row: int, leg: Leg) -> bool:
        self._screen.enter_leg_amount(row, leg)
        if not leg.is_below_minimum:
            return False
        self._screen.toasts.expect_warning()
        return self._case.is_negative

    def _verify_and_delete(self, before: LedgerPair, voucher_number: str) -> None:
        if not self._case.has_both_accounts:
            self._delete_if_asked(voucher_number)
            return
        debit, credit = self._case.debit_leg.value, self._case.credit_leg.value
        expected = LedgerPair(before.debit_side + debit, before.credit_side - credit)
        self._screen.ledgers.expect_pair(self._names, expected)
        self._delete_if_asked(voucher_number)
        if self._case.delete_after:
            self._screen.ledgers.expect_pair(self._names, before)

    def _delete_if_asked(self, voucher_number: str) -> None:
        if self._case.delete_after:
            self._screen.delete_voucher(voucher_number, _named(*self._names))
