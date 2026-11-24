"""J21 sharing a report by WhatsApp and email (specs/notifications-export.md, NE-28..NE-30), on the Sale
Register. Every call that would upload a file for sharing or deliver a message is answered by a stub
(`StubbedEndpoint`), and each test proves its stub answered before it looks at the screen; the send guard
aborts anything no stub answers. Nothing reaches a person."""

import re

import pytest
from playwright.sync_api import Page

from pages.accounting.toasts import Toasts
from pages.components.stubbed_endpoint import StubbedEndpoint, StubReply
from pages.notifications_export.delivery_endpoints import EMAIL_SEND, WHATSAPP_SEND
from pages.notifications_export.email_draft import EmailDraft
from pages.notifications_export.json_route import success_envelope
from pages.notifications_export.report_share_export import SHARE_UPLOAD, ReportShareExport
from pages.notifications_export.sale_register_page import SaleRegisterPage
from test_data.notifications_export import QA_EMAIL, QA_WHATSAPP_NUMBER

pytestmark = [pytest.mark.p2, pytest.mark.journey("notifications-export")]

FAKE_LINK_ID = "QA-share-link"
ATTACHMENT_NOT_FOUND = re.compile(re.escape("Attachment file not found!"), re.IGNORECASE)
# Spelling as in the app (global.ts:19693).
WHATSAPP_SENT = re.compile(re.escape("Whastapp Sent Succesfully !"), re.IGNORECASE)
INVALID_EMAIL = re.compile(re.escape("Please enter a valid Email Id!"), re.IGNORECASE)
EMAIL_SENT = re.compile(re.escape("Email sent successfully."), re.IGNORECASE)


@pytest.fixture
def share(journey_page: Page) -> ReportShareExport:
    SaleRegisterPage(journey_page).open()
    return ReportShareExport(journey_page)


@pytest.fixture
def share_upload(journey_page: Page) -> StubbedEndpoint:
    return StubbedEndpoint(journey_page, SHARE_UPLOAD)


@pytest.fixture
def email_draft(journey_page: Page, share: ReportShareExport) -> EmailDraft:
    share.email_pdf()
    draft = EmailDraft(journey_page)
    draft.expect_open()
    return draft


def test_share_without_an_uploaded_file_says_attachment_not_found(
    share: ReportShareExport, share_upload: StubbedEndpoint, journey_page: Page
) -> None:
    """NE-28: when the upload returns no link, What's App > PDF stops with "Attachment file not found!"."""
    share_upload.answer_with(StubReply(success_envelope("")))

    share_upload.capture_one(share.share_pdf_on_whatsapp)

    Toasts(journey_page).expect_any_saying(ATTACHMENT_NOT_FOUND)


def test_whatsapp_share_sends_the_link_to_the_typed_number(
    share: ReportShareExport, share_upload: StubbedEndpoint, journey_page: Page
) -> None:
    """NE-30 (stubbed): What's App > PDF, number typed, Share: the send call carries that number and the app
    says it was sent. Notification/SendWhatsapp is answered by the stub."""
    share_upload.answer_with(StubReply(success_envelope(FAKE_LINK_ID)))
    whatsapp = StubbedEndpoint(journey_page, WHATSAPP_SEND)
    whatsapp.answer_with(StubReply(success_envelope(True)))
    share_upload.capture_one(share.share_pdf_on_whatsapp)
    share.expect_whatsapp_number_asked()

    sent = whatsapp.capture_one(lambda: share.share_with_whatsapp_number(QA_WHATSAPP_NUMBER))

    assert sent.json_body()["contactUser"] == QA_WHATSAPP_NUMBER
    Toasts(journey_page).expect_any_saying(WHATSAPP_SENT)


def test_email_without_a_recipient_is_refused_and_not_sent(
    email_draft: EmailDraft, journey_page: Page
) -> None:
    """NE-29: with no To address, Send says "Please enter a valid Email Id!" and posts nothing."""
    email_send = StubbedEndpoint(journey_page, EMAIL_SEND)
    email_send.answer_with(StubReply(success_envelope(None)))
    email_draft.clear_recipients()

    email_send.expect_none_during(email_draft.send)

    Toasts(journey_page).expect_any_saying(INVALID_EMAIL)


def test_email_share_sends_the_report_to_the_recipient(email_draft: EmailDraft, journey_page: Page) -> None:
    """NE-30 (stubbed): Send posts the PDF to the address typed (the prefilled real address is removed
    first) and the app says "Email sent successfully."."""
    email_send = StubbedEndpoint(journey_page, EMAIL_SEND)
    email_send.answer_with(StubReply(success_envelope(None)))
    email_draft.address_to(QA_EMAIL)

    sent = email_send.capture_one(email_draft.send)

    assert sent.json_body()["toemailid"] == QA_EMAIL
    Toasts(journey_page).expect_any_saying(EMAIL_SENT)
