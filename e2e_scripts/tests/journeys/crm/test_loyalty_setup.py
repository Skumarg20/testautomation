"""J36: CRM > Loyalty Management System on the garments company (specs/crm-module.md, LY cases).

The setup is one record per company and has no delete (spec N3), so each test edits it and the
`loyalty_setup` fixture saves the earning rule it found back in teardown.
"""

import pytest

from pages.crm.loyalty_setup import LoyaltySetup
from test_data.loyalty import earning_unlike

# The setup is company-wide state: these tests must not run side by side.
pytestmark = [
    pytest.mark.p3,
    pytest.mark.journey("crm-module"),
    pytest.mark.xdist_group("garments-loyalty"),
]


def test_changed_loyalty_points_are_kept(loyalty_setup: LoyaltySetup, run_id: str) -> None:
    changed = earning_unlike(loyalty_setup.current_earning(), run_id)
    loyalty_setup.enter_earning(changed)
    loyalty_setup.update()
    loyalty_setup.expect_updated()
    loyalty_setup.reopen()
    loyalty_setup.expect_earning(changed)


def test_loyalty_setup_without_amount_is_refused(loyalty_setup: LoyaltySetup) -> None:
    loyalty_setup.clear_amount()
    loyalty_setup.update()
    loyalty_setup.expect_refused_for_missing_details()


def test_loyalty_setup_keeps_amount_after_refused_update(loyalty_setup: LoyaltySetup) -> None:
    saved = loyalty_setup.current_earning()
    loyalty_setup.clear_amount()
    loyalty_setup.update()
    loyalty_setup.reopen()
    loyalty_setup.expect_earning(saved)


def test_closing_loyalty_setup_asks_for_confirmation(loyalty_setup: LoyaltySetup) -> None:
    loyalty_setup.ask_to_close()
    loyalty_setup.expect_close_question()
