"""J37 one company's online orders stay with that company (OS-28, OS-29).

An order is seeded on GANE29; the test then switches to a second company with its own Online Store
(PHARMA_COMPANY) and skips when it has none (spec N1).

OS-29 is an API scenario. It is scripted here, not under `tests/api/`, because the Online Store API takes the
company from the encrypted headers the app's interceptor builds per session (`order_api.py`): the `api`
fixture's client cannot sign in to it, so the test replays the second company's captured headers instead.
The call only targets this test's own seeded order.
"""

from collections.abc import Callable

import pytest
from playwright.sync_api import expect

from pages.online_store.order_api import OnlineStoreApi
from pages.online_store.order_dashboard import OrderColumn, OrderDashboard, StatusFilter
from test_data.online_store import PENDING, ListedOrder, SeededOrder

pytestmark = [pytest.mark.p3, pytest.mark.journey("online-store")]

OpenOtherStore = Callable[[], OnlineStoreApi]


def test_order_of_one_company_is_not_listed_for_another(
    dashboard: OrderDashboard, seeded_pending_order: SeededOrder, open_other_company_store: OpenOtherStore
) -> None:
    """OS-28: orders are filtered on complinkid / FulfillingCompanyLinkId (`OnlineStore.cs:320`)."""
    open_other_company_store()
    dashboard.show_every_vendor()
    dashboard.show_status(StatusFilter.ALL)
    expect(dashboard.order_row(seeded_pending_order.order_no)).to_have_count(0)


def test_other_company_cannot_change_the_status_of_an_order(
    listed_pending_order: ListedOrder,
    open_other_company_store: OpenOtherStore,
    reopen_own_store: Callable[[], OrderDashboard],
) -> None:
    """OS-29: StatusUpdationOfOnlineStore from another company must not touch the order.

    The update filters only on linkid and concatenates SQL (`OnlineStore.cs:570`): expected to fail.
    """
    open_other_company_store().mark_converted(listed_pending_order.link_id)
    dashboard = reopen_own_store()
    dashboard.show_every_vendor()
    dashboard.show_status(StatusFilter.ALL)
    assert dashboard.cell_text(listed_pending_order.order.order_no, OrderColumn.STATUS) == PENDING
