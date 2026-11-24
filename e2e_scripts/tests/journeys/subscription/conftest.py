"""Fixtures for the subscription journey (J34): the Manage-Subscription screen of the super-admin login.

The journey is read only (specs/subscription-status.md): no fixture or test buys, renews, upgrades or adds
anything. The plan belongs to the licence, not to a company, so the company is not pinned.
"""

from collections.abc import Callable
from datetime import date

import pytest
from playwright.sync_api import Page

from config.settings import Account
from pages.subscription.add_on_order import AddOnOrder
from pages.subscription.current_plan import CurrentPlanCard
from pages.subscription.manage_subscription_page import ManageSubscriptionPage, SubscriptionTab
from pages.subscription.payment_history import PaymentHistory
from pages.subscription.plan_catalogue import PlanCatalogue

SUBSCRIPTION_ACCOUNT: Account = "garments"


@pytest.fixture
def subscription_page(page_as: Callable[[Account], Page]) -> Page:
    return page_as(SUBSCRIPTION_ACCOUNT)


@pytest.fixture
def manage_subscription(subscription_page: Page) -> ManageSubscriptionPage:
    screen = ManageSubscriptionPage(subscription_page)
    screen.open()
    return screen


@pytest.fixture
def current_plan(manage_subscription: ManageSubscriptionPage) -> CurrentPlanCard:
    card = CurrentPlanCard(manage_subscription.page)
    card.expect_shown()
    return card


@pytest.fixture
def plan_catalogue(manage_subscription: ManageSubscriptionPage) -> PlanCatalogue:
    manage_subscription.open_tab(SubscriptionTab.MANAGE_PLAN)
    return PlanCatalogue(manage_subscription.page)


@pytest.fixture
def next_due_date(current_plan: CurrentPlanCard) -> date:
    """Read on My Current Plan before another tab hides the card; add-ons are charged up to this date."""
    return current_plan.next_due_date()


@pytest.fixture
def add_on_order(next_due_date: date, manage_subscription: ManageSubscriptionPage) -> AddOnOrder:
    manage_subscription.open_tab(SubscriptionTab.ADD_ON)
    return AddOnOrder(manage_subscription.page)


@pytest.fixture
def payment_history(manage_subscription: ManageSubscriptionPage) -> PaymentHistory:
    manage_subscription.open_tab(SubscriptionTab.PAYMENT_HISTORY)
    history = PaymentHistory(manage_subscription.page)
    history.show_longest_period()
    return history
