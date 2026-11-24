"""The not-authorized page object finds the app's error-page heading by role, not by CSS."""

import pytest
from playwright.sync_api import Page, expect

from pages.components.not_authorized import NotAuthorizedPage

pytestmark = pytest.mark.framework

ERROR_PAGE_HTML = "<error-page><div><h1> Oops! You are not authorized. </h1></div></error-page>"


def test_not_authorized_heading_is_found_on_the_error_page(page: Page) -> None:
    page.set_content(ERROR_PAGE_HTML)

    NotAuthorizedPage(page).expect_shown()


def test_not_authorized_heading_is_absent_on_another_page(page: Page) -> None:
    page.set_content("<h1>Dashboard</h1>")

    expect(NotAuthorizedPage(page).heading).to_have_count(0)
