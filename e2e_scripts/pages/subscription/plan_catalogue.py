"""Plan cards with their yearly prices: the in-app Manage Plan tab and the public /pricing page."""

from decimal import Decimal

from playwright.sync_api import Locator, expect

from pages.base_page import BasePage
from pages.subscription.rupees import rupees_in

CATALOGUE_TIMEOUT_MS = 60_000
# Why CSS: plan cards have no role or test id; both pages build them from the same "boxInner" block.
PLAN_CARD = ".boxInner"


class PlanCatalogue(BasePage):
    """The Manage Plan tab: one card per plan, a price or "Contact Us", and "Buy Now" (never clicked)."""

    # Why CSS: the plan name is a bare span; its "plan" class is the only thing that tells it from the badge.
    PLAN_NAME = ".plan"
    BUY_NOW = "Buy Now"

    def prices(self) -> dict[str, Decimal]:
        """Price by plan name for every card that shows a rupee price (plans on "Contact Us" are left out)."""
        expect(self._cards.first).to_be_visible(timeout=CATALOGUE_TIMEOUT_MS)
        return dict(_priced(card, self.PLAN_NAME) for card in self._cards.all() if _has_price(card))

    def expect_buy_now_offered(self, plan: str) -> None:
        buy_now = self._card(plan).get_by_text(self.BUY_NOW, exact=True)
        expect(buy_now).to_be_visible()
        expect(buy_now).to_be_enabled()

    @property
    def _cards(self) -> Locator:
        return self.page.get_by_role("tabpanel").locator(PLAN_CARD)

    def _card(self, plan: str) -> Locator:
        return self._cards.filter(has=self.page.locator(self.PLAN_NAME).get_by_text(plan, exact=True))


class PublicPricingPage(BasePage):
    """The marketing pricing page; its "Try Now" links go to registration and are never followed."""

    PATH = "/pricing"
    # Why CSS: the public plan name is a bare <label> with no "for" and no role.
    PLAN_NAME = "label"

    def open(self) -> None:
        self.goto(self.PATH, CATALOGUE_TIMEOUT_MS)
        expect(self._cards.first).to_be_visible(timeout=CATALOGUE_TIMEOUT_MS)

    def prices(self) -> dict[str, Decimal]:
        return dict(_priced(card, self.PLAN_NAME) for card in self._cards.all() if _has_price(card))

    @property
    def _cards(self) -> Locator:
        return self.page.locator(PLAN_CARD)


def _has_price(card: Locator) -> bool:
    return _price_heading(card).count() == 1


def _priced(card: Locator, name_selector: str) -> tuple[str, Decimal]:
    return card.locator(name_selector).first.inner_text().strip(), rupees_in(
        _price_heading(card).inner_text()
    )


def _price_heading(card: Locator) -> Locator:
    return card.get_by_role("heading").filter(has_text="₹")
