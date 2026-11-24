"""Report > Sale Register (`/report/register/sale`, salepurchase.register.component.ts). Its Share menu is the
one report screen found whose What's App > PDF goes straight to the share upload (`mediaShare` is
`{isWoConfiguration: true}`, so share.component.ts:528 emits instead of saying "under development") and whose
Email entry opens the report's own mail draft (`emailPdfExcel = true`). Not seen live: see the spec.
"""

import re

from playwright.sync_api import expect

from pages.base_page import BasePage

PATH = "/report/register/sale"
TITLE = re.compile(r"^Sale Register")
LOAD_TIMEOUT_MS = 60_000


class SaleRegisterPage(BasePage):
    def open(self) -> None:
        self.goto(PATH, LOAD_TIMEOUT_MS)
        expect(self.page.get_by_role("heading", name=TITLE, level=1)).to_be_visible(timeout=LOAD_TIMEOUT_MS)
