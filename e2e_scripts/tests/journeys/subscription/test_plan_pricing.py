"""J34 pricing: the plans offered in the app carry the prices of the public pricing page.

Plan: specs/subscription-status.md (SS-06). Read only: Buy Now and Try Now are never clicked.
"""

import pytest

from pages.subscription.plan_catalogue import PlanCatalogue, PublicPricingPage

pytestmark = [pytest.mark.p2, pytest.mark.journey("subscription-status")]


def test_every_priced_plan_offers_buy_now(plan_catalogue: PlanCatalogue) -> None:
    priced_plans = plan_catalogue.prices()

    assert priced_plans
    for plan in priced_plans:
        plan_catalogue.expect_buy_now_offered(plan)


def test_in_app_plan_prices_match_public_pricing(plan_catalogue: PlanCatalogue) -> None:
    in_app = plan_catalogue.prices()
    public_pricing = PublicPricingPage(plan_catalogue.page)

    public_pricing.open()

    public = public_pricing.prices()
    assert in_app.keys() <= public.keys(), (in_app, public)
    assert {plan: public[plan] for plan in in_app} == in_app
