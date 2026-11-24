"""The "Current Plan" card and the "Add-ons Stats" of the My Current Plan tab."""

import re
from datetime import date, datetime
from decimal import Decimal

from playwright.sync_api import Locator, expect

from pages.base_page import BasePage
from pages.subscription.rupees import rupees_in

CARD_TIMEOUT_MS = 60_000
# The app prints September as "Sept" (01-Sept-2026); strptime only knows "Sep".
SEPTEMBER_AS_PRINTED = "-Sept-"
PRINTED_DATE_FORMAT = "%d-%b-%Y"
PRINTED_PRICE = re.compile(r"₹\s*[\d,]+")
PRINTED_DATE = re.compile(r"\d{2}-[A-Za-z]+-\d{4}$")
STAT_HEADING = re.compile(r"^(?P<name>.+?) (?P<counts>\S+)$")


class CurrentPlanCard(BasePage):
    def expect_shown(self) -> None:
        """The card is up and its plan figures have arrived (the price heading is first painted empty)."""
        expect(self._title).to_be_visible(timeout=CARD_TIMEOUT_MS)
        expect(self._price_heading).to_have_text(PRINTED_PRICE, timeout=CARD_TIMEOUT_MS)

    def plan_name(self) -> str:
        """The plan name is the unlabelled line printed right under the card title."""
        self.expect_shown()
        lines = [line.strip() for line in self._card.inner_text().splitlines() if line.strip()]
        return lines[lines.index("Current Plan") + 1]

    def price(self) -> Decimal:
        self.expect_shown()
        return rupees_in(self._price_heading.inner_text())

    def subscription_date(self) -> date:
        return self._date_after("Subscription Date")

    def activation_date(self) -> date:
        return self._date_after("Activation on")

    def next_due_date(self) -> date:
        return self._date_after("Next Due Date")

    def open_manage_plan(self) -> None:
        self._card.get_by_role("button", name="Manage Plan").click()

    def add_on_stats(self) -> dict[str, str]:
        """Each add-on stat by name, with its two counts as printed ("0/2")."""
        self.expect_shown()
        expect(self._stat_headings.first).to_be_visible(timeout=CARD_TIMEOUT_MS)
        return dict(_stat_parts(text) for text in self._stat_headings.all_inner_texts())

    def _date_after(self, label: str) -> date:
        self.expect_shown()
        line = self._card.get_by_role("paragraph").filter(has_text=f"{label} :")
        expect(line).to_have_text(PRINTED_DATE, timeout=CARD_TIMEOUT_MS)
        printed = line.inner_text().split(":", 1)[1].strip().replace(SEPTEMBER_AS_PRINTED, "-Sep-")
        return datetime.strptime(printed, PRINTED_DATE_FORMAT).date()

    @property
    def _title(self) -> Locator:
        return self.page.get_by_role("heading", name="Current Plan", exact=True, level=4)

    @property
    def _price_heading(self) -> Locator:
        return self._card.get_by_role("heading", level=4).filter(has_text="₹")

    @property
    def _card(self) -> Locator:
        # Why XPath: the card has no role or test id; it is the nearest block with the title and a button.
        return self._title.locator("xpath=ancestor::*[.//button][1]")

    @property
    def _stat_headings(self) -> Locator:
        return self.page.get_by_role("tabpanel").get_by_role("heading", level=3)


def _stat_parts(heading_text: str) -> tuple[str, str]:
    flat = " ".join(heading_text.split())
    found = STAT_HEADING.match(flat)
    if found is None:
        raise ValueError(f'Add-on stat "{flat}" is not "<name> <counts>"')
    return found["name"], found["counts"]
