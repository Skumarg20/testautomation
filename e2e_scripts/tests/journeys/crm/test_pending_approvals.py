"""J36: CRM > Pending Approvals (specs/crm-module.md, PA-01 and PA-03). Read only: no approval is made."""

import pytest

from pages.crm.pending_approvals import PendingApprovals

pytestmark = [pytest.mark.p3, pytest.mark.journey("crm-module")]

APPROVAL_COLUMNS = ("Transaction No", "Transaction Type", "Comment", "Requested By", "Created On", "Action")


def test_pending_approvals_open_on_pending_requests(pending_approvals: PendingApprovals) -> None:
    pending_approvals.open_from_menu()
    pending_approvals.expect_showing("Pending")
    pending_approvals.expect_columns(APPROVAL_COLUMNS)


def test_all_requests_can_be_shown(pending_approvals: PendingApprovals) -> None:
    pending_approvals.open_from_menu()
    pending_approvals.show("All")
    pending_approvals.expect_showing("All")
    pending_approvals.expect_count_shown()
