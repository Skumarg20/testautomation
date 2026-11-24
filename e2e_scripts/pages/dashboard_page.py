import re

from playwright.sync_api import Locator, expect

from pages.base_page import BasePage

DASHBOARD_TIMEOUT_MS = 150_000


class NotAuthorizedPageError(AssertionError):
    def __init__(self, path: str) -> None:
        super().__init__(f"{path} rendered the app's not-authorized page")


class DashboardPage(BasePage):
    PATH = "/dashboard"

    def open(self) -> None:
        self.goto(self.PATH, DASHBOARD_TIMEOUT_MS)
        self.page.wait_for_load_state("load", timeout=DASHBOARD_TIMEOUT_MS)

    def expect_loaded(self) -> None:
        expect(self.page).to_have_url(re.compile(re.escape(self.PATH)), timeout=DASHBOARD_TIMEOUT_MS)

    def expect_menu_items(self, names: tuple[str, ...]) -> None:
        for name in names:
            expect(self._menu_link(name)).to_be_visible(timeout=DASHBOARD_TIMEOUT_MS)

    def log_out(self) -> None:
        self.page.locator("#dropdownMenuButton").click()
        self.page.get_by_text("Logout", exact=True).click()

    def expect_page_open(self, path: str, screen: Locator) -> None:
        """The page stayed at `path` and rendered `screen` (a locator only that screen has), not the app's
        not-authorized page. The check waits for whichever of the two appears first, because the absence of
        the error page right after the URL matched proves nothing: the route may not have rendered yet."""
        expect(self.page).to_have_url(re.compile(re.escape(path)), timeout=DASHBOARD_TIMEOUT_MS)
        not_authorized = self.page.locator("error-page h1")
        expect(screen.or_(not_authorized).first).to_be_visible(timeout=DASHBOARD_TIMEOUT_MS)
        if not_authorized.first.is_visible():
            raise NotAuthorizedPageError(path)

    def _menu_link(self, name: str) -> Locator:
        """The sidebar link is named by its icon alt text plus its label, for example "Master Master"."""
        return self.page.get_by_role("link", name=re.compile(rf"^{re.escape(name)}( {re.escape(name)})?$"))
