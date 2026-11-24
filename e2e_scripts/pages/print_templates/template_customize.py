"""Utilities & Tools > Invoice Template: the "Template Customize" screen (route /print-template).

Live 2026-10-09: a list of voucher types on the left; for the chosen one a "Predefined Template" section
(one card, "Show More" lists all) and a "Custom Template" section. Each card has a Customise link; predefined
cards have "Set as Default"; custom cards have Delete and Export buttons that only show on hover, and the
default custom card carries a check mark. Delete asks "Are you sure you want to delete the selected Record?".
"""

from playwright.sync_api import Locator, expect

from pages.accounting.waiting import appears_within
from pages.base_page import BasePage
from pages.components.confirm_dialog import ConfirmDialog
from pages.dashboard_page import DashboardPage
from pages.print_templates.template_studio import TemplateStudio

LIST_TIMEOUT_MS = 60_000
CONFIRMATION_TIMEOUT_MS = 15_000
CUSTOM_CARDS_LOOKUP_MS = 10_000


class TemplateCustomizePage(BasePage):
    def open_for(self, voucher_type: str) -> None:
        """Opens the screen from the Utilities & Tools menu and shows the templates of `voucher_type`."""
        DashboardPage(self.page).open()
        self.page.get_by_title("Utilities & Tools").click()
        self.page.get_by_role("link", name="Invoice Template", exact=True).click()
        self.page.get_by_role("link", name=voucher_type, exact=True).click()
        expect(self._cards.first).to_be_visible(timeout=LIST_TIMEOUT_MS)

    def customise_predefined(self, name: str) -> TemplateStudio:
        show_more = self.page.get_by_role("button", name="Show More")
        show_more.click()
        expect(show_more).to_be_hidden()  # the cards are rendered again once the full list is shown
        return self._customise(self._predefined_card(name))

    def customise_custom(self, name: str) -> TemplateStudio:
        return self._customise(self._custom_card(name))

    def expect_custom_template(self, name: str) -> None:
        expect(self._custom_card(name)).to_be_visible(timeout=LIST_TIMEOUT_MS)

    def expect_no_custom_template(self, name: str) -> None:
        expect(self._custom_cards_named(name)).to_have_count(0, timeout=LIST_TIMEOUT_MS)

    def expect_custom_template_count(self, name: str, count: int) -> None:
        expect(self._custom_cards_named(name)).to_have_count(count, timeout=LIST_TIMEOUT_MS)

    def custom_template_count(self, name: str) -> int:
        """The custom section renders after the first predefined card, so the count waits for the first
        card of `name` (a name with no copy costs the lookup time)."""
        cards = self._custom_cards_named(name)
        appears_within(cards, CUSTOM_CARDS_LOOKUP_MS)
        return cards.count()

    def delete_custom(self, name: str) -> None:
        self.ask_to_delete_custom(name)
        ConfirmDialog(self.page).answer_yes()

    def ask_to_delete_custom(self, name: str) -> None:
        card = self._custom_card(name)
        card.hover()  # Delete only becomes visible on hover
        card.get_by_title("Delete").click()

    def decline_deletion(self) -> None:
        no = self._confirmation.locator("#btnNo")  # Why CSS: Yes and No are both named "Close" (brief).
        expect(no).to_be_visible(timeout=CONFIRMATION_TIMEOUT_MS)
        no.click()
        expect(self._confirmation).to_be_hidden(timeout=CONFIRMATION_TIMEOUT_MS)

    @property
    def _cards(self) -> Locator:
        # Why CSS: a template card has no role, test id or label; `print-thumb` is its only handle.
        return self.page.locator(".print-thumb")

    @property
    def _confirmation(self) -> Locator:
        return self.page.get_by_role("dialog").filter(
            has=self.page.get_by_role("heading", name="Confirmation", exact=True)
        )

    def _predefined_card(self, name: str) -> Locator:
        return self._cards.filter(has_not=self.page.get_by_title("Delete")).filter(
            has=self.page.get_by_text(name, exact=True)
        )

    def _custom_cards_named(self, name: str) -> Locator:
        return self._cards.filter(has=self.page.get_by_title("Delete")).filter(
            has=self.page.get_by_text(name, exact=True)
        )

    def _custom_card(self, name: str) -> Locator:
        return self._custom_cards_named(name).first

    def _customise(self, card: Locator) -> TemplateStudio:
        card.get_by_role("link", name="Customise").click()
        studio = TemplateStudio(self.page)
        studio.expect_open()
        return studio
