"""J22 dashboard layout (specs/dashboard.md): summary cards, tile sections and the Shortcut Keys panel."""

import pytest

from pages.dashboard.dashboard_links import DashboardLinks
from pages.dashboard.figures import DashboardFigures, SummaryCard

pytestmark = [pytest.mark.p2, pytest.mark.journey("dashboard")]

TILE_SECTIONS: dict[str, tuple[str, ...]] = {
    "Fund Summary": ("Bank Balance", "Cash Balance", "Cash Deposited", "Withdrawal", "Cheque For Deposit"),
    "Outstanding": ("Current Receivable", "Overdue Receivable", "Current Payable", "Overdue Payable"),
    "Business": ("CGST Payable", "SGST Payable", "IGST Payable"),
    "New Added": ("Items", "Agency", "Customer", "Category", "Supplier"),
    "Stock": ("Reorder", "Dump Stock", "Minimum Stock"),
    "Pending": ("Sales Challan", "Sales Order", "Purchase Order", "Purchase Challan"),
}


@pytest.mark.parametrize("card", SummaryCard, ids=lambda card: card.title)
def test_summary_card_shows_current_and_previous_figure(figures: DashboardFigures, card: SummaryCard) -> None:
    """DB-01: "₹current from ₹previous" and a change percentage."""
    figures.expect_card_shown(card)


@pytest.mark.parametrize("section", TILE_SECTIONS)
def test_tile_section_shows_its_tiles(figures: DashboardFigures, section: str) -> None:
    """DB-02: each section below the cards lists its tiles, each with a figure."""
    figures.expect_section_shown(section)
    for tile in TILE_SECTIONS[section]:
        figures.expect_tile_shown(tile)


def test_shortcut_keys_panel_lists_the_home_shortcut(links: DashboardLinks) -> None:
    """DB-08: the header's Shortcut button opens the panel; it names Alt + H for the dashboard."""
    links.open_shortcut_keys()

    links.expect_shortcut_listed("HOME/DASHBOARD", "Alt + H")


def test_home_shortcut_returns_to_the_dashboard(links: DashboardLinks) -> None:
    """DB-08: Alt+H on a report goes back to the dashboard."""
    links.open_card_report(SummaryCard.NET_SALE)
    links.expect_card_report_open(SummaryCard.NET_SALE)

    links.go_home_by_shortcut()

    links.expect_on_dashboard()
