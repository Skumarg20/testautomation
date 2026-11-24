"""J35 data-sync-offline: what a lost bill save leaves behind on the server (DS-07 number part, DS-08).

DS-07: the save never left the browser (offline), so after signing in again the next bill number is the one
the lost bill showed (N3: other sessions saving on the same company in the meantime would move it; run in a
quiet window). DS-08: the server received the save but its answer was dropped; at most one bill may carry that
number, also after the user saves the bill again (pack DS-08, expected server idempotency UNVERIFIED).
Every test runs in its own form login, because the lost answer ends in the app's logout. DS-08 saves real
bills on the pharma company and deletes them afterwards.
DRAFT: written from the Angular source (specs/data-sync-offline.md), not run against the app yet.
"""

from collections.abc import Callable, Iterator

import pytest
from playwright.sync_api import Page

from pages.data_sync.connection import Connectivity
from pages.data_sync.lost_save import DroppedSaveAnswer, SaleBillCount
from pages.data_sync.maintenance_page import MaintenancePage
from pages.data_sync.offline_bill import OfflineBill
from pages.sale.documents.bill import SaleBillDocument

pytestmark = [pytest.mark.p3, pytest.mark.journey("data-sync-offline")]

AT_MOST_ONE_BILL = 1


@pytest.fixture
def bills_to_delete(own_login_page: Page) -> Iterator[list[str]]:
    """Bill numbers a test may have saved; each one still listed is deleted afterwards."""
    numbers: list[str] = []
    yield numbers
    count = SaleBillCount(own_login_page)
    for number in numbers:
        if count.bills_numbered(number):
            SaleBillDocument(own_login_page).delete(number)


@pytest.fixture
def dropped_save_number(
    filled_offline_bill: OfflineBill,
    sign_in_again: Callable[[], None],
    bills_to_delete: list[str],
) -> str:
    """The bill was saved with its answer dropped, the app logged out, and the user signed in again."""
    number = filled_offline_bill.number()
    bills_to_delete.append(number)
    dropped = DroppedSaveAnswer(filled_offline_bill.page)
    dropped.install()
    filled_offline_bill.save_with_keyboard()
    MaintenancePage(filled_offline_bill.page).expect_sent_to_login()
    dropped.remove()
    assert dropped.server_statuses, "DS-08: the save never reached the server, so nothing was dropped"
    sign_in_again()
    return number


def test_lost_offline_save_does_not_use_up_the_bill_number(
    own_login_page: Page, filled_offline_bill: OfflineBill, sign_in_again: Callable[[], None]
) -> None:
    lost_number = filled_offline_bill.number()
    Connectivity(own_login_page).go_offline()
    filled_offline_bill.save_with_keyboard()
    maintenance = MaintenancePage(own_login_page)
    maintenance.expect_shown()
    Connectivity(own_login_page).go_online()
    maintenance.reload()
    maintenance.expect_sent_to_login()
    sign_in_again()

    next_bill = OfflineBill(own_login_page)
    next_bill.fill()

    assert next_bill.number() == lost_number, (
        f"DS-07: the lost bill showed {lost_number}, the next bill shows {next_bill.number()} (see N3)"
    )


def test_save_with_a_dropped_answer_leaves_at_most_one_bill(
    own_login_page: Page, dropped_save_number: str
) -> None:
    listed = SaleBillCount(own_login_page).bills_numbered(dropped_save_number)

    assert listed <= AT_MOST_ONE_BILL, f"DS-08: {listed} bills carry number {dropped_save_number}"


def test_saving_again_after_a_dropped_answer_does_not_duplicate_the_number(
    own_login_page: Page, dropped_save_number: str, bills_to_delete: list[str]
) -> None:
    again = OfflineBill(own_login_page)
    again.fill()
    bills_to_delete.append(again.number())
    bill = SaleBillDocument(own_login_page)

    bill.save()
    bill.expect_saved()

    listed = SaleBillCount(own_login_page).bills_numbered(dropped_save_number)
    assert listed <= AT_MOST_ONE_BILL, (
        f"DS-08: {listed} bills carry number {dropped_save_number} after saving again"
    )
