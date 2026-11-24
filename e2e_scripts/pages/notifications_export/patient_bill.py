"""A chemist cash sale bill made out to a patient, as the prescription reminder expects one after a
prescription falls due (KB careportal_enriched_v5.csv#d71970a8: the reminder shows "until a sale bill is
made"). Built from the chemist suite's own header, grid and footer."""

from playwright.sync_api import Page

from pages.components.sale_bill_header import SaleBillHeader
from pages.sale.chemist.sale_bill import SaleBill
from test_data.headers import CASH_ACCOUNT
from test_data.models import BillHeader, SaleItem


class PatientBill:
    def __init__(self, page: Page) -> None:
        self._header = SaleBillHeader(page)
        self._bill = SaleBill(page)

    def make(self, patient: str, item: SaleItem) -> None:
        self._header.open_document("sale bill")
        self._header.fill(BillHeader(party_name=CASH_ACCOUNT, patient_name=patient))
        self._bill.add_item(0, item.by_description())
        self._bill.save_and_expect_saved()
