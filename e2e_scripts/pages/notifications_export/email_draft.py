"""The "New Email" draft a report's Share > Email opens (`ControlRoomSettingEmail`,
email.setting.html:391-564; seen live 2026-10-14). From, To, CC and BCC are chip lists: each address is a chip
with a remove "X"; typing an address and pressing Enter adds a chip. To starts with the party's (or the
user's own registered) address. Send validates on the client: no To or no From gives "Please enter a valid
Email Id!" and nothing is posted (email.setting.ts:308-313); otherwise it posts
`Template/SendEmailPdfExcel` (share.component.ts:427)."""

from playwright.sync_api import Locator, expect

from pages.base_page import BasePage

DRAFT_TITLE = "New Email"
DRAFT_TIMEOUT_MS = 30_000
CHIP_REMOVE = "X"
TO_LIST_POSITION = 1


class EmailDraft(BasePage):
    def expect_open(self) -> None:
        expect(self._draft).to_be_visible(timeout=DRAFT_TIMEOUT_MS)

    def clear_recipients(self) -> None:
        """Removes every To chip, so the real address the app prefilled can never be used."""
        removes = self._to_list.get_by_role("option").get_by_text(CHIP_REMOVE, exact=True)
        while removes.count() > 0:
            removes.first.click()
        expect(removes).to_have_count(0)

    def address_to(self, address: str) -> None:
        self.clear_recipients()
        box = self._to_list.get_by_role("combobox")
        box.fill(address)
        box.press("Enter")
        expect(self._to_list.get_by_role("option").filter(has_text=address)).to_be_visible()

    def send(self) -> None:
        self._draft.get_by_role("button", name="Send", exact=True).click()

    @property
    def _to_list(self) -> Locator:
        # Why a position: From, To and CC are chip lists all named "selection", always in that order (live
        # 2026-10-14); their labels are bare text, not tied to the lists.
        return self._draft.get_by_role("listbox", name="selection").nth(TO_LIST_POSITION)

    @property
    def _draft(self) -> Locator:
        return self.page.get_by_role("dialog").filter(has_text=DRAFT_TITLE)
