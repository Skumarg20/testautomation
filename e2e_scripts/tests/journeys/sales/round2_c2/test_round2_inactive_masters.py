"""Ajay rows 84 and 85: a Discontinued item and a Discontinued party are not offered in a sale bill.

Rule: in a transaction only master rows with Status = Continue are listed
(Services/Helper.services.ts:11728-11745 for ledgers, :11760-11772 for items). The test makes the master
itself (Status = Discontinue in the form / Other Info) so no QA data is needed.
"""

from decimal import Decimal

import pytest
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Page

from pages.components.bill_totals import BillTotals
from pages.masters.round2_c2.owned_items import OwnedItems
from pages.masters.round2_c2.owned_parties import OwnedParties
from pages.sale.documents.bill import SaleBillDocument
from pages.sale.garments.garments_sale_page import GarmentsSalePage

pytestmark = [pytest.mark.p2, pytest.mark.journey("sale-bill-creation")]


def test_discontinued_party_is_not_selectable(guarded_page: Page, parties: OwnedParties) -> None:
    party = parties.saved_discontinued()
    bill = SaleBillDocument(guarded_page)
    bill.open_new()

    with pytest.raises((AssertionError, PlaywrightError)):
        bill.choose_party(party.name)

    BillTotals(guarded_page).leave_without_saving()


def test_discontinued_item_is_not_offered_in_the_item_picker(guarded_page: Page, items: OwnedItems) -> None:
    item = items.saved_discontinued(items.spec())
    sale = GarmentsSalePage(guarded_page)
    sale.open_new_bill()
    sale.choose_party("Ajay")

    with pytest.raises((AssertionError, PlaywrightError)):
        sale.add_item(0, item.product, Decimal(1))

    BillTotals(guarded_page).leave_without_saving()
