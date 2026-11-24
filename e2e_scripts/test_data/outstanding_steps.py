"""The step language of the outstanding/advance cases (`scenarios/outstanding-advance.md`).

Bills and credits are named in a case ("A", "B", "R1", "SR1", "ADV") and the runner maps each name to the
document it saved. A credit is a receipt or a sale return; its `against` tuple says which bills it is
adjusted to; whatever is not allocated stays with the party as an advance.
"""

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum


class CreditKind(Enum):
    RECEIPT = "receipt"
    SALE_RETURN = "sale return"


@dataclass(frozen=True)
class Allocation:
    bill: str
    amount: Decimal


NOT_ADJUSTED: tuple[Allocation, ...] = ()


@dataclass(frozen=True)
class SaleBill:
    bill: str
    amount: Decimal
    paid_at_save: Decimal = Decimal(0)


@dataclass(frozen=True)
class RefusedSaleBill:
    """A bill whose bill-time payment exceeds its amount; the app must refuse to save it."""

    amount: Decimal
    paid_at_save: Decimal


@dataclass(frozen=True)
class ModifyBill:
    bill: str
    amount: Decimal


@dataclass(frozen=True)
class ChangeBillPayment:
    bill: str
    paid_at_save: Decimal


@dataclass(frozen=True)
class DeleteBill:
    bill: str


@dataclass(frozen=True)
class RefusedBillDelete:
    """Deleting a bill that still has an adjustment linked; the app must refuse."""

    bill: str


@dataclass(frozen=True)
class Credit:
    credit: str
    kind: CreditKind
    amount: Decimal
    against: tuple[Allocation, ...] = NOT_ADJUSTED


@dataclass(frozen=True)
class ModifyCredit:
    credit: str
    amount: Decimal
    against: tuple[Allocation, ...] = NOT_ADJUSTED


@dataclass(frozen=True)
class DeleteCredit:
    credit: str


@dataclass(frozen=True)
class Readjust:
    """Replaces a credit's adjustments; an empty `against` un-adjusts it completely."""

    credit: str
    against: tuple[Allocation, ...] = NOT_ADJUSTED


@dataclass(frozen=True)
class RefusedOverAdjustment:
    """Adjusting more than a bill's balance; the app must refuse the amount."""

    credit: str
    allocation: Allocation


Step = (
    SaleBill
    | RefusedSaleBill
    | ModifyBill
    | ChangeBillPayment
    | DeleteBill
    | RefusedBillDelete
    | Credit
    | ModifyCredit
    | DeleteCredit
    | Readjust
    | RefusedOverAdjustment
)


@dataclass(frozen=True)
class PartyBalances:
    """The workbook's "Expected Outstanding" and "Expected Advance" for the whole party."""

    outstanding: Decimal
    advance: Decimal


@dataclass(frozen=True)
class BillBalance:
    bill: str
    outstanding: Decimal


@dataclass(frozen=True)
class BillBalances:
    """Rows whose "Calculation" names single bills: those bills' balances, plus the party's advance."""

    bills: tuple[BillBalance, ...]
    advance: Decimal


Expectation = PartyBalances | BillBalances


@dataclass(frozen=True)
class OutstandingCase:
    number: int
    title: str
    steps: tuple[Step, ...]
    expected: Expectation
    known_issue: str = ""

    @property
    def id(self) -> str:
        return f"OA-{self.number:03d}"

    @property
    def needs_bill_time_payment(self) -> bool:
        return any(_takes_payment_at_save(step) for step in self.steps)


def _takes_payment_at_save(step: Step) -> bool:
    if isinstance(step, SaleBill):
        return step.paid_at_save > 0
    return isinstance(step, RefusedSaleBill | ChangeBillPayment)
