"""Sale bill rows 148 and 152.

Row 148. The next bill number is the number of the latest not-deleted bill of the series plus one
(`VoucherCodeDal.cs:36-117`: `select top 1 entryNo ... isDelete=0 order by id desc`, then `+1`, padded).
So a number
freed by deleting the latest bill is given out again. Another user saving in between would break the test.
Row 152. With "Sale BackDate Billing" = No, a bill whose date is changed to yesterday after its line was
entered warns
"Back Date Billing Not Allowed" and the save is refused (`processout.transaction.component.ts:1815`, :10402,
:10456; dataCalculation.ts:2694): the list gains no bill.
"""

from collections.abc import Iterator
from datetime import date, timedelta
from decimal import Decimal

import pytest
from playwright.sync_api import Page

from pages.accounting.outstanding.document_list import DocumentList
from pages.dashboard_page import DashboardPage
from pages.sale.documents.bill import SaleBillDocument
from pages.sale.manual import messages
from pages.sale.manual.pharma_bill import PARTY, PharmaBill
from pages.sale.manual.saved_bills import SavedBills
from pages.settings.control_room_state import ControlRoomState
from pages.settings.control_room_switch import SwitchValue, switch_held

pytestmark = [
    pytest.mark.p1,
    pytest.mark.journey("sale-bill-creation"),
    pytest.mark.xdist_group("chemist-tenant"),
]

ONE = Decimal(1)


@pytest.fixture
def back_billing_off(sales_page: Page) -> Iterator[None]:
    switch = SwitchValue("Sale BackDate Billing", "No")
    with switch_held(ControlRoomState(sales_page), switch, DashboardPage(sales_page).open):
        yield


def test_number_of_a_deleted_latest_bill_is_given_out_again(
    bill: PharmaBill, saved_bills: SavedBills
) -> None:
    bill.start()
    bill.add_line(0, ONE)
    deleted = saved_bills.save(bill)
    SaleBillDocument(bill.page).delete(deleted)
    saved_bills.forget(deleted)

    bill.start()

    assert bill.document.document_number() == deleted
    bill.leave_without_saving()


@pytest.mark.usefixtures("back_billing_off")
def test_save_is_refused_when_the_date_is_moved_back(bill: PharmaBill) -> None:
    before = DocumentList(bill.page, SaleBillDocument.menu).numbers_for(PARTY)
    bill.start()
    bill.add_line(0, ONE)
    bill.document.enter_date(date.today() - timedelta(days=1))
    bill.messages.expect_warning(messages.BACK_DATE_REFUSED)

    bill.try_save()

    bill.messages.expect_warning(messages.BACK_DATE_REFUSED)
    bill.leave_without_saving()
    assert DocumentList(bill.page, SaleBillDocument.menu).numbers_for(PARTY) == before
