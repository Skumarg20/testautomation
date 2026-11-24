"""The 100 outstanding/advance base cases of `TestCase_Outstanding.xlsx`, as steps and expected balances.

Expected values are copied from the workbook's "Expected Outstanding" and "Expected Advance" columns
(scenarios/outstanding-advance.md). Never change one to make a test pass; rows the workbook contradicts are
listed there under "Needs decision".
"""

from decimal import Decimal

from test_data.outstanding_steps import (
    NOT_ADJUSTED,
    Allocation,
    BillBalance,
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
    Step,
)

ADVANCE_DECREASE_REFUSED = "Workbook remark: system does not allow decreasing an advance (actual stayed 1000)"


def to(bill: str, amount: int) -> Allocation:
    return Allocation(bill, Decimal(amount))


def bill(name: str, amount: int, paid: int = 0) -> SaleBill:
    return SaleBill(name, Decimal(amount), Decimal(paid))


def receipt(name: str, amount: int, *against: Allocation) -> Credit:
    return Credit(name, CreditKind.RECEIPT, Decimal(amount), against)


def sale_return(name: str, amount: int, *against: Allocation) -> Credit:
    return Credit(name, CreditKind.SALE_RETURN, Decimal(amount), against)


def modify(name: str, amount: int, *against: Allocation) -> ModifyCredit:
    return ModifyCredit(name, Decimal(amount), against)


def readjust(name: str, *against: Allocation) -> Readjust:
    return Readjust(name, against)


def unadjust(name: str) -> Readjust:
    return Readjust(name, NOT_ADJUSTED)


def modify_bill(name: str, amount: int) -> ModifyBill:
    return ModifyBill(name, Decimal(amount))


def change_payment(name: str, paid: int) -> ChangeBillPayment:
    return ChangeBillPayment(name, Decimal(paid))


def party(outstanding: int, advance: int) -> PartyBalances:
    return PartyBalances(Decimal(outstanding), Decimal(advance))


def bills(advance: int, **balances: int) -> BillBalances:
    rows = tuple(BillBalance(name, Decimal(amount)) for name, amount in balances.items())
    return BillBalances(rows, Decimal(advance))


Heading = tuple[int, str]
"""The workbook's case number and title."""


def case(heading: Heading, steps: list[Step], expected: Expectation) -> OutstandingCase:
    number, title = heading
    return OutstandingCase(number, title, tuple(steps), expected)


def known_issue(heading: Heading, steps: list[Step], expected: Expectation) -> OutstandingCase:
    number, title = heading
    return OutstandingCase(number, title, tuple(steps), expected, ADVANCE_DECREASE_REFUSED)


A1000 = bill("A", 1000)
PAID_300 = bill("A", 1000, paid=300)
ADV_1000 = receipt("ADV", 1000)
ADV_500 = receipt("ADV", 500)

SALE_BILL_AND_RECEIPT = (
    case((1, "Simple credit sale"), [A1000], party(1000, 0)),
    case((2, "Sale bill modify, increase"), [A1000, modify_bill("A", 1500)], party(1500, 0)),
    case((3, "Sale bill modify, decrease"), [bill("A", 1500), modify_bill("A", 1000)], party(1000, 0)),
    case(
        (4, "Bill modified below an adjusted receipt"),
        [bill("A", 1500), receipt("R1", 1200, to("A", 1200)), modify_bill("A", 1000)],
        party(0, 200),
    ),
    case((5, "Two bills, same party"), [A1000, bill("B", 2000)], party(3000, 0)),
    case((6, "Sale bill delete, no adjustment"), [A1000, DeleteBill("A")], party(0, 0)),
    case((7, "Partial receipt"), [A1000, receipt("R1", 400, to("A", 400))], party(600, 0)),
    case((8, "Full receipt"), [A1000, receipt("R1", 1000, to("A", 1000))], party(0, 0)),
    case((9, "Excess receipt"), [A1000, receipt("R1", 1300, to("A", 1000))], party(0, 300)),
    case(
        (10, "Receipt modify, increase"),
        [A1000, receipt("R1", 400, to("A", 400)), modify("R1", 700, to("A", 700))],
        party(300, 0),
    ),
    case(
        (11, "Receipt modified to excess"),
        [A1000, receipt("R1", 900, to("A", 900)), modify("R1", 1200, to("A", 1000))],
        party(0, 200),
    ),
    case(
        (12, "Receipt delete after partial adjustment"),
        [A1000, receipt("R1", 500, to("A", 500)), DeleteCredit("R1")],
        party(1000, 0),
    ),
    case(
        (13, "Receipt un-adjust"),
        [A1000, receipt("R1", 1000, to("A", 1000)), unadjust("R1")],
        party(1000, 1000),
    ),
    case((14, "Receipt without a bill is an advance"), [receipt("R1", 600)], party(0, 600)),
    case(
        (15, "One receipt adjusted to two bills"),
        [bill("A", 600), bill("B", 400), receipt("R1", 1000, to("A", 600), to("B", 400))],
        party(0, 0),
    ),
)

SALE_RETURN = (
    case((16, "Sale return, partial"), [A1000, sale_return("SR1", 300, to("A", 300))], party(700, 0)),
    case((17, "Sale return, full"), [A1000, sale_return("SR1", 1000, to("A", 1000))], party(0, 0)),
    case(
        (18, "Sale return greater than the bill"),
        [A1000, sale_return("SR1", 1300, to("A", 1000))],
        party(0, 300),
    ),
    case(
        (19, "Sale return after full receipt"),
        [A1000, receipt("R1", 1000, to("A", 1000)), sale_return("SR1", 400)],
        party(0, 400),
    ),
    case(
        (20, "Sale return and partial receipt"),
        [A1000, receipt("R1", 400, to("A", 400)), sale_return("SR1", 300, to("A", 300))],
        party(300, 0),
    ),
    case(
        (21, "Sale return modify, increase"),
        [A1000, sale_return("SR1", 300, to("A", 300)), modify("SR1", 500, to("A", 500))],
        party(500, 0),
    ),
    case(
        (22, "Sale return modify, decrease"),
        [A1000, sale_return("SR1", 500, to("A", 500)), modify("SR1", 200, to("A", 200))],
        party(800, 0),
    ),
    case(
        (23, "Sale return delete"),
        [A1000, sale_return("SR1", 400, to("A", 400)), DeleteCredit("SR1")],
        party(1000, 0),
    ),
    case(
        (24, "Sale return un-adjust"),
        [A1000, sale_return("SR1", 400, to("A", 400)), unadjust("SR1")],
        party(1000, 400),
    ),
    case(
        (25, "Two sale returns on one bill"),
        [A1000, sale_return("SR1", 200, to("A", 200)), sale_return("SR2", 300, to("A", 300))],
        party(500, 0),
    ),
    case(
        (26, "Sale return after partial receipt"),
        [A1000, receipt("R1", 400, to("A", 400)), sale_return("SR1", 300, to("A", 300))],
        party(300, 0),
    ),
    case(
        (27, "Sale return after partial receipt, excess"),
        [A1000, receipt("R1", 400, to("A", 400)), sale_return("SR1", 700, to("A", 600))],
        party(0, 100),
    ),
    case(
        (28, "Sale return adjusted in the next sale bill"),
        [
            A1000,
            receipt("R1", 1000, to("A", 1000)),
            sale_return("SR1", 300),
            bill("B", 800),
            readjust("SR1", to("B", 300)),
        ],
        party(500, 0),
    ),
    case(
        (29, "Sale return delete after receipt"),
        [A1000, receipt("R1", 600, to("A", 600)), sale_return("SR1", 300, to("A", 300)), DeleteCredit("SR1")],
        party(400, 0),
    ),
    case(
        (30, "Sale return reference change"),
        [A1000, bill("B", 800), sale_return("SR1", 300, to("A", 300)), readjust("SR1", to("B", 300))],
        bills(0, A=1000, B=500),
    ),
    case(
        (31, "Receipt after full sale return"),
        [A1000, sale_return("SR1", 1000, to("A", 1000)), receipt("R1", 200)],
        party(0, 200),
    ),
    case(
        (32, "Receipt modify after sale return"),
        [
            A1000,
            sale_return("SR1", 400, to("A", 400)),
            receipt("R1", 300, to("A", 300)),
            modify("R1", 500, to("A", 500)),
        ],
        party(100, 0),
    ),
    case(
        (33, "Receipt delete after sale return"),
        [A1000, sale_return("SR1", 400, to("A", 400)), receipt("R1", 300, to("A", 300)), DeleteCredit("R1")],
        party(600, 0),
    ),
    case(
        (34, "Receipt un-adjust after sale return"),
        [A1000, sale_return("SR1", 400, to("A", 400)), receipt("R1", 300, to("A", 300)), unadjust("R1")],
        party(600, 300),
    ),
    case(
        (35, "Two receipts and a sale return"),
        [
            A1000,
            receipt("R1", 300, to("A", 300)),
            receipt("R2", 200, to("A", 200)),
            sale_return("SR1", 400, to("A", 400)),
        ],
        party(100, 0),
    ),
    case(
        (36, "Sale return before any receipt"), [A1000, sale_return("SR1", 500, to("A", 500))], party(500, 0)
    ),
    case(
        (37, "Receipt before sale return"),
        [A1000, receipt("R1", 400, to("A", 400)), sale_return("SR1", 500, to("A", 500))],
        party(100, 0),
    ),
    case(
        (38, "Receipt and sale return exactly close the bill"),
        [A1000, receipt("R1", 600, to("A", 600)), sale_return("SR1", 400, to("A", 400))],
        party(0, 0),
    ),
    case(
        (39, "Sale return over the remaining balance"),
        [A1000, receipt("R1", 700, to("A", 700)), sale_return("SR1", 400, to("A", 300))],
        party(0, 100),
    ),
    case(
        (40, "Sale return un-adjusted, then adjusted again"),
        [A1000, sale_return("SR1", 400, to("A", 400)), unadjust("SR1"), readjust("SR1", to("A", 400))],
        party(600, 0),
    ),
)

BILL_TIME_PAYMENT = (
    case((41, "Bill-time partial payment"), [PAID_300], party(700, 0)),
    case((42, "Bill-time full payment"), [bill("A", 1000, paid=1000)], party(0, 0)),
    case(
        (43, "Bill-time payment above the bill is refused"),
        [RefusedSaleBill(Decimal(1000), Decimal(1200))],
        party(0, 0),
    ),
    case((44, "Bill-time payment modified up"), [PAID_300, change_payment("A", 500)], party(500, 0)),
    case(
        (45, "Bill-time payment modified down"),
        [bill("A", 1000, paid=500), change_payment("A", 200)],
        party(800, 0),
    ),
    case((46, "Bill-time payment removed"), [PAID_300, change_payment("A", 0)], party(1000, 0)),
    case((47, "Invoice delete with only a bill-time payment"), [PAID_300, DeleteBill("A")], party(0, 0)),
    case(
        (48, "Bill-time payment and full sale return"),
        [PAID_300, sale_return("SR1", 1000, to("A", 700))],
        party(0, 300),
    ),
    case(
        (49, "Bill-time payment and partial sale return"),
        [PAID_300, sale_return("SR1", 400, to("A", 400))],
        party(300, 0),
    ),
    case((50, "Bill-time payment and receipt"), [PAID_300, receipt("R1", 500, to("A", 500))], party(200, 0)),
    case(
        (51, "Bill-time payment and excess receipt"),
        [PAID_300, receipt("R1", 800, to("A", 700))],
        party(0, 100),
    ),
    case(
        (52, "Bill-time payment and two receipts"),
        [PAID_300, receipt("R1", 200, to("A", 200)), receipt("R2", 300, to("A", 300))],
        party(200, 0),
    ),
    case(
        (53, "Bill-time payment and receipt modify"),
        [PAID_300, receipt("R1", 200, to("A", 200)), modify("R1", 400, to("A", 400))],
        party(300, 0),
    ),
    case(
        (54, "Bill-time payment and receipt delete"),
        [PAID_300, receipt("R1", 400, to("A", 400)), DeleteCredit("R1")],
        party(700, 0),
    ),
    case(
        (55, "Bill-time payment and receipt un-adjust"),
        [PAID_300, receipt("R1", 400, to("A", 400)), unadjust("R1")],
        party(700, 400),
    ),
    case(
        (56, "Bill-time payment, sale return and receipt"),
        [PAID_300, sale_return("SR1", 400, to("A", 400)), receipt("R1", 200, to("A", 200))],
        party(100, 0),
    ),
    case(
        (57, "Bill-time payment, excess sale return and receipt"),
        [PAID_300, sale_return("SR1", 800, to("A", 700)), receipt("R1", 100)],
        party(0, 200),
    ),
    case(
        (58, "Bill-time payment modified after sale return"),
        [PAID_300, sale_return("SR1", 400, to("A", 400)), change_payment("A", 500)],
        party(100, 0),
    ),
    case(
        (59, "Bill-time payment removed after sale return"),
        [PAID_300, sale_return("SR1", 400, to("A", 400)), change_payment("A", 0)],
        party(600, 0),
    ),
    case(
        (60, "Bill-time payment and sale return delete"),
        [PAID_300, sale_return("SR1", 400, to("A", 400)), DeleteCredit("SR1")],
        party(700, 0),
    ),
    case(
        (100, "Master end-to-end case"),
        [PAID_300, receipt("R1", 200, to("A", 200)), sale_return("SR1", 600, to("A", 500))],
        party(0, 100),
    ),
)

ADVANCE = (
    case((61, "Advance receipt"), [ADV_1000], party(0, 1000)),
    case(
        (62, "Advance adjusted to one bill"),
        [ADV_1000, bill("A", 600), readjust("ADV", to("A", 600))],
        party(0, 400),
    ),
    case(
        (63, "Advance adjusted to two bills"),
        [ADV_1000, bill("A", 400), bill("B", 600), readjust("ADV", to("A", 400), to("B", 600))],
        party(0, 0),
    ),
    case(
        (64, "Advance partly adjusted"),
        [ADV_1000, bill("A", 800), readjust("ADV", to("A", 300))],
        party(500, 700),
    ),
    known_issue((65, "Advance modify, decrease"), [ADV_1000, modify("ADV", 700)], party(0, 700)),
    case((66, "Advance modify, increase"), [receipt("ADV", 700), modify("ADV", 1000)], party(0, 1000)),
    case((67, "Advance delete, no adjustment"), [ADV_1000, DeleteCredit("ADV")], party(0, 0)),
    case(
        (68, "Advance used, un-adjusted, then bill deleted"),
        [ADV_1000, bill("A", 600), readjust("ADV", to("A", 600)), unadjust("ADV"), DeleteBill("A")],
        party(0, 1000),
    ),
    case(
        (69, "Advance adjusted then un-adjusted"),
        [ADV_1000, bill("A", 700), readjust("ADV", to("A", 700)), unadjust("ADV")],
        party(700, 1000),
    ),
    case(
        (70, "Advance adjusted to the wrong bill, then corrected"),
        [
            ADV_1000,
            bill("A", 400),
            bill("B", 600),
            readjust("ADV", to("A", 400)),
            unadjust("ADV"),
            readjust("ADV", to("B", 600)),
        ],
        bills(400, B=0),
    ),
    case(
        (71, "Invoice delete with advance adjusted is refused"),
        [ADV_500, bill("A", 500), readjust("ADV", to("A", 500)), RefusedBillDelete("A")],
        party(0, 0),
    ),
    case(
        (72, "Advance un-adjusted, then invoice deleted"),
        [ADV_500, bill("A", 500), readjust("ADV", to("A", 500)), unadjust("ADV"), DeleteBill("A")],
        party(0, 500),
    ),
    case(
        (73, "Invoice delete with partial advance adjusted is refused"),
        [ADV_1000, bill("A", 600), readjust("ADV", to("A", 300)), RefusedBillDelete("A")],
        party(300, 700),
    ),
    case(
        (74, "Partial advance un-adjusted, then invoice deleted"),
        [ADV_1000, bill("A", 600), readjust("ADV", to("A", 300)), unadjust("ADV"), DeleteBill("A")],
        party(0, 1000),
    ),
    case(
        (75, "Advance and receipt combined"),
        [receipt("ADV", 400), A1000, readjust("ADV", to("A", 400)), receipt("R1", 300, to("A", 300))],
        party(300, 0),
    ),
    case(
        (76, "Advance and sale return combined"),
        [receipt("ADV", 400), A1000, readjust("ADV", to("A", 400)), sale_return("SR1", 300, to("A", 300))],
        party(300, 0),
    ),
    case(
        (77, "Advance over-adjustment is refused"),
        [ADV_500, bill("A", 400), RefusedOverAdjustment("ADV", to("A", 600)), readjust("ADV", to("A", 400))],
        party(0, 100),
    ),
    case(
        (78, "Advance adjusted after bill modify"),
        [ADV_500, bill("A", 600), modify_bill("A", 400), readjust("ADV", to("A", 400))],
        party(0, 100),
    ),
    case(
        (79, "Advance adjusted, then receipt modified"),
        [
            ADV_500,
            bill("A", 800),
            readjust("ADV", to("A", 500)),
            receipt("R1", 200, to("A", 200)),
            modify("R1", 400, to("A", 300)),
        ],
        party(0, 100),
    ),
    case(
        (80, "Advance un-adjusted after use on two bills"),
        [
            ADV_1000,
            bill("A", 400),
            bill("B", 300),
            readjust("ADV", to("A", 400), to("B", 300)),
            unadjust("ADV"),
        ],
        party(700, 1000),
    ),
)

DELETE_AND_UNADJUST = (
    case(
        (81, "Invoice delete with receipt adjusted is refused"),
        [A1000, receipt("R1", 600, to("A", 600)), RefusedBillDelete("A")],
        party(400, 0),
    ),
    case(
        (82, "Receipt un-adjusted, then invoice deleted"),
        [A1000, receipt("R1", 600, to("A", 600)), unadjust("R1"), DeleteBill("A")],
        party(0, 600),
    ),
    case(
        (83, "Invoice delete with sale return adjusted is refused"),
        [A1000, sale_return("SR1", 400, to("A", 400)), RefusedBillDelete("A")],
        party(600, 0),
    ),
    case(
        (84, "Sale return un-adjusted, then invoice deleted"),
        [A1000, sale_return("SR1", 400, to("A", 400)), unadjust("SR1"), DeleteBill("A")],
        party(0, 400),
    ),
    case(
        (85, "Invoice delete with advance adjusted is refused (again)"),
        [ADV_500, bill("A", 500), readjust("ADV", to("A", 500)), RefusedBillDelete("A")],
        party(0, 0),
    ),
    case(
        (86, "Advance un-adjusted, then invoice deleted (again)"),
        [ADV_500, bill("A", 500), readjust("ADV", to("A", 500)), unadjust("ADV"), DeleteBill("A")],
        party(0, 500),
    ),
    case(
        (87, "Receipt deleted after partial adjustment"),
        [A1000, receipt("R1", 400, to("A", 400)), DeleteCredit("R1")],
        party(1000, 0),
    ),
    case(
        (88, "Sale return deleted after partial adjustment"),
        [A1000, sale_return("SR1", 300, to("A", 300)), DeleteCredit("SR1")],
        party(1000, 0),
    ),
    case(
        (89, "Receipt and sale return adjusted, receipt deleted"),
        [A1000, receipt("R1", 400, to("A", 400)), sale_return("SR1", 300, to("A", 300)), DeleteCredit("R1")],
        party(1000, 0),
    ),
    case(
        (90, "Receipt and sale return adjusted, sale return deleted"),
        [A1000, receipt("R1", 400, to("A", 400)), sale_return("SR1", 300, to("A", 300)), DeleteCredit("SR1")],
        party(1000, 0),
    ),
    case(
        (91, "Receipt un-adjusted after partial adjustment"),
        [A1000, receipt("R1", 400, to("A", 400)), unadjust("R1")],
        party(1000, 400),
    ),
    case(
        (92, "Sale return un-adjusted after partial adjustment"),
        [A1000, sale_return("SR1", 300, to("A", 300)), unadjust("SR1")],
        party(1000, 300),
    ),
    case(
        (93, "Receipt un-adjusted, then adjusted to another bill"),
        [
            A1000,
            bill("B", 600),
            receipt("R1", 500, to("A", 500)),
            unadjust("R1"),
            readjust("R1", to("B", 500)),
        ],
        bills(0, B=100),
    ),
    case(
        (94, "Sale return un-adjusted, then adjusted to another bill"),
        [
            A1000,
            bill("B", 700),
            sale_return("SR1", 400, to("A", 400)),
            unadjust("SR1"),
            readjust("SR1", to("B", 400)),
        ],
        bills(0, B=300),
    ),
    case(
        (95, "Advance, receipt and sale return mixed"),
        [
            receipt("ADV", 300),
            A1000,
            readjust("ADV", to("A", 300)),
            receipt("R1", 200, to("A", 200)),
            sale_return("SR1", 400, to("A", 400)),
        ],
        party(100, 0),
    ),
    case(
        (96, "Receipt created after the invoice was deleted"),
        [A1000, DeleteBill("A"), receipt("R1", 500)],
        party(0, 500),
    ),
    case(
        (97, "Sale return created after the invoice was deleted"),
        [A1000, DeleteBill("A"), sale_return("SR1", 400)],
        party(0, 400),
    ),
    case(
        (98, "Un-adjust in mixed order"),
        [
            receipt("ADV", 100),
            A1000,
            readjust("ADV", to("A", 100)),
            receipt("R1", 300, to("A", 300)),
            sale_return("SR1", 200, to("A", 200)),
            unadjust("SR1"),
            unadjust("ADV"),
            unadjust("R1"),
        ],
        party(1000, 600),
    ),
    case(
        (99, "Full rollback"),
        [
            A1000,
            receipt("R1", 400, to("A", 400)),
            sale_return("SR1", 300, to("A", 300)),
            unadjust("R1"),
            unadjust("SR1"),
            DeleteCredit("R1"),
            DeleteCredit("SR1"),
        ],
        party(1000, 0),
    ),
)

ALL_CASES = SALE_BILL_AND_RECEIPT + SALE_RETURN + BILL_TIME_PAYMENT + ADVANCE + DELETE_AND_UNADJUST
