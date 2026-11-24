"""Customers a round-2 test creates through Master > Accounts Master > Ledger, and deletes in teardown.

Each method saves a new customer (run-id name, the mandatory fields the QA company asks for) with one extra
attribute the manual cases need: an e-mail id, a credit limit, a Discontinue status, a Hide visibility, or no
mobile number. Names carry the run id; the ledgers are deleted afterwards (after their bills: fixtures tear
down in reverse order). Part C2 owns this helper.
"""

from collections.abc import Callable
from decimal import Decimal

from playwright.sync_api import Page

from pages.masters.ledger_form import LedgerForm
from pages.masters.master_records import MasterRecords
from pages.masters.round2_c2.ledger_windows import CreditLimitAction, LedgerExtras
from test_data.masters import MasterDataFactory, PartyLedgerSpec

Extras = Callable[[LedgerExtras], None]


def email_of(party: PartyLedgerSpec) -> str:
    """A reserved example.com address derived from the party's own name, so two parties never share one."""
    return f"{party.name.lower()}@example.com"


class OwnedParties:
    def __init__(self, page: Page, run_id: str) -> None:
        self._page = page
        self._records = MasterRecords(page, MasterDataFactory(run_id))

    def saved_with_email(self) -> PartyLedgerSpec:
        customer = self._records.new_customer()
        return self._save(customer, lambda extras: extras.type_email(email_of(customer)))

    def saved_with_credit_limit(self, limit: Decimal, action: CreditLimitAction) -> PartyLedgerSpec:
        customer = self._records.new_customer()
        return self._save(customer, lambda extras: extras.set_credit_limit(limit, action))

    def saved_discontinued(self) -> PartyLedgerSpec:
        return self._save(self._records.new_customer(), LedgerExtras.discontinue)

    def saved_hidden(self) -> PartyLedgerSpec:
        return self._save(self._records.new_customer(), LedgerExtras.hide)

    def saved_without_mobile(self) -> PartyLedgerSpec:
        """Needs the Control Room option "Mobile Number Mandatory in Ledger" held at No by the caller
        (createledger.component.ts:616-626); with Yes the form refuses an empty mobile."""
        customer = self._records.new_customer()
        form = LedgerForm(self._page)
        form.open_new()
        form.enter_party(customer)
        form.clear_mobile()
        form.save()
        form.expect_saved()
        return customer

    def delete_all(self) -> None:
        self._records.delete_all()

    def _save(self, customer: PartyLedgerSpec, fill_extras: Extras) -> PartyLedgerSpec:
        form = LedgerForm(self._page)
        form.open_new()
        form.enter_party(customer)
        fill_extras(LedgerExtras(self._page))
        form.save()
        form.expect_saved()
        return customer
