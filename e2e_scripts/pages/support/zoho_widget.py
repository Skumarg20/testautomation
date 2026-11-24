"""A stand-in for the Zoho SalesIQ chat widget the app loads from `https://salesiq.zoho.in/widget`
(`src/index.html:17-34` in the Angular source). "Chat Now" in the Help drawer calls
`$zoho.salesiq.floatwindow.visible('show')` (`homelayout.component.ts:4004-4010`).

Zoho is a third-party chat with real agents, so no test may load it. The stand-in answers the widget
script itself with a few lines that record the float-window call, and aborts every other Zoho request.
It is a page route set before the page's first navigation. (`StubbedEndpoint` cannot be used: it answers
JSON, and this is a script.)
"""

import re

from playwright.sync_api import Page, Route

ZOHO_HOST = re.compile(r"^https://salesiq\.zoho\.in/")
WIDGET_PATH = re.compile(r"^https://salesiq\.zoho\.in/widget")
WIDGET_TIMEOUT_MS = 30_000
FLOAT_WINDOW_STATE = "window.__qaZohoFloatWindow || null"
STAND_IN_SCRIPT = """
window.$zoho.salesiq.floatbutton = { visible: function () {} };
window.$zoho.salesiq.floatwindow = {
  visible: function (state) { window.__qaZohoFloatWindow = state; }
};
"""


class ZohoWidget:
    def __init__(self, page: Page) -> None:
        self._page = page
        self._served = 0

    def stand_in(self) -> None:
        """Answers the widget script with the recording stand-in."""
        self._page.route(ZOHO_HOST, self._answer)

    def block(self) -> None:
        """Aborts the widget script, as when Zoho is unreachable."""
        self._page.route(ZOHO_HOST, self._abort)

    def expect_stand_in_loaded(self) -> None:
        """Proves the stand-in, not Zoho, answered the widget before anything is clicked."""
        self._page.wait_for_function(
            "() => Boolean(window.$zoho && window.$zoho.salesiq && window.$zoho.salesiq.floatwindow)",
            timeout=WIDGET_TIMEOUT_MS,
        )
        assert self._served >= 1, "the Zoho widget was not answered by the stand-in"

    def float_window_state(self) -> str | None:
        state: str | None = self._page.evaluate(FLOAT_WINDOW_STATE)
        return state

    def _answer(self, route: Route) -> None:
        if WIDGET_PATH.match(route.request.url):
            self._served += 1
            route.fulfill(status=200, content_type="application/javascript", body=STAND_IN_SCRIPT)
            return
        route.abort()

    @staticmethod
    def _abort(route: Route) -> None:
        route.abort()
