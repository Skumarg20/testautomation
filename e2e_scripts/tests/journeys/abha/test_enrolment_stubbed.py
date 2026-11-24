"""J39 ABHA enrolment after the OTP (AB-18..AB-20), class b: every ABDM call of the chain is a proven stub.

The `address_step` fixture types the fake mobile, OTP and the shown captcha, and proves that the enrolment
and the address-suggestion calls were answered by stubs before the create-address popup is looked at. Each
test stubs the address (and card) call it lets happen; an address the screen must refuse makes no call.
On the standalone screen a created address never saves to the tenant (`UpdateBill` runs only from the sale
bill, `abha-address.component.ts:95-99`), and the guard would abort `SaveAbhadetails` if it did.
"""

import pytest
from playwright.sync_api import expect

from pages.abha.abdm_endpoints import ADDRESS_CREATED_REPLY, ADDRESS_TAKEN_REPLY, CARD_REPLY
from pages.abha.address_popup import AbhaAddressPopup, AbhaCardPopup
from pages.abha.messages import ABHA_ADDRESS_CREATED, ABHA_ADDRESS_NOT_VALID, ABHA_ADDRESS_TAKEN
from pages.components.stubbed_endpoint import StubbedEndpoint
from pages.masters.master_toasts import MasterToasts
from test_data.abha import (
    ABHA_ADDRESS_STRIPPED,
    ABHA_ADDRESS_WITH_STRAY_CHARACTERS,
    FAKE_ABHA_ADDRESS,
    NO_SEPARATOR_ABHA_ADDRESS,
    SUGGESTED_ABHA_ADDRESSES,
    TOO_SHORT_ABHA_ADDRESS,
)

pytestmark = [pytest.mark.p3, pytest.mark.journey("abha-health-flows")]


@pytest.fixture
def created_address(
    address_step: AbhaAddressPopup, create_abha_address: StubbedEndpoint, abha_card: StubbedEndpoint
) -> AbhaAddressPopup:
    """The fake address saved through the stubbed address call; the card call it triggers is stubbed too."""
    create_abha_address.answer_with(ADDRESS_CREATED_REPLY)
    abha_card.answer_with(CARD_REPLY)
    address_step.type_address(FAKE_ABHA_ADDRESS)
    create_abha_address.capture_one(address_step.save)
    return address_step


def test_address_popup_offers_the_suggested_addresses(address_step: AbhaAddressPopup) -> None:
    for address in SUGGESTED_ABHA_ADDRESSES:
        address_step.expect_suggested(address)


def test_address_box_drops_characters_other_than_letters_digits_dot_and_underscore(
    address_step: AbhaAddressPopup,
) -> None:
    address_step.type_address(ABHA_ADDRESS_WITH_STRAY_CHARACTERS)

    expect(address_step.address_box).to_have_value(ABHA_ADDRESS_STRIPPED)


def test_too_short_address_is_refused_without_a_call(
    address_step: AbhaAddressPopup, create_abha_address: StubbedEndpoint
) -> None:
    address_step.type_address(TOO_SHORT_ABHA_ADDRESS)

    create_abha_address.expect_none_during(address_step.save)

    MasterToasts(address_step.page).expect_warning_saying(ABHA_ADDRESS_NOT_VALID)


def test_address_without_a_dot_or_underscore_is_refused_without_a_call(
    address_step: AbhaAddressPopup, create_abha_address: StubbedEndpoint
) -> None:
    address_step.type_address(NO_SEPARATOR_ABHA_ADDRESS)

    create_abha_address.expect_none_during(address_step.save)

    MasterToasts(address_step.page).expect_warning_saying(ABHA_ADDRESS_NOT_VALID)


def test_valid_address_is_sent_as_the_preferred_address(
    address_step: AbhaAddressPopup, create_abha_address: StubbedEndpoint, abha_card: StubbedEndpoint
) -> None:
    create_abha_address.answer_with(ADDRESS_CREATED_REPLY)
    abha_card.answer_with(CARD_REPLY)
    address_step.type_address(FAKE_ABHA_ADDRESS)

    sent = create_abha_address.capture_one(address_step.save).json_body()

    assert (sent["abhaAddress"], sent["preferred"]) == (FAKE_ABHA_ADDRESS, 1)


def test_taken_address_is_reported(
    address_step: AbhaAddressPopup, create_abha_address: StubbedEndpoint
) -> None:
    create_abha_address.answer_with(ADDRESS_TAKEN_REPLY)
    address_step.type_address(FAKE_ABHA_ADDRESS)
    create_abha_address.capture_one(address_step.save)

    MasterToasts(address_step.page).expect_warning_saying(ABHA_ADDRESS_TAKEN)


def test_created_address_is_confirmed(created_address: AbhaAddressPopup) -> None:
    MasterToasts(created_address.page).expect_success_saying(ABHA_ADDRESS_CREATED)


def test_created_address_opens_the_abha_card(
    address_step: AbhaAddressPopup, create_abha_address: StubbedEndpoint, abha_card: StubbedEndpoint
) -> None:
    create_abha_address.answer_with(ADDRESS_CREATED_REPLY)
    abha_card.answer_with(CARD_REPLY)
    address_step.type_address(FAKE_ABHA_ADDRESS)

    abha_card.capture_one(lambda: create_abha_address.capture_one(address_step.save))

    AbhaCardPopup(address_step.page).expect_card_shown()
