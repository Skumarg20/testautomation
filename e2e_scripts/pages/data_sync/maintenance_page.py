"""The public `/error` route: "Website Under Maintenance", then a jump to `/login` (J35 DS-05, DS-06, DS-24).

`MrgHttpService.httpConnection` sends the web app here when a call fails with status 0 ("0 Unknown Error",
`MrgHttpService.service.ts:467-479`). On load the page calls a user-detail API and, when it answers, goes to
`/login` (`errorpage.component.ts:53-65`); the login screen then logs the session out on the server and
clears storage (`login.component.ts:336-343`). DRAFT: texts from the Angular source, not seen live.
"""

import re

from playwright.sync_api import expect

from pages.base_page import BasePage

PATH = "/error"
TITLE = "Website Under Maintenance"
APOLOGY = "We're Sorry! Web site is down for maintenance"
ERROR_TIMEOUT_MS = 30_000
LOGIN_TIMEOUT_MS = 60_000
LOGIN_ROUTE = re.compile(r"/login(?:[/?#]|$)")
ERROR_ROUTE = re.compile(rf"{PATH}(?:[/?#]|$)")


class MaintenancePage(BasePage):
    def open(self) -> None:
        self.goto(PATH)

    def reload(self) -> None:
        self.page.reload()

    def expect_shown(self) -> None:
        expect(self.page).to_have_url(ERROR_ROUTE, timeout=ERROR_TIMEOUT_MS)
        expect(self.page.get_by_role("heading", name=TITLE)).to_be_visible(timeout=ERROR_TIMEOUT_MS)
        expect(self.page.get_by_text(APOLOGY)).to_be_visible()

    def expect_sent_to_login(self) -> None:
        expect(self.page).to_have_url(LOGIN_ROUTE, timeout=LOGIN_TIMEOUT_MS)
