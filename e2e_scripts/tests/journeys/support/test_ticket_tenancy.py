"""J41 tickets after a company switch (SH-37). The list request is a read; the company switch changes the
chemist login's last company, which other tests share, so the module runs on the tenant's worker and the
fixture switches back. The server scopes tickets by login and licence (`MargSupportController.cs:321-333`),
so the pack expects the same tickets in every company; whether the business wants company-scoped tickets is
an open question for a human."""

import pytest
from playwright.sync_api import Page

from pages.company_switch_page import CompanySwitchPage
from pages.support.ticket_list import SupportTicketList

pytestmark = [
    pytest.mark.p3,
    pytest.mark.journey("support-helpdesk"),
    pytest.mark.xdist_group("chemist-tenant"),
]


# SH-37
def test_ticket_list_keeps_its_licence_scope_after_a_company_switch(
    guarded_page: Page, second_company: str
) -> None:
    tickets = SupportTicketList(guarded_page)
    scope_before = tickets.open_capturing_scope()
    CompanySwitchPage(guarded_page).switch_company(second_company)

    scope_after = tickets.open_capturing_scope()

    assert scope_after == scope_before
