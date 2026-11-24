"""Sale bills for the outstanding cases: one line of the 0% GST item, so the bill amount is the line rate.

Save opens Mode Of Payment (the bill-time payment), then the Bill Adjustment window when the party has
credits or a changed bill no longer matches its adjustments, then a Print window (live 2026-10-09). Adjusting
credits is a separate step in the cases, so the adjustment window is saved as the app proposes it.
"""

import re
from decimal import Decimal

from playwright.sync_api import Page, expect

from pages.accounting.outstanding.document_desk import DELETE_ACTION, DocumentDesk
from pages.components.confirm_dialog import ConfirmDialog
from pages.sale.documents.bill import SaleBillDocument
from pages.sale.documents.mode_of_payment import ModeOfPayment

REFUSED_DELETE = re.compile(r"Can't Delete/Cancel Bill, Adjustment Available", re.IGNORECASE)
REFUSAL_TIMEOUT_MS = 30_000


class SaleBillDesk(DocumentDesk):
    def __init__(self, page: Page, item: str) -> None:
        self._bill = SaleBillDocument(page)
        super().__init__(page, item, self._bill)
        self._payment = ModeOfPayment(page)

    def create(self, party: str, amount: Decimal, paid_at_save: Decimal) -> str:
        self._start(party, amount)
        self._open_payment_window()
        if paid_at_save > 0:
            self._payment.take_cash(paid_at_save)
        self._save_payment()
        return self._saved_number(party)

    def expect_create_refused(self, party: str, amount: Decimal, paid_at_save: Decimal) -> None:
        self._start(party, amount)
        self._open_payment_window()
        self._payment.take_cash(paid_at_save)
        self._payment.expect_above_bill_amount_refused()

    def change_amount(self, number: str, amount: Decimal) -> None:
        self._open_for_change(number)
        self._reprice(amount)
        self._open_payment_window()
        self._save_payment()

    def change_payment(self, number: str, paid_at_save: Decimal) -> None:
        self._open_for_change(number)
        self._open_payment_window()
        self._payment.take_cash(paid_at_save)
        self._save_payment()

    def expect_delete_refused(self, number: str) -> None:
        self._list.choose_from_menu(number, DELETE_ACTION)
        ConfirmDialog(self._page).answer_yes()
        expect(self._page.get_by_text(REFUSED_DELETE).first).to_be_visible(timeout=REFUSAL_TIMEOUT_MS)

    def _start(self, party: str, amount: Decimal) -> None:
        self._start_for(party)
        self._line.add(amount)

    def _open_payment_window(self) -> None:
        self._save_from_footer()
        self._payment.expect_open()

    def _save_payment(self) -> None:
        self._payment.save()
        self._accept_adjustment_as_shown()
        self._close_print_window()
