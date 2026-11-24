"""Offline checks of J39's safety net: the ABDM guard pattern, a stub winning over it, the setup reader."""

import pytest
from playwright.sync_api import BrowserContext, Page, Route

from pages.abha.abdm_endpoints import ABDM_OR_ABHA_WRITE, SESSION_TOKEN, SESSION_TOKEN_REPLY
from pages.abha.abha_setup import AbhaSetup, AbhaSetupReader
from pages.components.send_guard import SendAttemptedError, SendGuard
from pages.components.stubbed_endpoint import StubbedEndpoint

pytestmark = pytest.mark.framework

LOCAL_SITE = "http://localhost:4200"
SESSION_TOKEN_PATH = "/api/AbhaGateway/GetSessionToken"
REGISTRATION_OTP_PATH = "/api/Enrollment/m1/request/otp"
STORE_SETUP = """
([bustype, abhaId]) => {
    const key = name => JSON.stringify({key: name, session: 'mb-session'});
    localStorage.setItem(key('LoggedInUserInfo'), JSON.stringify({SelectedCompany: {bustype: bustype}}));
    localStorage.setItem(key('controlRoomData'), JSON.stringify({profilerModel: {FieldsData: [
        {fieldId: 4426, ActionData: [{}, {}, {}, {}, {}, {}, {action: abhaId}]}]}}));
}
"""


def _stub_site(route: Route) -> None:
    route.fulfill(body="<p>stub</p>", content_type="text/html")


@pytest.fixture
def local_page(context: BrowserContext, page: Page) -> Page:
    context.route(f"{LOCAL_SITE}/**", _stub_site)
    return page


def _post(page: Page, path: str) -> None:
    page.evaluate(f"fetch('{path}', {{method: 'POST'}}).catch(() => null)")


def _armed_guard(page: Page) -> SendGuard:
    guard = SendGuard(page, ABDM_OR_ABHA_WRITE)
    guard.arm()
    return guard


@pytest.mark.parametrize(
    "url",
    [
        f"{LOCAL_SITE}{REGISTRATION_OTP_PATH}",
        "https://abdm.example.test/anything",
        "https://abhaconnector.example.test/consents",
        f"{LOCAL_SITE}/api/MedicalPrescription/SaveAbhadetails",
    ],
)
def test_guard_aborts_every_abdm_or_abha_write_call(local_page: Page, url: str) -> None:
    guard = _armed_guard(local_page)
    local_page.goto(f"{LOCAL_SITE}/abha/patient/registration")

    local_page.evaluate("url => fetch(url, {method: 'POST'}).catch(() => null)", url)

    with pytest.raises(SendAttemptedError):
        guard.expect_nothing_sent()


def test_session_token_stub_wins_over_the_guard(local_page: Page) -> None:
    guard = _armed_guard(local_page)
    token = StubbedEndpoint(local_page, SESSION_TOKEN)
    token.answer_with(SESSION_TOKEN_REPLY)
    local_page.goto(f"{LOCAL_SITE}/abha/patient/registration")

    token.capture_one(lambda: _post(local_page, SESSION_TOKEN_PATH))

    guard.expect_nothing_sent()


@pytest.mark.parametrize(
    ("stored", "shows_abha"),
    [((5, "QA-FAKE-ID"), True), ((5, ""), False), ((13, "QA-FAKE-ID"), False)],
)
def test_setup_reader_shows_abha_only_for_a_chemist_with_field_4426(
    local_page: Page, stored: tuple[int, str], shows_abha: bool
) -> None:
    local_page.goto(f"{LOCAL_SITE}/dashboard")
    local_page.evaluate(STORE_SETUP, list(stored))

    assert AbhaSetupReader(local_page).read().shows_abha is shows_abha


def test_setup_without_stored_data_shows_no_abha(local_page: Page) -> None:
    local_page.goto(f"{LOCAL_SITE}/dashboard")

    assert AbhaSetupReader(local_page).read() == AbhaSetup(business_type=-1, abha_id_set=False)
