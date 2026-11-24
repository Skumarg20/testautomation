"""Fixtures for the Email / SMS / WhatsApp setup tests: a guarded garments session and the screens.

Every test runs under the outbound guard: a save or send request is aborted and fails the test.
"""

from collections.abc import Callable, Iterator

import pytest
from playwright.sync_api import Page

from config.settings import Account
from pages.communication_setup.communication_settings import CommunicationSettings
from pages.communication_setup.dlt_registration import DltRegistration
from pages.communication_setup.email_settings import EmailSettings
from pages.communication_setup.outbound_guard import OutboundGuard
from pages.communication_setup.transaction_messages import TransactionMessages
from pages.company_switch_page import GARMENTS_COMPANY, CompanySwitchPage
from pages.dashboard_page import DashboardPage

# The account and company the screens were observed on (specs/email-sms-whatsapp-setup.md).
COMMUNICATION_ACCOUNT: Account = "garments"


@pytest.fixture
def guarded_page(page_as: Callable[[Account], Page]) -> Iterator[Page]:
    page = page_as(COMMUNICATION_ACCOUNT)
    DashboardPage(page).open()
    CompanySwitchPage(page).ensure_company(GARMENTS_COMPANY)
    guard = OutboundGuard(page)
    guard.arm()
    yield page
    guard.expect_nothing_sent()


@pytest.fixture
def control_room(guarded_page: Page) -> CommunicationSettings:
    return CommunicationSettings(guarded_page)


@pytest.fixture
def email_settings(guarded_page: Page) -> EmailSettings:
    return EmailSettings(guarded_page)


@pytest.fixture
def dlt_registration(guarded_page: Page) -> DltRegistration:
    return DltRegistration(guarded_page)


@pytest.fixture
def transaction_messages(guarded_page: Page) -> TransactionMessages:
    return TransactionMessages(guarded_page)
