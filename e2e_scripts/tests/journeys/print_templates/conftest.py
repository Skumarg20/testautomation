"""Fixtures for the print template tests (J32): a garments session, the screen and test-owned templates."""

from collections.abc import Callable, Iterator

import pytest
from playwright.sync_api import Page

from config.settings import Account
from pages.company_switch_page import GARMENTS_COMPANY, CompanySwitchPage
from pages.dashboard_page import DashboardPage
from pages.print_templates.owned_templates import OwnedTemplates
from pages.print_templates.template_customize import TemplateCustomizePage

TEMPLATES_ACCOUNT: Account = "garments"


@pytest.fixture
def templates_page(page_as: Callable[[Account], Page]) -> Page:
    page = page_as(TEMPLATES_ACCOUNT)
    DashboardPage(page).open()
    # Templates belong to the company; the screens were observed on this one.
    CompanySwitchPage(page).ensure_company(GARMENTS_COMPANY)
    return page


@pytest.fixture
def templates(templates_page: Page, run_id: str) -> Iterator[OwnedTemplates]:
    owned = OwnedTemplates(templates_page, run_id)
    yield owned
    owned.delete_all()


@pytest.fixture
def customize(templates_page: Page) -> TemplateCustomizePage:
    return TemplateCustomizePage(templates_page)
