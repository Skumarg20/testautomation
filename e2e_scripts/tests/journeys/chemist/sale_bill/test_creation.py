"""Chemist sale-bill creation: barcodes, batches, saving, dates and basic validation.

Ported from the original suite's creation.spec.ts. Flows with no clear expected result are skipped with
the question that needs an answer (Clean Code T4). The "billing off" fixtures are in ../conftest.py.
"""

import pytest
from playwright.sync_api import Page

from pages.sale.chemist.sale_bill import SaleBill
from pages.sale.manual import messages
from pages.sale.manual.bill_messages import BillMessages
from test_data.models import HeaderTag, ItemEntry
from test_data.sale_items import (
    A_TO_Z_NS,
    BIOZENTRA,
    CHEMIST_SALE_ITEMS,
    EXPIRED_BIOZENTRA,
    NEAR_EXPIRY_BIOZENTRA,
)

pytestmark = [
    pytest.mark.p0,
    pytest.mark.journey("sale-bill-creation"),
    pytest.mark.xdist_group("chemist-tenant"),
]


class TestAddItemsByBarcode:
    @pytest.mark.usefixtures("master_wise_barcodes")
    def test_master_barcode_adds_the_item_with_its_quantity(self, sale_bill: SaleBill) -> None:
        sale_bill.start()

        sale_bill.add_item(0, A_TO_Z_NS.by_barcode())

        assert sale_bill.quantity_of(0) == A_TO_Z_NS.quantity

    @pytest.mark.usefixtures("batch_wise_barcodes")
    def test_batch_barcode_adds_the_item_when_barcodes_are_batch_wise(self, sale_bill: SaleBill) -> None:
        sale_bill.start()

        sale_bill.add_item(0, A_TO_Z_NS.by_batch_barcode())

        assert sale_bill.quantity_of(0) == A_TO_Z_NS.quantity

    @pytest.mark.skip(
        reason="CR-03: the barcode design doc (onedrive:MARG BOOKS (2)/BARCODE/Barcode v1.0.1.docx#1.3) only "
        "says Master Wise barcodes are given in the Item Master; it does not say what a batch barcode does "
        "in that mode. The lookup builds its candidates from Item, Batch and BarCodeDetails barcodes alike "
        "(09-inventory-barcode-batch-serial.md K3, GetDataProc.xml:3181-3189), so the code may accept it, "
        "and an unknown barcode warns '<caption> Not Available' (Common.service.ts:3281-3292). Question: "
        "in Master Wise mode, should a batch barcode be refused with 'Not Available' or add its item?"
    )
    def test_batch_barcode_is_not_accepted_in_master_wise_mode(self) -> None: ...

    @pytest.mark.skip(
        reason="CR-04: one barcode on several items opens the item picker (14-cross-feature-interactions.md "
        "INT-09); the 'Multiple' mode is one item with several barcodes (onedrive:MARG BOOKS (2)/BARCODE/"
        "Barcode v1.0.1.docx#1.3). Still blocked on data: the QA tenant has no two items sharing a barcode "
        "and the picker has no locators (see tests/journeys/sales/manual/test_manual_blocked_cases.py)."
    )
    def test_multiple_barcodes_add_multiple_items(self) -> None: ...


@pytest.mark.usefixtures("master_wise_barcodes")
class TestMultipleBatches:
    def test_item_with_several_batches_lets_the_user_pick_a_batch(self, sale_bill: SaleBill) -> None:
        sale_bill.start()

        sale_bill.add_item(0, NEAR_EXPIRY_BIOZENTRA.by_description())

        assert sale_bill.quantity_of(0) == NEAR_EXPIRY_BIOZENTRA.quantity

    def test_near_expiry_batch_can_be_selected(self, sale_bill: SaleBill) -> None:
        sale_bill.start()
        near_expiry = ItemEntry(description=NEAR_EXPIRY_BIOZENTRA.description, expiry_type="NE", quantity=9)

        sale_bill.add_item(0, near_expiry)

        assert sale_bill.quantity_of(0) == near_expiry.quantity

    def test_expired_batch_shows_the_expired_warning(self, sale_bill: SaleBill) -> None:
        sale_bill.start()

        sale_bill.add_item(0, ItemEntry(description=EXPIRED_BIOZENTRA.description, expiry_type="EXP"))


@pytest.mark.usefixtures("master_wise_barcodes")
class TestSavingABill:
    def test_bill_by_barcode_is_saved(self, sale_bill: SaleBill) -> None:
        sale_bill.start()
        sale_bill.add_item(0, A_TO_Z_NS.by_barcode())

        sale_bill.save_and_expect_saved()

    def test_bill_by_item_code_is_saved(self, sale_bill: SaleBill) -> None:
        sale_bill.start()
        sale_bill.add_item(0, BIOZENTRA.by_item_code())

        sale_bill.save_and_expect_saved()

    def test_bill_by_description_is_saved(self, sale_bill: SaleBill) -> None:
        sale_bill.start()
        sale_bill.add_item(0, A_TO_Z_NS.by_description())

        sale_bill.save_and_expect_saved()

    def test_bill_with_items_added_three_different_ways_is_saved(self, sale_bill: SaleBill) -> None:
        sale_bill.start()
        sale_bill.add_items([item.entry() for item in CHEMIST_SALE_ITEMS])

        sale_bill.save_and_expect_saved()


@pytest.mark.usefixtures("master_wise_barcodes")
class TestBillDates:
    @pytest.mark.usefixtures("sale_future_date_billing_off")
    def test_future_date_is_rejected_when_future_billing_is_off(
        self, sale_bill: SaleBill, chemist_page: Page
    ) -> None:
        # KB: careportal:309030 (a future date is picked only with 'Sale Future Date Billing' = Yes);
        # KB: global.ts:19801 'Future Date Billing Not Allowed' (13-configuration-and-number-series.md M12)
        sale_bill.start(HeaderTag.FUTURE_DATE_NOT_ALLOWED)

        BillMessages(chemist_page).expect_warning(messages.FUTURE_DATE_REFUSED)

    @pytest.mark.usefixtures("sale_back_date_billing_off")
    def test_back_date_is_rejected_when_back_billing_is_off(
        self, sale_bill: SaleBill, chemist_page: Page
    ) -> None:
        # KB: careportal:297065 (back date billing is enabled per setting/role);
        # KB: processout.transaction.component.ts:1815 'Back Date Billing Not Allowed'
        sale_bill.start(HeaderTag.BACK_DATE_NOT_ALLOWED)

        BillMessages(chemist_page).expect_warning(messages.BACK_DATE_REFUSED)

    @pytest.mark.usefixtures("sale_back_date_billing")
    def test_bill_with_a_back_date_is_saved_when_back_billing_is_on(self, sale_bill: SaleBill) -> None:
        sale_bill.start(HeaderTag.BACK_DATE_ALLOWED)
        sale_bill.add_item(0, A_TO_Z_NS.entry())

        sale_bill.save_and_expect_saved()

    @pytest.mark.usefixtures("sale_future_date_billing")
    def test_bill_with_a_future_date_is_saved_when_future_billing_is_on(self, sale_bill: SaleBill) -> None:
        sale_bill.start(HeaderTag.FUTURE_DATE_ALLOWED)
        sale_bill.add_item(0, A_TO_Z_NS.entry())

        sale_bill.save_and_expect_saved()


class TestQuantityValidation:
    def test_zero_quantity_is_rejected(self, sale_bill: SaleBill, chemist_page: Page) -> None:
        # KB: template.sale.decimalformat.ts:658 (AlertMsg.saleBillQty, global.ts:18995) and
        # transactionin.component.ts:7804 (CheckQtyOrFree: quantity 0 and no free is refused)
        sale_bill.start()

        sale_bill.add_item(0, ItemEntry(description=A_TO_Z_NS.description, quantity=0))

        BillMessages(chemist_page).expect_warning(messages.QUANTITY_REQUIRED)
