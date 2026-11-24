"""J41 ticket attachment (SH-21 to SH-24). The files are built in memory; nothing is saved."""

import re

import pytest
from playwright.sync_api import FilePayload, Page

from pages.accounting.toasts import Toasts
from pages.support.ticket_modal import TicketModal
from test_data.support import ATTACHMENT_LIMIT_BYTES

pytestmark = [pytest.mark.p3, pytest.mark.journey("support-helpdesk")]

TOO_BIG = re.compile(re.escape("Maximum file size allowed is 2 MB."))
NOT_AN_IMAGE = re.compile(re.escape("Invalid image format. Only jpg/jpeg/png format is supported."))
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def _file(name: str, size: int) -> FilePayload:
    return {"name": name, "mimeType": "application/octet-stream", "buffer": b"\0" * size}


def _small_png() -> FilePayload:
    return {"name": "qa-screen.png", "mimeType": "image/png", "buffer": PNG_SIGNATURE}


# SH-21
def test_file_over_2_mb_is_refused_with_a_warning(guarded_page: Page, create_modal: TicketModal) -> None:
    create_modal.attach(_file("qa-too-big.png", ATTACHMENT_LIMIT_BYTES + 1))

    Toasts(guarded_page).expect_any_saying(TOO_BIG)


# SH-21
def test_file_over_2_mb_is_not_attached(create_modal: TicketModal) -> None:
    create_modal.attach(_file("qa-too-big.png", ATTACHMENT_LIMIT_BYTES + 1))

    create_modal.expect_nothing_attached()


# SH-22
def test_file_of_exactly_2_mb_is_attached(create_modal: TicketModal) -> None:
    create_modal.attach(_file("qa-limit.png", ATTACHMENT_LIMIT_BYTES))

    create_modal.expect_attached("qa-limit.png")


# SH-22
def test_small_png_is_attached(create_modal: TicketModal) -> None:
    create_modal.attach(_small_png())

    create_modal.expect_attached("qa-screen.png")


# SH-23
def test_marg_backup_file_is_refused_with_a_warning(guarded_page: Page, create_modal: TicketModal) -> None:
    create_modal.attach(_file("backup.mbk", len(PNG_SIGNATURE)))

    Toasts(guarded_page).expect_any_saying(NOT_AN_IMAGE)


# SH-23
def test_marg_backup_file_is_not_attached(create_modal: TicketModal) -> None:
    create_modal.attach(_file("backup.mbk", len(PNG_SIGNATURE)))

    create_modal.expect_nothing_attached()


# SH-24 (D6: the code accepts any type but .mbk while its message says images only; the pack's expected
# value is the code's behaviour until a human decides the rule)
@pytest.mark.parametrize("name", ["qa-invoice.pdf", "qa-logs.zip"])
def test_non_image_file_is_attached(create_modal: TicketModal, name: str) -> None:
    create_modal.attach(_file(name, len(PNG_SIGNATURE)))

    create_modal.expect_attached(name)
