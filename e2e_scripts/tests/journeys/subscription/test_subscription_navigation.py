"""J34 navigation: Manage-Subscription opens from Dashboard Settings, switches tabs and goes back.

Plan: specs/subscription-status.md (SS-01, SS-08). Read only.
"""

import pytest
from playwright.sync_api import Page

from pages.dashboard_page import DashboardPage
from pages.subscription.current_plan import CurrentPlanCard
from pages.subscription.manage_subscription_page import ManageSubscriptionPage, SubscriptionTab

pytestmark = [pytest.mark.p2, pytest.mark.journey("subscription-status")]


def test_settings_configure_opens_current_plan(subscription_page: Page) -> None:
    DashboardPage(subscription_page).open()

    ManageSubscriptionPage(subscription_page).open_from_settings()

    ManageSubscriptionPage(subscription_page).expect_tab_active(SubscriptionTab.CURRENT_PLAN)
    CurrentPlanCard(subscription_page).expect_shown()


def test_manage_plan_button_opens_manage_plan_tab(
    manage_subscription: ManageSubscriptionPage, current_plan: CurrentPlanCard
) -> None:
    current_plan.open_manage_plan()

    manage_subscription.expect_tab_active(SubscriptionTab.MANAGE_PLAN)


def test_back_returns_to_dashboard(manage_subscription: ManageSubscriptionPage) -> None:
    manage_subscription.go_back()

    DashboardPage(manage_subscription.page).expect_loaded()
