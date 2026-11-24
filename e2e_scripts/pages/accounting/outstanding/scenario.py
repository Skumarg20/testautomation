"""Runs one outstanding/advance case: plays its steps on the app, then checks the party's balances."""

from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Protocol

from pages.accounting.outstanding.outstanding_report import OutstandingReport, PartyOutstanding
from test_data.outstanding_steps import (
    Allocation,
    BillBalances,
    ChangeBillPayment,
    Credit,
    CreditKind,
    DeleteBill,
    DeleteCredit,
    Expectation,
    ModifyBill,
    ModifyCredit,
    OutstandingCase,
    PartyBalances,
    Readjust,
    RefusedBillDelete,
    RefusedOverAdjustment,
    RefusedSaleBill,
    SaleBill,
)

BillAllocations = dict[str, Decimal]
"""Adjusted amount per bill number, in the order the case names the bills."""


class SaleBills(Protocol):
    def create(self, party: str, amount: Decimal, paid_at_save: Decimal) -> str: ...
    def expect_create_refused(self, party: str, amount: Decimal, paid_at_save: Decimal) -> None: ...
    def change_amount(self, number: str, amount: Decimal) -> None: ...
    def change_payment(self, number: str, paid_at_save: Decimal) -> None: ...
    def delete(self, number: str) -> None: ...
    def expect_delete_refused(self, number: str) -> None: ...


class CreditDocuments(Protocol):
    """A receipt voucher or a sale return: both carry an amount that is adjusted to bills."""

    def create(self, party: str, amount: Decimal, allocations: BillAllocations) -> str: ...
    def change(self, number: str, amount: Decimal, allocations: BillAllocations) -> None: ...
    def readjust(self, number: str, allocations: BillAllocations) -> None: ...
    def expect_over_adjustment_refused(self, number: str, bill_number: str, amount: Decimal) -> None: ...
    def delete(self, number: str) -> None: ...


class UnknownDocumentError(KeyError):
    def __init__(self, case_id: str, name: str) -> None:
        super().__init__(f"{case_id}: no document named {name!r} was saved earlier in the case")


@dataclass(frozen=True)
class CaseDesks:
    """The screens a case acts through: sale bills, the two credit documents and the outstanding report."""

    bills: SaleBills
    credits: dict[CreditKind, CreditDocuments]
    report: OutstandingReport


class OutstandingScenario:
    def __init__(self, party: str, desks: CaseDesks) -> None:
        self._party = party
        self._bills = desks.bills
        self._credits = desks.credits
        self._report = desks.report
        self._numbers: dict[str, str] = {}
        self._credit_kinds: dict[str, CreditKind] = {}
        self._case_id = ""

    def play(self, case: OutstandingCase) -> None:
        self._case_id = case.id
        handlers: dict[type, Callable[[Any], None]] = {
            SaleBill: self._create_bill,
            RefusedSaleBill: self._refuse_bill,
            ModifyBill: self._modify_bill,
            ChangeBillPayment: self._change_payment,
            DeleteBill: self._delete_bill,
            RefusedBillDelete: self._refuse_bill_delete,
            Credit: self._create_credit,
            ModifyCredit: self._modify_credit,
            DeleteCredit: self._delete_credit,
            Readjust: self._readjust,
            RefusedOverAdjustment: self._refuse_over_adjustment,
        }
        for step in case.steps:
            handlers[type(step)](step)

    def expect_balances(self, expected: Expectation) -> None:
        actual = self._report.read(self._party)
        if isinstance(expected, PartyBalances):
            assert (actual.outstanding, actual.advance) == (expected.outstanding, expected.advance), (
                f"{self._case_id}: {actual}"
            )
            return
        self._expect_bill_balances(expected, actual)

    def _expect_bill_balances(self, expected: BillBalances, actual: PartyOutstanding) -> None:
        wanted = {self._number(row.bill): row.outstanding for row in expected.bills}
        seen = {number: actual.bill_balance(number) for number in wanted}
        assert (seen, actual.advance) == (wanted, expected.advance), f"{self._case_id}: {actual}"

    def _create_bill(self, step: SaleBill) -> None:
        self._numbers[step.bill] = self._bills.create(self._party, step.amount, step.paid_at_save)

    def _refuse_bill(self, step: RefusedSaleBill) -> None:
        self._bills.expect_create_refused(self._party, step.amount, step.paid_at_save)

    def _modify_bill(self, step: ModifyBill) -> None:
        self._bills.change_amount(self._number(step.bill), step.amount)

    def _change_payment(self, step: ChangeBillPayment) -> None:
        self._bills.change_payment(self._number(step.bill), step.paid_at_save)

    def _delete_bill(self, step: DeleteBill) -> None:
        self._bills.delete(self._number(step.bill))

    def _refuse_bill_delete(self, step: RefusedBillDelete) -> None:
        self._bills.expect_delete_refused(self._number(step.bill))

    def _create_credit(self, step: Credit) -> None:
        documents = self._credits[step.kind]
        self._numbers[step.credit] = documents.create(
            self._party, step.amount, self._allocations(step.against)
        )
        self._credit_kinds[step.credit] = step.kind

    def _modify_credit(self, step: ModifyCredit) -> None:
        allocations = self._allocations(step.against)
        self._credit_documents(step.credit).change(self._number(step.credit), step.amount, allocations)

    def _delete_credit(self, step: DeleteCredit) -> None:
        self._credit_documents(step.credit).delete(self._number(step.credit))

    def _readjust(self, step: Readjust) -> None:
        allocations = self._allocations(step.against)
        self._credit_documents(step.credit).readjust(self._number(step.credit), allocations)

    def _refuse_over_adjustment(self, step: RefusedOverAdjustment) -> None:
        allocation = step.allocation
        self._credit_documents(step.credit).expect_over_adjustment_refused(
            self._number(step.credit), self._number(allocation.bill), allocation.amount
        )

    def _allocations(self, against: tuple[Allocation, ...]) -> BillAllocations:
        return {self._number(allocation.bill): allocation.amount for allocation in against}

    def _credit_documents(self, name: str) -> CreditDocuments:
        return self._credits[self._credit_kinds[name]]

    def _number(self, name: str) -> str:
        if name not in self._numbers:
            raise UnknownDocumentError(self._case_id, name)
        return self._numbers[name]
