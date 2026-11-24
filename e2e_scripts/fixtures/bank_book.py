"""Fixture for the bank and ledger-report journeys (J11, J12): a garments session with its own ledgers.

Imported by the conftest.py of tests/journeys/banking and tests/journeys/reports.
"""

from collections.abc import Callable, Iterator

import pytest
from playwright.sync_api import Page

from config.settings import Account
from pages.banking.bank_book import BankBook
from test_data.banking import bank_ledgers
from test_data.factory import DataFactory

GARMENTS: Account = "garments"


@pytest.fixture
def bank_book(page_as: Callable[[Account], Page], data: DataFactory) -> Iterator[BankBook]:
    """A new bank ledger and expense ledger; their vouchers and the ledgers are deleted after the test."""
    book = BankBook(page_as(GARMENTS), bank_ledgers(data))
    try:
        book.open()
        yield book
    finally:
        book.close()
