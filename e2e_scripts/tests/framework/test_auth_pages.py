import pytest
from playwright.sync_api import Page, expect

from pages.company_switch_page import CompanySwitchPage
from pages.dashboard_page import DashboardPage
from pages.login_page import LoginPage

pytestmark = pytest.mark.framework

LOGIN_HTML = """
<input id="userid"><button id="SIGNin">SIGN IN</button>
<input id="password" type="password" style="display:none">
<button type="submit">CONTINUE</button>
<div class="toast">Please Enter Password</div>
"""
MENU_HTML = """
<a href="#a"><img alt="Master"> Master</a><a href="#b">Dashboard</a>
<a id="dropdownMenuButton" href="#c" onclick="document.body.dataset.menu='open'">profile</a>
<a href="#d" onclick="document.body.dataset.out='yes'">Logout</a>
"""
COMPANY_HTML = """
<input type="search" aria-label="Search" id="SearchBox">
<div role="row"><div col-id="compname">Garments New 29-08 (GANE29)</div></div>
"""


def test_login_page_shows_a_message_and_the_password_step(page: Page) -> None:
    page.set_content(LOGIN_HTML)
    login_page = LoginPage(page, style="two_step")

    login_page.expect_message("Please Enter Password")

    expect(login_page.password).to_be_hidden()


def test_login_step_one_types_the_user_id(page: Page) -> None:
    page.set_content(LOGIN_HTML)

    LoginPage(page, style="two_step").continue_with_user("someone")

    expect(page.locator("#userid")).to_have_value("someone")


def test_dashboard_finds_menu_links_by_icon_and_label(page: Page) -> None:
    page.set_content(MENU_HTML)

    DashboardPage(page).expect_menu_items(("Master", "Dashboard"))


def test_dashboard_logout_clicks_the_logout_item(page: Page) -> None:
    page.set_content(MENU_HTML)

    DashboardPage(page).log_out()

    assert page.evaluate("document.body.dataset.out") == "yes"


def test_company_search_types_into_the_search_box(page: Page) -> None:
    page.set_content(COMPANY_HTML)

    CompanySwitchPage(page).search("Garm")

    expect(page.get_by_role("searchbox", name="Search")).to_have_value("Garm")


def test_company_row_is_found_by_name_prefix(page: Page) -> None:
    page.set_content(COMPANY_HTML)

    CompanySwitchPage(page).expect_organisation_listed("Garments New 29-08")


def test_company_row_absent_is_detected(page: Page) -> None:
    page.set_content(COMPANY_HTML)

    CompanySwitchPage(page).expect_organisation_not_listed("Pharma")
