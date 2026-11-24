"""J37 saving the create-store form: the own Online Store (OS-04/05/06) and Marg Mart registration (OS-07).

Creating a store has no delete, so OS-04 is the one test that saves for real and is marked `permanent`. The
others answer the save with a stub and run on a page whose creation writes are guarded: nothing is created.
"""

import re
from dataclasses import dataclass

import pytest

from pages.components.confirm_dialog import ConfirmDialog
from pages.components.stubbed_endpoint import StubbedEndpoint
from pages.online_store.create_store import MARG_MART_TAB, OWN_STORE_TAB, CreateStorePage, StoreField
from pages.online_store.marg_mart_portal import MargMartPortalStub
from pages.online_store.order_dashboard import OrderDashboard
from pages.online_store.store_endpoints import (
    BSS_MARG_MART_DATA,
    BSS_STORE_DATA_REPLY,
    MARG_MART_SAVE,
    MARG_MART_SAVED_REPLY,
    SAVE_ONLINE_STORE,
    STORE_REFUSED_REPLY,
    STORE_SAVED_REPLY,
)
from pages.stock.messages import StockMessages
from test_data.online_store import (
    MALFORMED_GSTIN,
    MARG_MART_REGISTRATION,
    MARG_MART_SOURCE,
    STORE_CREATED,
    STORE_NOT_CREATED,
)

pytestmark = [pytest.mark.p3, pytest.mark.journey("online-store")]

REGISTRATION_URL = re.compile(rf"^{re.escape(MARG_MART_REGISTRATION)}.+&{re.escape(MARG_MART_SOURCE)}$")


@dataclass(frozen=True)
class InvalidEntry:
    field: StoreField
    value: str
    name: str


INVALID_ENTRIES = [
    InvalidEntry(StoreField.STORE_NAME, "", "blank-store-name"),
    InvalidEntry(StoreField.MOBILE, "", "blank-mobile"),
    InvalidEntry(StoreField.EMAIL, "", "blank-email"),
    InvalidEntry(StoreField.GSTIN, MALFORMED_GSTIN, "malformed-gstin"),
]


@pytest.fixture
def store_save(guarded_store_form: CreateStorePage) -> StubbedEndpoint:
    endpoint = StubbedEndpoint(guarded_store_form.page, SAVE_ONLINE_STORE)
    endpoint.answer_with(STORE_SAVED_REPLY)
    return endpoint


@pytest.mark.permanent("an own Online Store on the company (SaveOnlineStore has no delete)")
def test_saving_the_online_store_tab_creates_the_store(create_store_page: CreateStorePage) -> None:
    """OS-04: "Store Created Successfully. Redirecting to dashboared..." and the order dashboard opens."""
    create_store_page.start()
    create_store_page.choose_tab(OWN_STORE_TAB)
    create_store_page.save()
    ConfirmDialog(create_store_page.page).expect_asking(STORE_CREATED)
    OrderDashboard(create_store_page.page).expect_open()


@pytest.mark.parametrize("entry", INVALID_ENTRIES, ids=lambda entry: entry.name)
def test_store_form_with_a_missing_or_malformed_field_is_not_saved(
    guarded_store_form: CreateStorePage, store_save: StubbedEndpoint, entry: InvalidEntry
) -> None:
    """OS-05: refused before SaveOnlineStore is called (MMT-005); no validators exist, so expected to fail."""
    guarded_store_form.choose_tab(OWN_STORE_TAB)
    guarded_store_form.fill(entry.field, entry.value)
    store_save.expect_none_during(guarded_store_form.save)


def test_failed_store_save_says_the_store_was_not_created(
    guarded_store_form: CreateStorePage, store_save: StubbedEndpoint
) -> None:
    """OS-06: a refused SaveOnlineStore shows "Store not Created" (D4: the code always reports success)."""
    store_save.answer_with(STORE_REFUSED_REPLY)
    guarded_store_form.choose_tab(OWN_STORE_TAB)
    store_save.capture_one(guarded_store_form.save)
    StockMessages(guarded_store_form.page).expect_shown(re.compile(re.escape(STORE_NOT_CREATED)))


def test_marg_mart_save_opens_the_margmart_registration(guarded_store_form: CreateStorePage) -> None:
    """OS-07: Marg Mart's Save opens margmart.com/vendor/#/registration?value=...&utm_source=MARGBOOKS.

    Marg's BSS server, `MargMart/Save` and margmart.com are all answered by stubs.
    """
    page = guarded_store_form.page
    StubbedEndpoint(page, BSS_MARG_MART_DATA).answer_with(BSS_STORE_DATA_REPLY)
    StubbedEndpoint(page, MARG_MART_SAVE).answer_with(MARG_MART_SAVED_REPLY)
    portal = MargMartPortalStub(page)
    portal.answer()
    guarded_store_form.choose_tab(MARG_MART_TAB)
    opened = portal.url_opened_by(guarded_store_form.save)
    assert REGISTRATION_URL.match(opened), opened
