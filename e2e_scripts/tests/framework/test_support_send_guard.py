"""J41 safety net, checked offline against a local stub site: the send guard aborts every support-desk write
and dispatch, lets the desk's reads through, and a stub answers its write before the guard sees it."""

import pytest
from playwright.sync_api import BrowserContext, Page, Route

from pages.components.send_guard import SendAttemptedError, SendGuard
from pages.components.stubbed_endpoint import StubbedEndpoint, UnexpectedRequestError
from pages.support.desk_endpoints import SAVE_TICKET, SUPPORT_WRITES
from pages.support.desk_feed import write_accepted

pytestmark = pytest.mark.framework

LOCAL_SITE = "http://localhost:4200"
API = f"{LOCAL_SITE}/api/v1.1"
POST_FROM_PAGE = "url => fetch(url, {method: 'POST', body: '{\"ID\":0}'}).then(r => r.status).catch(() => -1)"
ABORTED = -1

WRITES = [
    "MargSupport/Save?isShowLoader=true",
    "MargSupport/MBSupportDeleteRecord",
    "MargSupport/MBSupportUpdateStatus",
    "MargSupport/MBSupportInsertChatRecord",
    "RegisterUser/CheckOTP",
    "PharmaNxt/SendOTP",
    "RegisterUser/SendSMSInQueMobile",
    "RegisterUser/SendBulkSMSTemplate",
    "Template/SendEmailPdfExcel",
    "Notification/SendWhatsappMulti",
    "Whatsapp/sendMessage",
]
READS = [
    "MargSupport/MargSupportStaticData",
    "MargSupport/MargPrtnerSupprtDetail",
    "MargSupport/MBSupportGetChatRecord?ID=1",
    "QuestionSearchMargBook/GetQuestionSugestion?keyword=gstr",
]


def _stub_site(route: Route) -> None:
    route.fulfill(body="<p>stub</p>", content_type="text/html")


@pytest.fixture
def guarded_site(context: BrowserContext, page: Page) -> tuple[Page, SendGuard]:
    context.route(f"{LOCAL_SITE}/**", _stub_site)
    guard = SendGuard(page, SUPPORT_WRITES)
    guard.arm()
    page.goto(f"{LOCAL_SITE}/support/support-ticket")
    return page, guard


@pytest.mark.parametrize("write", WRITES)
def test_send_guard_aborts_every_support_write(guarded_site: tuple[Page, SendGuard], write: str) -> None:
    page, guard = guarded_site

    status = page.evaluate(POST_FROM_PAGE, f"{API}/{write}")

    assert status == ABORTED
    with pytest.raises(SendAttemptedError):
        guard.expect_nothing_sent()


@pytest.mark.parametrize("read", READS)
def test_send_guard_lets_the_desk_reads_through(guarded_site: tuple[Page, SendGuard], read: str) -> None:
    page, guard = guarded_site

    status = page.evaluate(POST_FROM_PAGE, f"{API}/{read}")

    assert status == 200
    guard.expect_nothing_sent()


def test_send_guard_covers_a_tab_the_app_opens(guarded_site: tuple[Page, SendGuard]) -> None:
    page, guard = guarded_site
    tab = page.context.new_page()
    tab.goto(f"{LOCAL_SITE}/help")

    tab.evaluate(POST_FROM_PAGE, f"{API}/MargSupport/Save")

    with pytest.raises(SendAttemptedError):
        guard.expect_nothing_sent()


def test_stub_answers_the_save_before_the_guard_sees_it(guarded_site: tuple[Page, SendGuard]) -> None:
    page, guard = guarded_site
    stub = StubbedEndpoint(page, SAVE_TICKET)
    stub.answer_with(write_accepted())

    captured = stub.capture_one(lambda: page.evaluate(POST_FROM_PAGE, f"{API}/MargSupport/Save"))

    assert captured.json_body() == {"ID": 0}
    guard.expect_nothing_sent()


def test_stub_reports_a_call_the_step_must_not_make(guarded_site: tuple[Page, SendGuard]) -> None:
    page, _ = guarded_site
    stub = StubbedEndpoint(page, SAVE_TICKET)
    stub.answer_with(write_accepted())

    with pytest.raises(UnexpectedRequestError):
        stub.expect_none_during(lambda: page.evaluate(POST_FROM_PAGE, f"{API}/MargSupport/Save"))


def test_stub_counts_every_request_it_answered(guarded_site: tuple[Page, SendGuard]) -> None:
    page, _ = guarded_site
    stub = StubbedEndpoint(page, SAVE_TICKET)
    stub.answer_with(write_accepted())

    page.evaluate(POST_FROM_PAGE, f"{API}/MargSupport/Save")
    page.evaluate(POST_FROM_PAGE, f"{API}/MargSupport/Save")

    assert stub.answered_once_things_settle() == 2
