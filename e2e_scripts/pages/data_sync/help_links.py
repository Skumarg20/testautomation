"""Header links that need the internet: the care portal in the Help window and the Pharma Free Drug Helpline
(J35 DS-09). Both check `noInternetConnection` first and warn "Internet Required for this option!"
(`homelayout.component.ts:2682-2687`, `:2785-2790`).

Help icon: `a[title=Help]` (`homeLayout.component.html:841-842`); its window has "Visit portal"
(`:3180`). Drug Helpline: `a[title="Pharma Free Drug Helpline"]`, only for business type 5 or 13 with plan
right C000123, and `d-lg-block` (`:784-787`). Opening the Help window saves a user-activity row
(`homelayout.component.ts:1379-1393`), so it is opened while online.
DRAFT: written from the Angular source, not seen live.
"""

import re

from playwright.sync_api import Locator, expect

from pages.base_page import BasePage

HELP = "Help"
VISIT_PORTAL = "Visit portal"
DRUG_HELPLINE = "Pharma Free Drug Helpline"
PHARMA_NXT_ROUTE = re.compile(r"/pharmanxt(?:[/?#]|$)")
WINDOW_TIMEOUT_MS = 15_000
# Why CSS: the Help window is a plain div with no role or heading name (homeLayout.component.html:3088).
HELP_WINDOW = "div.help-window"


class HelpLinks(BasePage):
    def open_help_window(self) -> None:
        self.page.get_by_role("link", name=HELP, exact=True).click()
        expect(self.visit_portal).to_be_visible(timeout=WINDOW_TIMEOUT_MS)

    @property
    def visit_portal(self) -> Locator:
        return self.page.locator(HELP_WINDOW).get_by_role("link", name=VISIT_PORTAL)

    @property
    def drug_helpline(self) -> Locator:
        # Why title: the link has no href (not a link role) and its only name is the title attribute.
        return self.page.get_by_title(DRUG_HELPLINE, exact=True)

    def expect_not_on_pharma_nxt(self) -> None:
        expect(self.page).not_to_have_url(PHARMA_NXT_ROUTE)
