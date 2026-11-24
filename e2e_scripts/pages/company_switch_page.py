"""The organisation list (/user-company): which company and books year is active, and switching."""

import re

from playwright.sync_api import Locator, expect

from config.settings import studio_company
from pages.base_page import BasePage

SWITCH_TIMEOUT_MS = 60_000
# In Test Studio mode these stand for QA test companies (config.settings.STUDIO_COMPANY_MAP).
GARMENTS_COMPANY = studio_company("Garments New 29-08")
# The chemist company the ported purchase, sales and chemist cases need (items with batch and expiry).
PHARMA_COMPANY = studio_company("Pharma New Company 23-09")
BOOKS_PERIOD = re.compile(r"\d{2}-\d{2}-\d{4} to \d{2}-\d{2}-\d{4}")

STORED_COMPANY_NAME_SCRIPT = """
() => JSON.parse(
    localStorage.getItem('{"key":"LoggedInUserInfo","session":"mb-session"}')
).SelectedCompany.compname
"""


class CompanySwitchPage(BasePage):
    PATH = "/user-company"

    def open(self) -> None:
        self.goto(self.PATH)
        expect(self._organisation_rows.first).to_be_visible(timeout=SWITCH_TIMEOUT_MS)

    def current_company(self) -> str:
        return self._header_company.inner_text().strip()

    def current_year(self) -> str:
        return self._header_books_period.inner_text().strip()

    def switch_company(self, name: str) -> None:
        name = studio_company(name)
        self.open()
        self._organisation_row(name).dblclick()
        expect(self.page).to_have_url(re.compile("/dashboard"), timeout=SWITCH_TIMEOUT_MS)

    def ensure_company(self, name: str) -> None:
        """Tests are written against one company; the account opens in whichever it used last."""
        name = studio_company(name)
        if not self.current_company().startswith(name):
            self.switch_company(name)
            self.expect_header_company(name)

    def switch_year(self, label: str) -> None:
        """Each books year is its own organisation row (for example "25-26 Fy"), picked like a company."""
        self.switch_company(label)

    def search(self, text: str) -> None:
        self.page.get_by_role("searchbox", name="Search").fill(text)

    def expect_organisation_listed(self, name: str) -> None:
        expect(self._organisation_row(name).first).to_be_visible(timeout=SWITCH_TIMEOUT_MS)

    def expect_organisation_not_listed(self, name: str) -> None:
        expect(self._organisation_row(name)).to_have_count(0, timeout=SWITCH_TIMEOUT_MS)

    def open_from_profile_card(self) -> None:
        self.page.locator("#dropdownMenuButton").click()
        self.page.locator("#switchOnly").click()
        expect(self.page).to_have_url(re.compile(re.escape(self.PATH)), timeout=SWITCH_TIMEOUT_MS)

    def open_profile_card(self) -> None:
        self.page.locator("#dropdownMenuButton").click()
        expect(self._profile_card).to_be_visible(timeout=SWITCH_TIMEOUT_MS)

    def expect_profile_card_shows(self, company: str, books_period: str) -> None:
        expect(self._profile_card.get_by_role("heading", level=5)).to_have_text(company)
        expect(self._profile_card.get_by_text(f"F.Y. : {books_period}")).to_be_visible()

    def expect_profile_card_actions(self) -> None:
        for action in ("Switch", "Edit", "Logout"):
            expect(self._profile_card.get_by_text(action, exact=True)).to_be_visible()

    def stored_company_name(self) -> str:
        return str(self.page.evaluate(STORED_COMPANY_NAME_SCRIPT))

    def expect_header_company(self, name: str) -> None:
        expect(self._header_company).to_have_text(name, timeout=SWITCH_TIMEOUT_MS)

    @property
    def _organisation_rows(self) -> Locator:
        return self.page.get_by_role("row").filter(has=self.page.locator('[col-id="compname"]'))

    def _organisation_row(self, name: str) -> Locator:
        name_cell = self.page.locator('[col-id="compname"]').filter(
            has_text=re.compile(rf"^\s*{re.escape(name)}(\s|$)")
        )
        return self.page.get_by_role("row").filter(has=name_cell)

    @property
    def _profile_card(self) -> Locator:
        """The dropdown under the profile picture; it has no id, only the Switch button inside it."""
        return self.page.locator(".dropdown-menu").filter(has=self.page.locator("#switchOnly"))

    @property
    def _header_company(self) -> Locator:
        return self.page.locator("#txtheadercompname .cname")

    @property
    def _header_books_period(self) -> Locator:
        return self.page.locator("#dropdownMenuLink").get_by_text(BOOKS_PERIOD)
