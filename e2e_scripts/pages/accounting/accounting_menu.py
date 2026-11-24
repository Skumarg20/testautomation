"""The left sidebar: opens an accounting voucher list or the ledger master list."""

import re
from itertools import pairwise
from typing import Literal

from playwright.sync_api import Locator

from pages.accounting.confirmation import Confirmation
from pages.accounting.loader import Loader
from pages.accounting.waiting import appears_within
from pages.base_page import BasePage

Screen = Literal["Receipt", "Payment", "Debit Note", "Credit Note", "Contra", "Journal"]
ACCOUNTING_GROUP = "Accounting Trans."
MASTER_GROUP = "Master"
LEDGER_PATH = ("Accounts Master", "Ledger")
BANK_RECONCILIATION = "Bank Reconciliation"
EXPAND_LOOKUP_MS = 2_000
SIDEBAR_LOOKUP_MS = 2_000
EXPAND_ATTEMPTS = 3
RESTORED_FORM_LOOKUP_MS = 1_000


class AccountingMenu(BasePage):
    def open_screen(self, screen: Screen) -> None:
        self._open(ACCOUNTING_GROUP, (screen,))

    def open_ledger_list(self) -> None:
        self._open(MASTER_GROUP, LEDGER_PATH)

    def open_bank_reconciliation(self) -> None:
        self._open(ACCOUNTING_GROUP, (BANK_RECONCILIATION,))

    def _open(self, group: str, path: tuple[str, ...]) -> None:
        self._ensure_sidebar_open()
        links = [self._group(group), *(self._link_in(group, name) for name in path)]
        for opener, target in pairwise(links):
            self._expand_until_visible(opener, target)
        links[-1].click()
        self._settle_after_navigation()

    def _group(self, group: str) -> Locator:
        return self.page.get_by_role("link", name=_link_name(group)).first

    def _link_in(self, group: str, name: str) -> Locator:
        # Why CSS: the sidebar groups are plain list items with a class, no role or test id.
        section = self.page.locator("li.grandParent").filter(has_text=group)
        return section.get_by_role("link", name=_link_name(name)).first

    def _ensure_sidebar_open(self) -> None:
        sidebar = self.page.locator("div.lft-cmp")
        if not appears_within(sidebar, SIDEBAR_LOOKUP_MS):
            self.page.locator("span.lft-toggle-bar").click()

    def _expand_until_visible(self, opener: Locator, target: Locator) -> None:
        for _ in range(EXPAND_ATTEMPTS):
            if appears_within(target, EXPAND_LOOKUP_MS):
                return
            opener.click()

    def _settle_after_navigation(self) -> None:
        confirmation = Confirmation(self.page)
        confirmation.answer_yes_if_asked()
        if appears_within(self._open_form, RESTORED_FORM_LOOKUP_MS):
            self.page.keyboard.press("Escape")
            confirmation.answer_yes_if_asked()
        Loader(self.page).wait_until_idle()

    @property
    def _open_form(self) -> Locator:
        # The router can restore a half-filled form after a reload; it is shown in this frame.
        return self.page.locator("div.frameModal")


def _link_name(label: str) -> re.Pattern[str]:
    """A sidebar link is named by its icon alt text plus its label, for example "Master Master"."""
    return re.compile(rf"^({re.escape(label)} )?{re.escape(label)}$")
