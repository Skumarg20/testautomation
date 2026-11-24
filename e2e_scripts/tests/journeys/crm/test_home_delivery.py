"""J36: Home Delivery, opened by URL (specs/crm-module.md, HD-01 and N2). Read only: no bill is assigned."""

import pytest

from pages.crm.home_delivery import HomeDelivery

pytestmark = [pytest.mark.p3, pytest.mark.journey("crm-module")]

DELIVERY_COLUMNS = ("Invoice No.", "Customer", "Amount", "Status", "Sale Person", "Delivery Date")


def test_home_delivery_opens_on_pending_bills(home_delivery: HomeDelivery) -> None:
    home_delivery.open()
    home_delivery.expect_showing("Pending")
    home_delivery.expect_columns(DELIVERY_COLUMNS)
    home_delivery.expect_assign_to_offered()


def test_delivered_bills_can_be_shown(home_delivery: HomeDelivery) -> None:
    home_delivery.open()
    home_delivery.show("Delivered")
    home_delivery.expect_showing("Delivered")
