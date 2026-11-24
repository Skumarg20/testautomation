"""Fixtures for J39 abha-health-flows (specs/abha-health-flows.md).

Safety (pack safety frame): every page is armed with the shared SendGuard before its first navigation, set to
`ABDM_OR_ABHA_WRITE`. It aborts any call to the ABDM proxy, the consent connector or `SaveAbhadetails` and
fails the test in teardown. The ABDM session-token call every ABHA screen makes on load is answered by a
stub, and the screen fixtures prove that stub answered it before a test types anything. Tests that need an
OTP answer use the OTP endpoint fixtures; nothing reaches the gateway and no real identity is used
(`test_data/abha.py`).

Precondition (read, never changed): the chemist login's company PHARMA_COMPANY must be a chemist company
(business type 5) with Control Room field 4426 "Abha Id for pharmacy store" filled. Otherwise the ABHA tests
skip and name what is missing. The hidden-UI tests (AB-02, AB-03) need the opposite and skip likewise.
"""

from collections.abc import Callable, Iterator

import pytest
from playwright.sync_api import Page

from config.settings import Account
from pages.abha.abdm_endpoints import (
    ABDM_OR_ABHA_WRITE,
    ABHA_CARD,
    ADDRESS_LOGIN_OTP,
    ADDRESS_SUGGESTION,
    CREATE_ABHA_ADDRESS,
    ENROL_BY_AADHAAR,
    ENROLLED_REPLY,
    LOGIN_OTP,
    OTP_SENT_REPLY,
    PATIENT_ABHA_DETAILS,
    PATIENT_ABHA_DETAILS_REPLY,
    REGISTRATION_OTP,
    SESSION_TOKEN,
    SESSION_TOKEN_REPLY,
    SUGGESTIONS_REPLY,
)
from pages.abha.abha_setup import AbhaSetup, AbhaSetupReader
from pages.abha.address_popup import AbhaAddressPopup
from pages.abha.billing_details import AbhaBillingDetails
from pages.abha.card_download_page import AbhaCardDownloadPage
from pages.abha.cash_bill_draft import CashBillDraft
from pages.abha.consent_connector import ConsentConnectorStub
from pages.abha.consent_dialog import ConsentDialog, GiveConsent
from pages.abha.digital_menu import DigitalMenu
from pages.abha.patient_abha_status import PatchedPatients, PatientAbhaStatusPatch
from pages.abha.patient_master import PatientMaster
from pages.abha.registration_page import AbhaRegistrationPage
from pages.abha.sale_bill_abha import SaleBillAbha
from pages.company_switch_page import GARMENTS_COMPANY, PHARMA_COMPANY, CompanySwitchPage
from pages.components.send_guard import SendGuard
from pages.components.stubbed_endpoint import StubbedEndpoint, StubReply
from pages.dashboard_page import DashboardPage
from pages.sale.documents.bill import SaleBillDocument
from test_data.abha import (
    FAKE_AADHAAR_PARTS,
    FAKE_ABHA_NUMBER,
    FAKE_CONSENT_NAME,
    FAKE_MOBILE,
    FAKE_OTP,
    fake_patient_mobile,
    fake_patient_name,
)

ABHA_ACCOUNT: Account = "chemist"
ABHA_COMPANY = PHARMA_COMPANY
NON_CHEMIST_COMPANY = GARMENTS_COMPANY


@pytest.fixture
def guarded_page(page_as: Callable[[Account], Page]) -> Iterator[Page]:
    """A chemist page, guarded against ABDM calls, not yet navigated."""
    page = page_as(ABHA_ACCOUNT)
    guard = SendGuard(page, ABDM_OR_ABHA_WRITE)
    guard.arm()
    yield page
    guard.expect_nothing_sent()


@pytest.fixture
def session_token(guarded_page: Page) -> StubbedEndpoint:
    """Answered before the first navigation: both standalone ABHA screens ask for it on load."""
    endpoint = StubbedEndpoint(guarded_page, SESSION_TOKEN)
    endpoint.answer_with(SESSION_TOKEN_REPLY)
    return endpoint


@pytest.fixture
def registration_otp(guarded_page: Page) -> StubbedEndpoint:
    """Not answered until a test says how; until then the guard aborts any call."""
    return StubbedEndpoint(guarded_page, REGISTRATION_OTP)


@pytest.fixture
def login_otp(guarded_page: Page) -> StubbedEndpoint:
    return StubbedEndpoint(guarded_page, LOGIN_OTP)


@pytest.fixture
def address_login_otp(guarded_page: Page) -> StubbedEndpoint:
    return StubbedEndpoint(guarded_page, ADDRESS_LOGIN_OTP)


@pytest.fixture
def abha_page(guarded_page: Page, session_token: StubbedEndpoint) -> Page:
    """The guarded page on the ABHA company's dashboard; skips unless that company shows ABHA."""
    setup = _open_dashboard_of(guarded_page, ABHA_COMPANY)
    if not setup.shows_abha:
        pytest.skip(_abha_missing(setup))
    return guarded_page


@pytest.fixture
def registration(abha_page: Page, session_token: StubbedEndpoint) -> AbhaRegistrationPage:
    """The screen, open, with its session-token call proven answered by the stub."""
    screen = AbhaRegistrationPage(abha_page)
    session_token.capture_one(screen.open)
    return screen


@pytest.fixture
def card_download(abha_page: Page, session_token: StubbedEndpoint) -> AbhaCardDownloadPage:
    """The screen, open, with its session-token call proven answered by the stub."""
    screen = AbhaCardDownloadPage(abha_page)
    session_token.capture_one(screen.open)
    return screen


@pytest.fixture
def consent_given(registration: AbhaRegistrationPage, registration_otp: StubbedEndpoint) -> GiveConsent:
    """Gives the consent with the fake Aadhaar and name, the OTP request answered with `reply`."""

    def give(reply: StubReply) -> None:
        registration_otp.answer_with(reply)
        registration.enter_aadhaar(FAKE_AADHAAR_PARTS)
        consent = ConsentDialog(registration.page)
        consent.enter_name(FAKE_CONSENT_NAME)
        registration_otp.capture_one(consent.agree)
        consent.expect_closed()

    return give


@pytest.fixture
def otp_stage(registration: AbhaRegistrationPage, consent_given: GiveConsent) -> AbhaRegistrationPage:
    consent_given(OTP_SENT_REPLY)
    registration.expect_otp_stage()
    return registration


@pytest.fixture
def create_abha_address(guarded_page: Page) -> StubbedEndpoint:
    return StubbedEndpoint(guarded_page, CREATE_ABHA_ADDRESS)


@pytest.fixture
def abha_card(guarded_page: Page) -> StubbedEndpoint:
    return StubbedEndpoint(guarded_page, ABHA_CARD)


@pytest.fixture
def address_step(otp_stage: AbhaRegistrationPage) -> AbhaAddressPopup:
    """The create-address popup, reached through a stubbed enrolment and suggestion call, both proven."""
    page = otp_stage.page
    enrolment = StubbedEndpoint(page, ENROL_BY_AADHAAR)
    enrolment.answer_with(ENROLLED_REPLY)
    suggestion = StubbedEndpoint(page, ADDRESS_SUGGESTION)
    suggestion.answer_with(SUGGESTIONS_REPLY)
    otp_stage.enter_correspondence_mobile(FAKE_MOBILE)
    otp_stage.type_otp(FAKE_OTP)
    otp_stage.captcha.enter_shown_code()
    # The suggestion call follows the enrolment reply (abha-patient-registration.component.ts:277,328).
    suggestion.capture_one(lambda: enrolment.capture_one(otp_stage.submit))
    popup = AbhaAddressPopup(page)
    popup.expect_shown()
    return popup


@pytest.fixture
def abha_sale_bill(abha_page: Page) -> SaleBillAbha:
    """A new, unsaved sale bill on the ABHA company (no patient, so no ABHA linked)."""
    SaleBillDocument(abha_page).open_new()
    return SaleBillAbha(abha_page)


@pytest.fixture
def abha_details(guarded_page: Page) -> StubbedEndpoint:
    """The patient's ABHA rows, answered with one fake row (decision N3: stub, do not seed)."""
    endpoint = StubbedEndpoint(guarded_page, PATIENT_ABHA_DETAILS)
    endpoint.answer_with(PATIENT_ABHA_DETAILS_REPLY)
    return endpoint


@pytest.fixture
def billing_details(abha_sale_bill: SaleBillAbha, abha_details: StubbedEndpoint) -> AbhaBillingDetails:
    """AB-33: "Select ABHA Address" chosen; the popup's rows proven to come from the stub."""
    abha_sale_bill.open_selection()
    abha_details.capture_one(abha_sale_bill.choose_select_address)
    popup = AbhaBillingDetails(abha_sale_bill.page)
    popup.expect_shown()
    return popup


@pytest.fixture
def abha_linked_sale_bill(abha_sale_bill: SaleBillAbha, billing_details: AbhaBillingDetails) -> SaleBillAbha:
    billing_details.choose(FAKE_ABHA_NUMBER)
    return abha_sale_bill


@pytest.fixture
def cash_bill_with_abha(abha_page: Page, abha_details: StubbedEndpoint) -> CashBillDraft:
    """AB-34: a cash bill with one item and the stubbed ABHA row linked; not saved."""
    draft = CashBillDraft(abha_page)
    draft.start()
    abha_button = SaleBillAbha(abha_page)
    abha_button.open_selection()
    abha_details.capture_one(abha_button.choose_select_address)
    AbhaBillingDetails(abha_page).choose(FAKE_ABHA_NUMBER)
    return draft


@pytest.fixture
def abha_page_cash_bill(abha_page: Page) -> CashBillDraft:
    """A plain cash bill (no ABHA) on the ABHA company, ready to save."""
    draft = CashBillDraft(abha_page)
    draft.start()
    return draft


@pytest.fixture
def consent_connector(guarded_page: Page) -> ConsentConnectorStub:
    """Registered after the guard, so it answers the consent tab instead of the guard aborting it."""
    stub = ConsentConnectorStub(guarded_page)
    stub.install()
    return stub


@pytest.fixture
def abha_patient_master(abha_page: Page) -> PatientMaster:
    patients = PatientMaster(abha_page)
    patients.open()
    return patients


@pytest.fixture
def patients_with_known_abha_states(abha_page: Page) -> PatchedPatients:
    """The patient list open, its reply patched so one patient has an ABHA link and one has none."""
    patch = PatientAbhaStatusPatch(abha_page)
    patch.install()
    return patch.capture_patched(PatientMaster(abha_page).open)


@pytest.fixture
def patient_checked_for_abha(
    abha_patient_master: PatientMaster, session_token: StubbedEndpoint, run_id: str
) -> PatientMaster:
    """AB-31: a new fake patient saved with "Save & Check Abha Id"; the card popup's token call is proven."""
    abha_patient_master.start_new_patient()
    abha_patient_master.fill_new_patient(fake_patient_mobile(run_id), fake_patient_name(run_id))
    session_token.capture_one(abha_patient_master.save_and_check_abha)
    return abha_patient_master


@pytest.fixture
def chemist_without_abha_page(guarded_page: Page) -> Page:
    """AB-02: the chemist company with field 4426 blank; skips when it is filled (the usual ABHA setup)."""
    setup = _open_dashboard_of(guarded_page, ABHA_COMPANY)
    if not setup.is_chemist or setup.abha_id_set:
        pytest.skip(
            f"AB-02 precondition: {ABHA_COMPANY} must be a chemist company with Control Room field 4426 "
            f"blank; "
            f"{_describe(setup)}. The suite does not change Control Room."
        )
    return guarded_page


@pytest.fixture
def non_chemist_page(guarded_page: Page) -> Page:
    """AB-03: a company of another trade (the garments company)."""
    setup = _open_dashboard_of(guarded_page, NON_CHEMIST_COMPANY)
    if setup.is_chemist:
        pytest.skip(
            f"AB-03 precondition: {NON_CHEMIST_COMPANY} must not be a chemist company; {_describe(setup)}"
        )
    return guarded_page


@pytest.fixture
def digital_with_only_abha(chemist_without_abha_page: Page) -> DigitalMenu:
    """AB-04: the Digital menu of a company where ABHA is off; skips if Digital has other children."""
    menu = DigitalMenu(chemist_without_abha_page)
    menu.wait_until_shown()
    if menu.digital_has_children():
        pytest.skip(
            "AB-04 precondition: needs a company whose Digital menu has no child but ABHA; "
            f"{ABHA_COMPANY}'s Digital menu still lists other entries with ABHA off."
        )
    return menu


def _open_dashboard_of(page: Page, company: str) -> AbhaSetup:
    DashboardPage(page).open()
    # The login's company is shared state that other suites switch.
    CompanySwitchPage(page).ensure_company(company)
    return AbhaSetupReader(page).read()


def _abha_missing(setup: AbhaSetup) -> str:
    return (
        f"ABHA precondition: {ABHA_COMPANY} must be a chemist company (business type 5) with Control Room "
        f'field 4426 "Abha Id for pharmacy store" filled; {_describe(setup)}. '
        "The suite does not change Control Room."
    )


def _describe(setup: AbhaSetup) -> str:
    field_state = "filled" if setup.abha_id_set else "blank"
    return f"it has business type {setup.business_type} and field 4426 {field_state}"
