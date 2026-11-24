"""The Bill of Materials reports: Pending & Register, Costing and Production Planning.

Routes (report.module.ts:260-261, global.ts:20435-20437): `/report/bomreport/bomdefault` (Pending & Register,
opens "Select Party" for a Sundry Creditor (Manufacturer) ledger), `/report/bomreport/costing` (opens "Select
Item"), `/report/bomreport` (Production Planning: "Planning Type" `#txtplanningtype`, "Item" `#txtitem`, OK),
which leads to `/report/bomreport/prodplan`. Seen live 2026-10-12: only the Production Planning filter page.

The report columns come from the stored procedure `sp_Bomreport`, which is not in the API repo, so the col-ids
below are the column names the Angular code reads ("Required Qty", "Qty", "Value", "Cost",
billofmaterial.report.ts:113-118, 340-362); the Pending column is matched by "Pending" in its col-id.
All of this is unverified live.
"""

import re
from decimal import Decimal

from playwright.sync_api import Locator, expect

from pages.base_page import BasePage
from pages.manufacturing.voucher_checks import PartyWindow
from pages.purchase.documents.feedback import AppFeedback
from pages.purchase.documents.selection_window import SelectionWindow
from pages.stock.messages import StockMessages
from test_data.money import parse_amount

PENDING_REGISTER_PATH = "/report/bomreport/bomdefault"
COSTING_PATH = "/report/bomreport/costing"
PLANNING_PATH = "/report/bomreport"
FROM_CURRENT_STOCK = "From Current Stock"
ONLY_MANUFACTURER_LEDGERS = re.compile(r"Please Select Only 'Sundry Creditor \(Manufacturer\)' A/C Ledgers")
ROW_TIMEOUT_MS = 30_000


class BomReportGrid(BasePage):
    """The report body (`#reportGrid`) and its totals row (`#trialBalFoot`)."""

    def figure(self, product: str, column: str) -> Decimal:
        cell = self._row(product).locator(f'[col-id="{column}"]').first
        expect(cell).to_be_visible(timeout=ROW_TIMEOUT_MS)
        return parse_amount(cell.inner_text().strip())

    def pending_figure(self, product: str) -> Decimal:
        cell = self._row(product).locator('[col-id*="Pending" i]').first
        expect(cell).to_be_visible(timeout=ROW_TIMEOUT_MS)
        return parse_amount(cell.inner_text().strip())

    def total(self, column: str) -> Decimal:
        cell = self.page.locator("#trialBalFoot .ag-row").locator(f'[col-id="{column}"]').first
        expect(cell).to_be_visible(timeout=ROW_TIMEOUT_MS)
        return parse_amount(cell.inner_text().strip())

    def _row(self, product: str) -> Locator:
        # Why CSS: the report is an ag-Grid whose rows and cells are told apart only by col-id.
        grid = self.page.locator("#reportGrid")
        return grid.get_by_role("row").filter(has=self.page.get_by_text(product, exact=True)).first


class PendingRegister(BomReportGrid):
    def open_for(self, party: str) -> None:
        self.goto(PENDING_REGISTER_PATH)
        window = PartyWindow(self.page)
        window.pick(party)
        AppFeedback(self.page).wait_for_loader()

    def expect_only_manufacturer_ledgers_taken(self) -> None:
        StockMessages(self.page).expect_shown(ONLY_MANUFACTURER_LEDGERS)


class CostingReport(BomReportGrid):
    def open_for(self, finished_product: str) -> None:
        self.goto(COSTING_PATH)
        SelectionWindow(self.page).choose_cell_text(finished_product)
        AppFeedback(self.page).wait_for_loader()


class ProductionPlanning(BomReportGrid):
    def open_for(self, finished_product: str) -> None:
        self.goto(PLANNING_PATH)
        # Why ids: the filter page's labels are not tied to its selects (productionplanning.report.html).
        self.page.locator("#txtplanningtype").select_option(label=FROM_CURRENT_STOCK)
        self.page.locator("#txtitem").select_option(label=finished_product)
        self.page.get_by_role("button", name="OK").click()
        AppFeedback(self.page).wait_for_loader()

    def plan(self, sets: Decimal) -> None:
        """Types the planned quantity into "Planning For" and presses Enter, which recalculates
        (browserShortCut, billofmaterial.report.ts:307-311)."""
        cell = self.page.locator("#reportGrid1 .ag-row").locator('[col-id="quantity"]').first
        cell.click()
        field = cell.locator("input")
        field.fill(str(sets))
        field.press("Enter")
