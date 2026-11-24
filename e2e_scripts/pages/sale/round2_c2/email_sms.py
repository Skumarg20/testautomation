"""Sending a sale bill by e-mail or SMS, with every send answered by a stub and recorded.

Sources (newmarg-webangular20/src/app):
- List > Email button: processout.list.component.ts:1305-1316 (SendEmails), :1387-1408 (GetBillsData runs
onEmail(1)
  per selected bill); a party with an e-mail id goes through Common.service.ts:2122-2136 and :2187-2225 (posts
  PrintTemplate/PrintTemplatePath, then Send posts Template/TriggerMail, :2243-2258). A party without one
  warns
  "Email Not Verified" (global.ts:19525).
- Save drop-down of the bill: "Save & SMS" (processout.transaction.component.ts:577-583, :1148-1160); after
the
  save onSMS(1) (:15385-15440) warns "Mobile no not found." without a number (global.ts:19327) and otherwise
  posts RegisterUser/SendSMSTemplate (Common.service.ts:2277-2350, global.ts:472).
Part C2 owns this module.
"""

import re
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from decimal import Decimal

from playwright.sync_api import Page

from pages.accounting.outstanding.sale_bill_desk import SaleBillDesk
from pages.components.stubbed_endpoint import AnsweredRequest, StubbedEndpoint, StubReply
from pages.notifications_export.json_route import success_envelope
from pages.sale.manual.bill_list_share import SaleBillListShare
from pages.settings.control_room_state import ControlRoomState
from pages.settings.control_room_switch import SwitchValue, switch_held

TRIGGER_MAIL = re.compile(r"Template/(TriggerMail|multiEmailTrigger)", re.IGNORECASE)
SEND_SMS = re.compile(r"RegisterUser/SendSMSTemplate", re.IGNORECASE)
PRINT_PATH = re.compile(r"PrintTemplate/PrintTemplatePath", re.IGNORECASE)
SEND_GUARD = re.compile(
    r"(Template/(TriggerMail|multiEmailTrigger|SendEmailPdfExcel)"
    r"|RegisterUser/(SendSMSTemplate|SendBulkSMSTemplate))",
    re.IGNORECASE,
)
MOBILE_NOT_FOUND = re.compile(r"Mobile no not found", re.IGNORECASE)
EMAIL_SENT = re.compile(r"Email send successfully", re.IGNORECASE)
MOBILE_MANDATORY = "Mobile Number Mandatory in Ledger"
SAVE_AND_SMS = "Save & SMS"
BASELINE_FIRST_EMPTY_ROW = 1
BARCODE_COLUMN = "tmp_barcode"


class RecordingStub(StubbedEndpoint):
    """A stubbed endpoint that also lets the test read what the screen posted."""

    @property
    def answered(self) -> list[AnsweredRequest]:
        return list(self._answered)


@dataclass(frozen=True)
class SentMail:
    email: str
    party: str
    body: str
    bill_link_id: str


def sent_mail(request: AnsweredRequest) -> SentMail:
    """Reads a Template/TriggerMail post with case-blind keys (emailid, userName, body,
    InvoiceExportReport)."""
    fields = {key.lower(): value for key, value in request.json_body().items()}
    report = {key.lower(): value for key, value in (fields.get("invoiceexportreport") or {}).items()}
    return SentMail(
        str(fields.get("emailid", "")),
        str(fields.get("username", "")),
        str(fields.get("body", "")),
        str(report.get("billlinkid", "")),
    )


def stub_mail_and_sms(page: Page) -> tuple[RecordingStub, RecordingStub]:
    """Routes the mail and SMS sends (and the PDF-link call before a mail) to stubs; returns (mail, sms)."""
    mail = RecordingStub(page, TRIGGER_MAIL)
    mail.answer_with(StubReply(success_envelope(True)))
    sms = RecordingStub(page, SEND_SMS)
    sms.answer_with(StubReply(success_envelope(True)))
    link = RecordingStub(page, PRINT_PATH)
    link.answer_with(StubReply(success_envelope("QA-STUB-LINK")))
    return mail, sms


def amount_in(body: str, amount: Decimal) -> bool:
    """True when the mail text carries the amount with two decimals (the list passes toFixed(decimals))."""
    return f"{amount:.2f}" in body


class ShareOnSaveDesk(SaleBillDesk):
    """Saves a one-line bill through the Save drop-down instead of the plain Save button."""

    def create_with_save_action(self, party: str, amount: Decimal, action: str) -> str:
        self._start(party, amount)
        self._choose_save_action(action)
        self._payment.expect_open()
        self._save_payment()
        return self._saved_number(party)

    def _choose_save_action(self, action: str) -> None:
        self._document.grid.cell(BASELINE_FIRST_EMPTY_ROW, BARCODE_COLUMN).click()
        self._page.keyboard.press("Tab")
        if self._document.selection.is_shown():
            self._page.keyboard.press("Escape")
        # Why CSS: the split button's arrow has no name; it is the only dropdown-toggle-split in the footer.
        self._page.locator("button.dropdown-toggle-split").locator("visible=true").last.click()
        self._page.locator(".dropdown-menu.show a.dropdown-item").filter(has_text=action).first.click()


def tick_first_bills(listed: SaleBillListShare, count: int) -> None:
    """Ticks the first `count` rows of the sale bill list with their selection boxes."""
    rows = listed.page.locator('[ref="eBodyContainer"] .ag-row')
    for index in range(count):
        # Why a class: ag-Grid draws the row's selection box as an icon only.
        rows.nth(index).locator(".ag-icon-checkbox-unchecked").first.click()


@contextmanager
def ledger_mobile_optional(page: Page) -> Iterator[None]:
    """Holds the tenant option "Mobile Number Mandatory in Ledger" (ledger.setting.html:96) at No, then puts
    it back. Tenant-wide: callers run in xdist group "chemist-tenant"."""
    access = ControlRoomState(page)
    with switch_held(access, SwitchValue(MOBILE_MANDATORY, "No")):
        yield
