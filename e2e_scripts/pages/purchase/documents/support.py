"""Shared set-up for the purchase tests."""

from collections.abc import Callable

from playwright.sync_api import Page

from config.settings import Account
from pages.company_switch_page import PHARMA_COMPANY, CompanySwitchPage
from pages.dashboard_page import DashboardPage
from test_data.document_cases import DocumentCase

ACCOUNT: Account = "chemist"  # the pharma company, on its own QA user


def open_dashboard(page_as: Callable[[Account], Page]) -> Page:
    """The ported cases use item 3 with a batch and expiry, so they run in the pharma company."""
    page = page_as(ACCOUNT)
    DashboardPage(page).open()
    CompanySwitchPage(page).ensure_company(PHARMA_COMPANY)
    return page


def positive(cases: list[DocumentCase]) -> list[DocumentCase]:
    return [case for case in cases if not case.is_negative]


def negative(cases: list[DocumentCase]) -> list[DocumentCase]:
    return [case for case in cases if case.is_negative]
