"""Self-contained checks that the framework works. No MargBooks app required."""

import pytest
from playwright.sync_api import Page, expect

from pages.login_page import LoginPage
from test_data.factory import DataFactory

pytestmark = pytest.mark.framework

SINGLE_STEP_FORM_HTML = """
    <input id="userid"><input id="password" type="password">
    <button id="btnSave"
        onclick="document.title = 'single:' + userid.value + ':' + password.value">Login</button>
"""

TWO_STEP_FORM_HTML = """
    <input id="userid">
    <button id="SIGNin" onclick="document.getElementById('second').style.display = 'block'">SIGN IN</button>
    <div id="second" style="display: none">
        <input id="password" type="password">
        <button type="submit"
            onclick="document.title = 'two:' + userid.value + ':' + password.value">Go</button>
    </div>
"""


def test_party_names_are_tagged_with_run_id_and_distinct() -> None:
    factory = DataFactory("abc123")

    assert factory.party_name() == "QA-abc123-Party-1"
    assert factory.party_name() == "QA-abc123-Party-2"


def test_valid_gstin_has_fifteen_characters() -> None:
    assert len(DataFactory("run").valid_gstin()) == 15


def test_invalid_gstin_differs_from_valid_only_in_check_character() -> None:
    factory = DataFactory("run")

    valid, invalid = factory.valid_gstin(), factory.invalid_gstin()

    assert valid[:-1] == invalid[:-1]
    assert valid[-1] != invalid[-1]


def test_single_step_login_fills_user_and_password_then_saves(page: Page) -> None:
    page.set_content(SINGLE_STEP_FORM_HTML)

    LoginPage(page, style="single_step").sign_in("qa@example.com", "secret")

    expect(page).to_have_title("single:qa@example.com:secret")


def test_two_step_login_reveals_password_after_user_id(page: Page) -> None:
    page.set_content(TWO_STEP_FORM_HTML)

    LoginPage(page, style="two_step").sign_in("qa@example.com", "secret")

    expect(page).to_have_title("two:qa@example.com:secret")
