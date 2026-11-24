"""Self-checks of the outstanding/advance cases: every workbook row is there and every step is coherent."""

import pytest

from test_data.outstanding_cases import ALL_CASES, BILL_TIME_PAYMENT
from test_data.outstanding_steps import (
    Allocation,
    ChangeBillPayment,
    Credit,
    DeleteBill,
    DeleteCredit,
    ModifyBill,
    ModifyCredit,
    OutstandingCase,
    Readjust,
    RefusedBillDelete,
    RefusedOverAdjustment,
    SaleBill,
    Step,
)

pytestmark = pytest.mark.framework

WORKBOOK_ROWS = 100


def test_every_workbook_row_is_a_case_exactly_once() -> None:
    assert sorted(case.number for case in ALL_CASES) == list(range(1, WORKBOOK_ROWS + 1))


def test_only_the_bill_time_payment_group_needs_payment_at_save() -> None:
    needing = {case.id for case in ALL_CASES if case.needs_bill_time_payment}

    assert needing == {case.id for case in BILL_TIME_PAYMENT}


@pytest.mark.parametrize("case", ALL_CASES, ids=lambda case: case.id)
def test_steps_name_only_documents_that_exist_at_that_point(case: OutstandingCase) -> None:
    live_bills: set[str] = set()
    credits: set[str] = set()
    for step in case.steps:
        assert _bills_named(step) <= live_bills, f"{case.id}: {step}"
        assert _credits_named(step) <= credits, f"{case.id}: {step}"
        _record(step, live_bills, credits)


@pytest.mark.parametrize("case", ALL_CASES, ids=lambda case: case.id)
def test_no_credit_is_allocated_more_than_its_amount(case: OutstandingCase) -> None:
    for step in case.steps:
        if isinstance(step, Credit | ModifyCredit):
            assert sum(allocation.amount for allocation in step.against) <= step.amount, case.id


def _bills_named(step: Step) -> set[str]:
    named = {allocation.bill for allocation in _allocations(step)}
    if isinstance(step, ModifyBill | ChangeBillPayment | DeleteBill | RefusedBillDelete):
        named.add(step.bill)
    return named


def _credits_named(step: Step) -> set[str]:
    if isinstance(step, ModifyCredit | DeleteCredit | Readjust | RefusedOverAdjustment):
        return {step.credit}
    return set()


def _allocations(step: Step) -> tuple[Allocation, ...]:
    if isinstance(step, Credit | ModifyCredit | Readjust):
        return step.against
    if isinstance(step, RefusedOverAdjustment):
        return (step.allocation,)
    return ()


def _record(step: Step, live_bills: set[str], credits: set[str]) -> None:
    if isinstance(step, SaleBill):
        live_bills.add(step.bill)
    elif isinstance(step, DeleteBill):
        live_bills.discard(step.bill)
    elif isinstance(step, Credit):
        credits.add(step.credit)
