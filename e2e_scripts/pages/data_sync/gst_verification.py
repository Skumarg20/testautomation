"""Ledger > Create > "GST Verification": fetch party details by GSTIN, tried offline (J35 DS-12).

The window (`gstVerfication.component.html`) has "GST No." (`input#gst`) and Verify; F10 verifies
(`gstVerfication.component.ts:66-69`). After Verify the ledger form encrypts the request
(`EInvoiceEncDec/EncryptAES`) and calls the paid GST lookup (`environment.preprod.ts:52`)
(`createledger.component.ts:4870-4905`). No offline guard exists on this path, so offline the first call
fails with status 0 (`MrgHttpService.service.ts:467-479`); the pack expects a graceful error with manual
entry still possible (`Marg_Books_Test_Cases_v1.0.xlsx#MST-035`), the source suggests `/error` (D3 in the
spec). The button is shown when not VAT and the full-detail or bank tab is on
(`createledger.component.html:2605-2607`). DRAFT: written from the Angular source, not seen live.
"""

from playwright.sync_api import Locator, expect

from pages.base_page import BasePage
from pages.masters.ledger_form import LedgerForm

OPEN_BUTTON = "GST Verification"
WINDOW_TITLE = "GST Verification"
WINDOW_TIMEOUT_MS = 15_000
# A well-formed GSTIN (15 characters); offline it never leaves the browser.
SAMPLE_GSTIN = "27AAPFU0939F1ZV"
# Why ids: the ledger form has no test ids and its labels are not tied to the inputs (as LedgerForm).
GSTIN_INPUT = "input#gst"
LEDGER_NAME_INPUT = "#txtlegername"


class GstVerificationWindow(BasePage):
    def open_from_new_ledger(self) -> None:
        LedgerForm(self.page).open_new()
        self.page.get_by_role("button", name=OPEN_BUTTON).click()
        expect(self._window).to_be_visible(timeout=WINDOW_TIMEOUT_MS)

    def verify_with_keyboard(self, gstin: str) -> None:
        field = self._window.locator(GSTIN_INPUT)
        field.fill(gstin)
        field.press("F10")

    def expect_ledger_form_still_editable(self) -> None:
        name = self.page.locator(LEDGER_NAME_INPUT)
        expect(name).to_be_editable(timeout=WINDOW_TIMEOUT_MS)

    @property
    def _window(self) -> Locator:
        return self.page.locator("form#gstForm").filter(
            has=self.page.get_by_role("heading", name=WINDOW_TITLE, exact=True)
        )
