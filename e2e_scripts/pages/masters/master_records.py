"""Test-owned account groups and ledgers: made through the UI, remembered, and deleted in teardown."""

from functools import partial
from typing import TypeVar

from playwright.sync_api import Page

from pages.components.undo import UndoStep, undo_all
from pages.masters.account_group_form import AccountGroupForm
from pages.masters.ledger_form import LedgerForm, TaxRegistration
from pages.masters.master_list import AccountGroupList, LedgerList, MasterList
from test_data.masters import (
    INDIRECT_EXPENSES,
    AccountGroupSpec,
    GeneralLedgerSpec,
    MasterDataFactory,
    PartyLedgerSpec,
)

LedgerSpec = TypeVar("LedgerSpec", PartyLedgerSpec, GeneralLedgerSpec)


class MasterRecords:
    """Every record is remembered before the UI is asked to save it, so a half-done save is cleaned too."""

    def __init__(self, page: Page, data: MasterDataFactory) -> None:
        self._page = page
        self._data = data
        self._ledgers: list[str] = []
        self._groups: list[str] = []

    def new_customer(self) -> PartyLedgerSpec:
        return self._own_ledger(self._data.customer())

    def new_supplier(self) -> PartyLedgerSpec:
        return self._own_ledger(self._data.supplier())

    def new_group(self) -> AccountGroupSpec:
        group = self._data.account_group(INDIRECT_EXPENSES)
        self.own_group_name(group.name)
        return group

    def new_general_ledger(self, group: str) -> GeneralLedgerSpec:
        return self._own_ledger(self._data.general_ledger(group))

    def own_ledger_name(self, name: str) -> None:
        self._ledgers.append(name)

    def own_group_name(self, name: str) -> None:
        self._groups.append(name)

    def saved_customer(self) -> PartyLedgerSpec:
        return self._saved_party(self.new_customer())

    def saved_supplier(self) -> PartyLedgerSpec:
        return self._saved_party(self.new_supplier())

    def saved_gst_supplier(self, registration: TaxRegistration, gstin: str) -> PartyLedgerSpec:
        """A supplier in the company's own state, then registered for GST with the given GSTIN."""
        supplier = self.saved_supplier()
        form = LedgerForm(self._page)
        form.open_existing(supplier.name)
        form.register_for_gst(registration, gstin)
        form.update()
        form.expect_updated()
        return supplier

    def saved_group(self) -> AccountGroupSpec:
        group = self.new_group()
        form = AccountGroupForm(self._page)
        form.open_new()
        form.enter(group)
        form.save()
        form.expect_saved()
        return group

    def saved_general_ledger(self, group: str) -> GeneralLedgerSpec:
        ledger = self.new_general_ledger(group)
        form = LedgerForm(self._page)
        form.open_new()
        form.enter_general(ledger)
        form.save()
        form.expect_saved()
        return ledger

    def delete_all(self) -> None:
        """Ledgers go first: a group that still has a ledger cannot be deleted."""
        undo_all(
            [
                *_undo_steps(LedgerList(self._page), self._ledgers),
                *_undo_steps(AccountGroupList(self._page), list(reversed(self._groups))),
            ]
        )

    def _own_ledger(self, ledger: LedgerSpec) -> LedgerSpec:
        self.own_ledger_name(ledger.name)
        return ledger

    def _saved_party(self, party: PartyLedgerSpec) -> PartyLedgerSpec:
        form = LedgerForm(self._page)
        form.open_new()
        form.enter_party(party)
        form.save()
        form.expect_saved()
        return party


def _undo_steps(screen: MasterList, names: list[str]) -> list[UndoStep]:
    if not names:
        return []
    deletes: list[UndoStep] = [(name, partial(_delete_if_listed, screen, name)) for name in names]
    return [(f"opening {type(screen).__name__}", screen.open), *deletes]


def _delete_if_listed(screen: MasterList, name: str) -> None:
    if screen.is_listed(name):
        screen.delete(name)
