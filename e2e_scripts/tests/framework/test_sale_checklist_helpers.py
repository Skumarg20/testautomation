"""Offline checks of the sale-checklist helpers: option matching and the API-call log."""

import pytest

from pages.sale.checklist.request_log import RequestLog
from pages.sale.checklist.sale_setting import _resolve

pytestmark = pytest.mark.framework

OPTIONS = [("1", "Rate * Quantity"), ("2", " Rate  *  Quantity - Discount "), ("3", "Net Amount")]


def test_an_option_is_found_by_its_value() -> None:
    assert _resolve("3", OPTIONS) == "3"


def test_an_option_is_found_by_its_label_ignoring_case_and_spacing() -> None:
    assert _resolve("rate * quantity - discount", OPTIONS) == "2"


def test_an_unknown_option_is_not_found() -> None:
    assert _resolve("Rate", OPTIONS) is None


def test_a_call_made_twice_is_reported_and_a_call_made_once_is_not() -> None:
    log = RequestLog(
        calls=[("GET", "https://api/x", ""), ("GET", "https://api/x", ""), ("POST", "https://api/y", "{}")]
    )

    assert log.repeated_calls() == {("GET", "https://api/x", ""): 2}


def test_calls_are_counted_by_a_fragment_of_the_address_ignoring_case() -> None:
    log = RequestLog(calls=[("POST", "https://api/Ledger/LedgerList", ""), ("GET", "https://api/item", "")])

    assert log.count_url_containing("ledger") == 1
