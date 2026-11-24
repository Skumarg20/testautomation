"""The sale bill's ABHA button and the "ABHA Selection" popup it opens.

The button is `<marg-button type="Abha" id="btnAbha<tabId>">`, rendered only for a chemist company with
Control Room 4426 filled, red (`red-btn`) while no ABHA is linked to the bill
(`processout.transaction.component.html:1188-1191`). The popup (`abha-selection-component.html`) offers four
options; "Patient History" opens an external consent site, which only the AB-35 test clicks, with that site
stubbed (pack finding 1, `pages/abha/consent_connector.py`).
"""

import re

from playwright.sync_api import Locator, expect

from pages.base_page import BasePage

UNLINKED_STYLE = re.compile(r"\bred-btn\b")
LINKED_STYLE = re.compile(r"\bblue-btn\b")
SELECTION_TITLE = "ABHA Selection"
# `abha-selection-component.html:19-55`, `.ts:64`: the first option's text depends on the link state.
SELECT_ADDRESS = "Select ABHA Address"
CHANGE_ADDRESS = "Change ABHA Address"
PATIENT_HISTORY = "Patient History"
OTHER_OPTIONS = ("Patient History", "Patient Registration", "Download Abha Card")
BUTTON_TIMEOUT_MS = 30_000


class SaleBillAbha(BasePage):
    def expect_button_offered_as_unlinked(self) -> None:
        expect(self._button).to_be_visible(timeout=BUTTON_TIMEOUT_MS)
        expect(self._button).to_have_class(UNLINKED_STYLE)

    def expect_button_offered_as_linked(self) -> None:
        expect(self._button).to_be_visible(timeout=BUTTON_TIMEOUT_MS)
        expect(self._button).to_have_class(LINKED_STYLE)

    def expect_button_not_offered(self) -> None:
        expect(self._button).to_have_count(0)

    def open_selection(self) -> None:
        self._button.click()
        expect(self._selection).to_be_visible()

    def expect_selection_options_for_unlinked_bill(self) -> None:
        expect(self._selection.get_by_text(SELECT_ADDRESS, exact=True)).to_be_visible()
        for option in OTHER_OPTIONS:
            expect(self._selection.get_by_text(option, exact=True)).to_be_visible()

    def expect_change_address_offered(self) -> None:
        # The text ends in a space in the source (`abha-selection-component.ts:64`).
        expect(self._selection.get_by_text(CHANGE_ADDRESS)).to_be_visible()

    def choose_select_address(self) -> None:
        self._selection.get_by_text(SELECT_ADDRESS, exact=True).click()

    def choose_patient_history(self) -> None:
        self._selection.get_by_text(PATIENT_HISTORY, exact=True).click()

    def close_selection(self) -> None:
        self._selection.get_by_role("button", name="Close").click()

    def expect_selection_closed(self) -> None:
        expect(self._selection).to_be_hidden()

    @property
    def _button(self) -> Locator:
        return self.page.get_by_role("button", name="Abha", exact=True)

    @property
    def _selection(self) -> Locator:
        return self.page.get_by_role("dialog").filter(
            has=self.page.get_by_role("heading", name=SELECTION_TITLE)
        )
