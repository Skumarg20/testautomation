"""J22 dashboard drill-down (specs/dashboard.md): each summary card opens its report."""

import pytest

from pages.dashboard.dashboard_links import DashboardLinks
from pages.dashboard.figures import SummaryCard

pytestmark = [pytest.mark.p2, pytest.mark.journey("dashboard")]


@pytest.mark.parametrize("card", SummaryCard, ids=lambda card: card.title)
def test_summary_card_title_opens_its_report(links: DashboardLinks, card: SummaryCard) -> None:
    """DB-07: Net Sale -> Sale Register, Net Purchase -> Purchase Register,
    Gross Profit -> Gross Profit."""
    links.open_card_report(card)

    links.expect_card_report_open(card)
