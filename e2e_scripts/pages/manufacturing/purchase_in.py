"""MF-32: a purchase bill of one of this run's items on GANE29, saved before a conversion of the same day.

Reuses the garments purchase window (pages/purchase/garments/purchase_bill_page.py, seen live with supplier
"Payable" by J05). That journey never saves; the save toast and deleting the bill from Purchase > Bill by
its invoice number are unverified live.
"""

from dataclasses import dataclass

from playwright.sync_api import Page

from pages.dashboard_page import DashboardPage
from pages.purchase.documents.document_list import DocumentList
from pages.purchase.documents.feedback import AppFeedback, ToastKind
from pages.purchase.documents.navigation import ModuleMenu, PurchaseScreen
from pages.purchase.garments.purchase_bill_page import GarmentsPurchaseLine, PurchaseBillPage

# An intra-state supplier on GANE29 (tests/journeys/purchase/test_purchase_itc.py, seen live).
SUPPLIER = "Payable"
SAVE_TIMEOUT_MS = 60_000


@dataclass(frozen=True)
class PurchaseIn:
    invoice_number: str
    line: GarmentsPurchaseLine


def save_purchase(page: Page, purchase: PurchaseIn) -> None:
    DashboardPage(page).open()
    bill = PurchaseBillPage(page)
    bill.open()
    bill.choose_supplier(SUPPLIER)
    bill.start_manual_entry()
    bill.enter_invoice_number_and_date(purchase.invoice_number)
    bill.add_garments_line(0, purchase.line)
    bill.save()
    feedback = AppFeedback(page)
    feedback.confirm_if_asked()
    feedback.expect_toast(ToastKind.SUCCESS, SAVE_TIMEOUT_MS)


def delete_purchase(page: Page, purchase: PurchaseIn) -> None:
    DashboardPage(page).open()
    ModuleMenu(page).open_purchase(PurchaseScreen.BILL)
    DocumentList(page).delete(purchase.invoice_number)
