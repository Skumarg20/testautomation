"""Stock row 31: after a sale and a return, the stock report is run and exported; it shows both documents.

The Item Register (detail of the stock summary, opened from the item list, `ItemLedger`) has the report
toolbar;
its Excel export of the Current View (Print Configuration) is the "printed" report. The export must list the
sale challan and the return, the sale first. Figures on the three screens are checked by
`tests/journeys/stock/sale_impact/test_batch_moves.py`. Toolbar on this screen: unverified live.
"""

from decimal import Decimal

import pytest

from pages.manufacturing.item_ledger import ItemLedger
from pages.notifications_export.downloads import saved_file
from pages.notifications_export.report_share_export import ReportShareExport
from pages.reports.gst_export import read_export
from pages.stock.sale_impact.documents import PRODUCT, sale_request
from pages.stock.sale_impact.shop import Shop

pytestmark = [pytest.mark.p2, pytest.mark.journey("inventory"), pytest.mark.xdist_group("chemist-tenant")]

SOLD = Decimal(2)
RETURNED = Decimal(1)


def test_exported_item_register_lists_the_sale_and_the_return(shop: Shop, batch: str) -> None:
    sale = shop.challan(sale_request(batch, SOLD))
    returned = shop.manual_return(sale_request(batch, RETURNED))

    ItemLedger(shop.page).open_for(PRODUCT)
    exported = read_export(saved_file(ReportShareExport(shop.page).export_excel_current_view()))

    lines = [" | ".join(row) for row in exported.rows]
    sale_at = next(i for i, line in enumerate(lines) if sale in line)
    return_at = next(i for i, line in enumerate(lines) if returned in line)
    assert sale_at < return_at
