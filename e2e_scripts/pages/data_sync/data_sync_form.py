"""The public `/datasync` route, "Online Data Sync From Server" (J35 DS-23).

The whole form is `[hidden]="!isElectron"`, so the web app keeps it in the page but never shows it
(`data-sync.component.html:2-3`, `:84`; route `app-routing.module.ts:191`). The component also asks for an
`NgbActiveModal`, which a routed component may not get (`data-sync.component.ts:46`); if it fails to build,
the form is missing altogether and the attached-check below fails. DRAFT: from the Angular source.
"""

from playwright.sync_api import Locator, expect

from pages.base_page import BasePage

PATH = "/datasync"
TITLE = "Online Data Sync From Server"
FORM_TIMEOUT_MS = 60_000
# Why CSS: the hidden form has no accessible name and hidden elements have no role; its id is the only handle.
FORM = "form#dataSyncForm"


class DataSyncForm(BasePage):
    def open(self) -> None:
        self.goto(PATH, FORM_TIMEOUT_MS)

    @property
    def form(self) -> Locator:
        return self.page.locator(FORM)

    def expect_built_but_hidden(self) -> None:
        expect(self.form).to_be_attached(timeout=FORM_TIMEOUT_MS)
        expect(self.form).to_be_hidden()
        expect(self.page.get_by_text(TITLE)).to_be_hidden()
