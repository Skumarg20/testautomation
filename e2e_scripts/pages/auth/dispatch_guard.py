"""Safety net for the unauthenticated auth screens: no OTP, SMS or reset mail may ever leave a test.

The endpoints come from the login app (margweblogin `Globals/global.ts` `CheckOTP`, `otpVerify`,
`environment*.ts` `sendOTP`) and the core API (`RegisterUser/ForgotPasswordMail`). A request to any of them is
aborted before it reaches the server and remembered, so the test can fail loudly.
"""

import re

from playwright.sync_api import Page, Route

DISPATCH_ENDPOINTS = re.compile(
    r"(RegisterUser/SendSMSInQue|PharmaNxt/SendOTP|RegisterUser/CheckOTP|RegisterUser/ForgotPasswordMail)",
    re.IGNORECASE,
)


class DispatchGuard:
    def __init__(self, page: Page) -> None:
        self.page = page
        self._blocked_urls: list[str] = []

    def install(self) -> None:
        """Guards every tab of the page's browser context, not only this page."""
        self.page.context.route(DISPATCH_ENDPOINTS, self._block)

    def expect_nothing_dispatched(self) -> None:
        assert not self._blocked_urls, (
            f"An OTP/mail request was attempted (and blocked): {self._blocked_urls}"
        )

    def _block(self, route: Route) -> None:
        self._blocked_urls.append(route.request.url)
        route.abort()
