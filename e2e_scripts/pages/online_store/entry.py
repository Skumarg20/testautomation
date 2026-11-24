"""Where the menu "Online Store" (`/other/onlinestore`) lands, and the menu entries that lead there.

`/other/onlinestore` is only a router (`Component/Online-Store/dashboard/onlineStoreDashboard.ts:69-87`): it
asks `MargMart/Get` and opens the order dashboard (Marg Mart or own Online Store mode) or, when the company
has neither store, `/other/createStore`. The dashboard keeps its mode in history state, so tests always go
through this router instead of deep-linking to the dashboard. Not yet seen live (spec "To verify live").
"""

import re
from enum import Enum

from playwright.sync_api import expect

from pages.base_page import BasePage
from pages.purchase.documents.navigation import ModuleMenu

ROUTER_PATH = "/other/onlinestore"
CREATE_STORE_PATH = "/other/createStore"
ORDER_DASHBOARD_PATH = "/report/crm/E-Commerce/dashboard"
LANDING_TIMEOUT_MS = 60_000
SALE_GROUP = "Sale"
ONLINE_ORDER_ENTRY = "Online Order"
ONLINE_STORE_ENTRY = "Online Store"


class StoreLanding(Enum):
    CREATE_STORE = CREATE_STORE_PATH
    ORDER_DASHBOARD = ORDER_DASHBOARD_PATH


class OnlineStoreEntry(BasePage):
    def open(self) -> StoreLanding:
        """Opens the router and answers where the company's store state sent it."""
        self.goto(ROUTER_PATH)
        return self.landing()

    def landing(self) -> StoreLanding:
        either = re.compile(f"{re.escape(CREATE_STORE_PATH)}|{re.escape(ORDER_DASHBOARD_PATH)}")
        expect(self.page).to_have_url(either, timeout=LANDING_TIMEOUT_MS)
        if CREATE_STORE_PATH in self.page.url:
            return StoreLanding.CREATE_STORE
        return StoreLanding.ORDER_DASHBOARD


class OnlineStoreMenu(ModuleMenu):
    def open_online_store(self) -> None:
        """Top-level menu "Online Store" (menumaster.json id 5467); a link without children."""
        self._expand_menu(ONLINE_STORE_ENTRY)
        self._group(ONLINE_STORE_ENTRY).click()
        self._settle()

    def open_online_order(self) -> None:
        """Sale > "Online Order" (AlterMainDBData.xml:484, MBC-17953)."""
        self._expand_menu(SALE_GROUP)
        self._expand(self._group(SALE_GROUP))
        self._parent_link(ONLINE_ORDER_ENTRY).click()
        self._settle()
