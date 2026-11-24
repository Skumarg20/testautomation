"""Test data of the J41 support-helpdesk journey: the desk the tests serve instead of Marg's live one.

Names and ids are invented (prefixed "QA"), so a served row can never be mistaken for a real ticket. The
hidden Main Disposition ids 60, 61, 62, 71 and 72 are the ones `create-ticket.component.ts:479` filters out.
"""

from pages.support.desk_feed import ChatLine, Choice, DeskTicket, DispositionTree, Suggestion

BILLING = Choice("9101", "QA Billing")
GST = Choice("9102", "QA GST")
HIDDEN_MAIN = tuple(
    Choice(choice_id, f"QA Hidden {choice_id}") for choice_id in ("60", "61", "62", "71", "72")
)

SALE_BILL = Choice("9201", "QA Sale bill", BILLING.choice_id)
PURCHASE_BILL = Choice("9202", "QA Purchase bill", BILLING.choice_id)
GSTR_1 = Choice("9203", "QA GSTR-1", GST.choice_id)

BILL_NOT_SAVING = Choice("9301", "QA Bill not saving", SALE_BILL.choice_id)
PRINT_ISSUE = Choice("9302", "QA Print issue", SALE_BILL.choice_id)
RETURN_FILING = Choice("9303", "QA Return filing", GSTR_1.choice_id)

DESK_TREE = DispositionTree(
    main=(BILLING, GST, *HIDDEN_MAIN),
    sub=(SALE_BILL, PURCHASE_BILL, GSTR_1),
    problem=(BILL_NOT_SAVING, PRINT_ISSUE, RETURN_FILING),
)

PENDING_TICKET = DeskTicket(
    ticket_id=9_000_003,
    ticket_no="QA-T3",
    status="Pending",
    description="QA pending ticket: sale bill does not save",
    main_disposition=BILLING,
    sub_disposition=SALE_BILL,
    problem_type=BILL_NOT_SAVING,
    ticket_date="2026-10-03T11:20:00",
    image_name="screen.png",
)
CLOSED_TICKET = DeskTicket(
    ticket_id=9_000_002,
    ticket_no="QA-T2",
    status="Closed",
    description="QA closed ticket: GSTR-1 return filing",
    main_disposition=GST,
    sub_disposition=GSTR_1,
    problem_type=RETURN_FILING,
    ticket_date="2026-10-02T09:05:00",
)
OLDEST_TICKET = DeskTicket(
    ticket_id=9_000_001,
    ticket_no="QA-T1",
    status="Closed",
    description="QA oldest ticket: print issue",
    main_disposition=BILLING,
    sub_disposition=SALE_BILL,
    problem_type=PRINT_ISSUE,
    ticket_date="2026-10-01T08:00:00",
)
# What the desk returns after the stubbed save of SH-40: the new ticket, numbered by the desk.
RAISED_TICKET = DeskTicket(
    ticket_id=9_000_004,
    ticket_no="QA-T4",
    status="Pending",
    description="QA raised ticket: sale bill does not save",
    main_disposition=BILLING,
    sub_disposition=SALE_BILL,
    problem_type=BILL_NOT_SAVING,
    ticket_date="2026-10-04T10:00:00",
)
# Served out of order: the list must sort them by ID, newest first (`support-ticket.component.ts:429`).
DESK_TICKETS = (CLOSED_TICKET, OLDEST_TICKET, PENDING_TICKET)
NEWEST_FIRST = ("QA-T3", "QA-T2", "QA-T1")

PARTNER_REPLY = ChatLine("QA reply: we are looking into it", "03-10-2026 12:00")
SUGGESTION = Suggestion("How to file QA gstr returns", "https://qa-suggestion.invalid/gstr")

REOPEN_MESSAGE = "QA reopen: the problem came back"
UNICODE_DESCRIPTION = "बिल सेव नहीं हो रहा 😟 QA"
REGEX_DESCRIPTION = "GST (sale"
REFUSAL_MESSAGE = "QA refusal from the stub"

ATTACHMENT_LIMIT_BYTES = 2 * 1024 * 1024
