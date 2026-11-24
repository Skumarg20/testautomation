"""The left-hand module menu: Purchase screens and the item master."""

from enum import Enum

from playwright.sync_api import Locator, expect

from pages.base_page import BasePage
from pages.purchase.documents.feedback import AppFeedback, appears_within

MENU_TIMEOUT_MS = 10_000
SETTLE_TIMEOUT_MS = 2_000
PURCHASE_GROUP = "Purchase"
MASTER_GROUP = "Master"
INVENTORY_MASTER = "Inventory Master"
ITEM_SCREEN = "Item"


class PurchaseScreen(Enum):
    ORDER = "Order"
    CHALLAN = "Challan"
    BILL = "Bill"
    RETURN = "Return"
    QUOTATION = "Quotation"
    STOCK_RECEIVE = "Stock Receive"


class ModuleMenu(BasePage):
    def open_purchase(self, screen: PurchaseScreen) -> None:
        self._expand_menu(PURCHASE_GROUP)
        self._expand(self._group(PURCHASE_GROUP))
        link = self._parent_link(screen.value)
        if not appears_within(link, SETTLE_TIMEOUT_MS):
            # Why: the menu can be a bar of icons although the group is listed; the toggle brings the labels.
            self.page.locator("span.lft-toggle-bar").click()
        link.click()
        self._settle()

    def open_item_master(self) -> None:
        self._expand_menu(MASTER_GROUP)
        self._expand(self._group(MASTER_GROUP))
        parent = self._parent_link(INVENTORY_MASTER)
        expect(parent).to_be_visible(timeout=MENU_TIMEOUT_MS)
        self._expand(parent)
        self._child_link(ITEM_SCREEN).click()
        self._settle()

    def _expand_menu(self, group: str) -> None:
        """A document screen leaves the side menu as a bar of icons; its toggle brings the labels back."""
        if not appears_within(self._group(group), SETTLE_TIMEOUT_MS):
            self.page.locator("span.lft-toggle-bar").click()

    @staticmethod
    def _expand(entry: Locator) -> None:
        """Opens a menu entry unless it is open already; clicking an open one would close it."""
        if "collapsed" in (entry.get_attribute("class") or ""):
            entry.click()

    def _group(self, name: str) -> Locator:
        # The sidebar is plain lists; entries are told apart by class and label only.
        return self.page.locator("li.grandParent > a").filter(has=self.page.get_by_text(name, exact=True))

    def _parent_link(self, name: str) -> Locator:
        label = self.page.get_by_text(name, exact=True)
        return self.page.locator("ul.collapse.show li.parent > a").filter(has=label).first

    def _child_link(self, name: str) -> Locator:
        return self.page.locator("li.child > a").filter(has=self.page.get_by_text(name, exact=True)).first

    def _settle(self) -> None:
        """Discards an unsaved-changes prompt or a form the app restored, then waits for the screen."""
        feedback = AppFeedback(self.page)
        feedback.confirm_if_asked()
        if appears_within(self.page.locator("div.frameModal"), SETTLE_TIMEOUT_MS):
            self.page.keyboard.press("Escape")
            feedback.confirm_if_asked()
        feedback.wait_for_loader()
