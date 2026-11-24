"""J34 payment history: each payment shows its status, amount and transaction, and opens its detail.

Plan: specs/subscription-status.md (SS-04). Read only.
"""

import pytest

from pages.subscription.payment_history import PaymentDetail, PaymentHistory

pytestmark = [pytest.mark.p2, pytest.mark.journey("subscription-status")]

SECOND_ENTRY = 1


def test_payment_history_entries_show_status_amount_and_txn(payment_history: PaymentHistory) -> None:
    entries = payment_history.entries()

    assert entries
    assert all(entry.status and entry.amount > 0 and entry.txn_id for entry in entries), entries


def test_selected_payment_detail_matches_entry(payment_history: PaymentHistory) -> None:
    entries = payment_history.entries()
    selected = entries[min(SECOND_ENTRY, len(entries) - 1)]

    payment_history.select(entries.index(selected))

    payment_history.expect_detail_for(selected)
    assert payment_history.detail() == PaymentDetail(selected.amount, selected.paid_at)


def test_search_without_match_lists_no_payment(payment_history: PaymentHistory, run_id: str) -> None:
    payment_history.entries()

    payment_history.search(f"QA-{run_id}-no-such-payment")

    payment_history.expect_no_entries()
