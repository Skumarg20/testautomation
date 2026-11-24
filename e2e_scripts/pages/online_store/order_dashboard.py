"""The order dashboard of the company's own Online Store (`/report/crm/E-Commerce/dashboard`, mode
"OnlinestoreNotMart"), from `Component/Master/E-Commerce/order-dashboard.component.html` and `.ts`.

Not yet seen live: every locator below comes from the template (spec "To verify live").
The grid is ag-Grid 19 (`#topGrid`); its cells carry the column's field as `col-id` (`.ts:422-462`).
The two filters are `select`s whose labels have `for=""`, so a filter is found through its form group.
"""

import re
from decimal import Decimal
from enum import Enum
from urllib.parse import parse_qs, urlparse

from playwright.sync_api import Locator, expect

from pages.base_page import BasePage
from pages.purchase.documents.feedback import AppFeedback, appears_within
from test_data.online_store import DASHBOARD_TITLE

DASHBOARD_TIMEOUT_MS = 60_000
SWITCH_PROBE_MS = 5_000
SWITCH_TO_OWN_STORE = "Switch to Online Store"
SWITCH_TO_MARG_MART = "Switch to MargMart"
QR_HEADING = "Scan QR Code"


class OrderColumn(Enum):
    ORDER_DATE = "orderDate"
    CUSTOMER = "customerName"
    ORDER_NO = "orderNo"
    STATUS = "statusCaption"
    QUANTITY = "totalOrderQty"
    AMOUNT = "orderAmount"


class StatusFilter(Enum):
    """Option captions of "Order Status" (`.html:708-713`)."""

    ALL = "All"
    PENDING = "Pending"
    CONVERTED = "Converted"
    REJECTED = "Order Rejected"


class OrderDashboard(BasePage):
    def expect_open(self) -> None:
        heading = self.page.get_by_role("heading", name=DASHBOARD_TITLE, exact=True)
        expect(heading).to_be_visible(timeout=DASHBOARD_TIMEOUT_MS)
        AppFeedback(self.page).wait_for_loader()

    def show_own_store(self) -> None:
        """A company with both stores opens in Marg Mart mode; its switch button leads to the own store."""
        self.expect_open()
        switch = self.page.get_by_role("button", name=SWITCH_TO_OWN_STORE)
        if appears_within(switch, SWITCH_PROBE_MS):
            switch.click()
        expect(self.switch_button).to_be_visible(timeout=DASHBOARD_TIMEOUT_MS)

    @property
    def switch_button(self) -> Locator:
        """In own Online Store mode the button offers the way back to Marg Mart (`.html:553-556`)."""
        return self.page.get_by_role("button", name=SWITCH_TO_MARG_MART)

    def show_status(self, status: StatusFilter) -> None:
        self._filter("Order Status").select_option(label=status.value)

    def show_every_vendor(self) -> None:
        self._filter("Vendor Type").select_option(label="All")
        AppFeedback(self.page).wait_for_loader()

    def chosen_vendor_type(self) -> str:
        # Why CSS: a select exposes its chosen option only through the :checked state.
        return self._filter("Vendor Type").locator("option:checked").inner_text().strip()

    def order_row(self, order_no: str) -> Locator:
        number_cell = self._cell_locator(OrderColumn.ORDER_NO).filter(
            has_text=re.compile(rf"^\s*{re.escape(order_no)}\s*$")
        )
        return self.page.get_by_role("row").filter(has=number_cell)

    def cell_text(self, order_no: str, column: OrderColumn) -> str:
        cell = self.order_row(order_no).locator(f'[col-id="{column.value}"]')
        expect(cell).to_be_visible(timeout=DASHBOARD_TIMEOUT_MS)
        return cell.inner_text().strip()

    def amount_of(self, order_no: str) -> Decimal:
        return Decimal(self.cell_text(order_no, OrderColumn.AMOUNT).replace(",", ""))

    def convert(self, order_no: str) -> None:
        self.convert_button(order_no).click()
        AppFeedback(self.page).wait_for_loader()

    def convert_button(self, order_no: str) -> Locator:
        """The "Convert To Order" column's button is captioned "Convert" (Shared/action.component.ts:221)."""
        return self.order_row(order_no).get_by_role("button", name="Convert", exact=True)

    def copy_store_link(self) -> None:
        self.page.get_by_role("button", name="Copy Store Link").click()

    def open_qr_code(self) -> None:
        self.page.get_by_role("button", name="Create QR code").click()

    @property
    def qr_heading(self) -> Locator:
        return self.page.get_by_role("heading", name=QR_HEADING)

    def close_qr_code(self) -> None:
        self._qr_popup.get_by_role("button", name="Close", exact=True).click()

    def qr_target_url(self) -> str:
        """The store URL the QR image encodes: its `data` parameter (order-dashboard.component.ts:1724)."""
        image_url = self._qr_popup.get_by_role("img", name="QR Code").get_attribute("src") or ""
        return parse_qs(urlparse(image_url).query).get("data", [""])[0]

    @property
    def marg_mart_switch_button(self) -> Locator:
        """Shown while the dashboard is in Marg Mart mode (`.html:553-556`)."""
        return self.page.get_by_role("button", name=SWITCH_TO_OWN_STORE)

    def open_manage_items(self) -> None:
        self.page.get_by_role("link").filter(has_text="Manage Item").click()
        AppFeedback(self.page).wait_for_loader()

    @property
    def _qr_popup(self) -> Locator:
        # Why CSS: the overlay is a plain div (no dialog role); its class is the only handle (`.html:536`).
        return self.page.locator(".qr-popup")

    def _filter(self, label: str) -> Locator:
        # Why CSS: the label has for="" (`.html:706,721`); the select is found in the label's form group.
        group = self.page.locator(".form-group").filter(has=self.page.get_by_text(label, exact=True))
        return group.get_by_role("combobox").first

    def _cell_locator(self, column: OrderColumn) -> Locator:
        # Why CSS: ag-Grid exposes only the col-id of a cell.
        return self.page.locator(f'#topGrid [col-id="{column.value}"]')
