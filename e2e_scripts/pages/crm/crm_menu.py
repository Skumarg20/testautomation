"""The CRM group of the left sidebar (specs/crm-module.md): which entries it has, and opening one."""

from playwright.sync_api import Locator, expect

from pages.accounting.accounting_menu import AccountingMenu

CRM_GROUP = "CRM"
LOYALTY_ENTRY = "Loyalty Management System"
PENDING_APPROVALS_ENTRY = "Pending Approvals"
MENU_TIMEOUT_MS = 30_000


class CrmMenu(AccountingMenu):
    def open_loyalty_setup(self) -> None:
        self._open(CRM_GROUP, (LOYALTY_ENTRY,))

    def open_pending_approvals(self) -> None:
        self._open(CRM_GROUP, (PENDING_APPROVALS_ENTRY,))

    def expect_entries(self, entries: tuple[str, ...]) -> None:
        """Exactly these entries, in this order, once the CRM group is expanded."""
        self._ensure_sidebar_open()
        self._expand_until_visible(self._group(CRM_GROUP), self._entries.first)
        expect(self._entries).to_have_text(list(entries), timeout=MENU_TIMEOUT_MS)

    @property
    def _entries(self) -> Locator:
        # Why CSS: the sidebar groups are plain list items with a class, no role or test id.
        section = self.page.locator("li.grandParent").filter(has_text=CRM_GROUP)
        return section.get_by_role("list").get_by_role("link")
