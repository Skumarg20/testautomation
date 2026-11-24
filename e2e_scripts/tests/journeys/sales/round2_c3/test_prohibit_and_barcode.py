"""Sale checklist row 29 (prohibited item) and row 95 (rate by barcode in the garments company).

Row 29, prohibited half: an item whose Agency is prohibited is taken out of the sale bill's item list
(`getLedgerItemListVisibilityAccToPermission`, Helper.services.ts:11763-11781, drops items whose
`itemcomplinkid` is in the prohibited-agency list while `userPowerSetting.prohibited` is on). The test makes
two agencies (one prohibited, one not) and one item under each, with no stock; Select Item must offer
the item of the open agency and not the other. Items and agencies are deleted afterwards.

Row 95, parameter (garments) barcode: the garments company's bill scans a barcode in its barcode cell; an item
the test made with barcode B and sale rate 150 gives a line whose amount is the sale rate (quantity 1).
"""

from collections.abc import Callable
from dataclasses import replace
from decimal import Decimal

import pytest
from playwright.sync_api import Page, expect

from config.settings import Account
from pages.company_switch_page import GARMENTS_COMPANY, PHARMA_COMPANY
from pages.components.bill_totals import BillTotals
from pages.dashboard_page import DashboardPage
from pages.masters.round2_c2.owned_items import OwnedItems
from pages.sale.documents.bill import SaleBillDocument
from pages.sale.documents.item_grid import PRODUCT
from pages.sale.documents.screen import exact_text
from pages.sale.garments.garments_sale_page import GarmentsSalePage
from pages.sale.round2_c3.agency_master import AgencyMaster
from pages.stock.search_typing import type_search
from test_data.factory import ITEM_SALE_RATE, DataFactory

pytestmark = [
    pytest.mark.p2,
    pytest.mark.journey("sale-bill-creation"),
    pytest.mark.xdist_group("chemist-tenant"),
]

GARMENTS: Account = "garments"
PICKER = "div.modal-dialog.modal-lg"


def test_item_of_a_prohibited_agency_is_not_offered_on_a_sale(
    company_page: Callable[[Account, str], Page], data: DataFactory, run_id: str
) -> None:
    """Row 29 (prohibited): the open agency's item is in Select Item, the prohibited agency's is not."""
    page = company_page("chemist", PHARMA_COMPANY)
    agencies = AgencyMaster(page)
    items = OwnedItems(page, data)
    banned, open_ = f"QA-{run_id}-Banned", f"QA-{run_id}-Open"
    try:
        agencies.create(banned, prohibited=True)
        agencies.create(open_, prohibited=False)
        banned_item = items.saved(replace(items.spec(), product=f"QA-{run_id}-BannedItem", company=banned))
        open_item = items.saved(replace(items.spec(), product=f"QA-{run_id}-OpenItem", company=open_))
        bill = SaleBillDocument(page)
        bill.open_new()
        bill.grid.cell(0, PRODUCT).click()
        page.keyboard.press("Enter")
        window = page.locator(PICKER)
        box = window.get_by_role("searchbox")

        type_search(box, open_item.product)
        listed = window.locator(".ag-cell-value").filter(has_text=exact_text(open_item.product))
        expect(listed.first).to_be_visible()
        type_search(box, banned_item.product)

        expect(
            window.locator(".ag-cell-value").filter(has_text=exact_text(banned_item.product))
        ).to_have_count(0)
    finally:
        BillTotals(page).leave_without_saving()
        items.delete_unused()
        agencies.delete_all()


def test_garments_barcode_gives_the_items_sale_rate(
    company_page: Callable[[Account, str], Page], data: DataFactory, run_id: str
) -> None:
    """Row 95 (parameter / barcode): scanning the barcode of a garments item made by the test puts it on the
    line at its sale rate of 150, quantity 1."""
    page = company_page(GARMENTS, GARMENTS_COMPANY)
    items = OwnedItems(page, data)
    barcode = f"9{int(run_id, 16) % 10**9:09d}"
    try:
        item = items.spec()
        items.saved_with_barcode(item, barcode)
        DashboardPage(page).open()
        sale = GarmentsSalePage(page)
        sale.open_new_bill()
        sale.choose_party("Ajay")

        sale.enter_barcode(0, barcode)

        assert sale.line_amount(0) == ITEM_SALE_RATE * Decimal(1)
        BillTotals(page).leave_without_saving()
    finally:
        items.delete_unused()
