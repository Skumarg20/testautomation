"""The create-ABHA-address popup the registration opens after a (stubbed) enrolment, and the card popup
that follows a created address (`abha-address.component.html/.ts`, `abha-download-popup.component.html`).

The address box strips every character but letters, digits, "." and "_" as it is typed (`.ts:62-66`), and
Save checks the 8-18 character, exactly-one-separator rule before it calls the ABDM proxy
(`.ts:53-60,106-110`). A created address leads to the card call and a "Download" popup with the card image
(`.ts:139-157`).
"""

from playwright.sync_api import Locator, expect

from pages.base_page import BasePage

POPUP_TIMEOUT_MS = 15_000
ADDRESS_HINT = "Create Your Unique ABHA Address."
CARD_POPUP_TITLE = "Download"
CARD_IMAGE_NAME = "ABHA Card"


class AbhaAddressPopup(BasePage):
    def expect_shown(self) -> None:
        expect(self._popup).to_be_visible(timeout=POPUP_TIMEOUT_MS)

    def expect_suggested(self, address: str) -> None:
        expect(self._popup.get_by_text(address, exact=True)).to_be_visible()

    def type_address(self, address: str) -> None:
        self.address_box.press_sequentially(address)

    def save(self) -> None:
        self._popup.get_by_role("button", name="Save").click()

    @property
    def address_box(self) -> Locator:
        # Why CSS: the label "Enter ABHA Address" is not linked to the input (`.html:20-24`).
        return self._popup.locator('input[formcontrolname="abhaEmail"]')

    @property
    def _popup(self) -> Locator:
        return self.page.get_by_role("dialog").filter(has_text=ADDRESS_HINT)


class AbhaCardPopup(BasePage):
    def expect_card_shown(self) -> None:
        expect(self._popup.get_by_role("img", name=CARD_IMAGE_NAME)).to_be_visible(timeout=POPUP_TIMEOUT_MS)

    @property
    def _popup(self) -> Locator:
        return self.page.get_by_role("dialog").filter(
            has=self.page.get_by_role("heading", name=CARD_POPUP_TITLE, exact=True)
        )
