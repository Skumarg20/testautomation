"""Fixtures for the cash transfer journey (J29): a garments session with its own cash and bank ledgers."""

from collections.abc import Callable, Iterator

import pytest
from playwright.sync_api import Page

from config.settings import Account
from pages.cash_transfer.cash_transfer_book import CashTransferBook
from pages.company_switch_page import GARMENTS_COMPANY
from test_data.cash_transfer import cash_bank_ledgers
from test_data.factory import DataFactory

GARMENTS: Account = "garments"


@pytest.fixture
def garments_page(company_page: Callable[[Account, str], Page]) -> Page:
    return company_page(GARMENTS, GARMENTS_COMPANY)


@pytest.fixture
def cash_book(garments_page: Page, data: DataFactory) -> Iterator[CashTransferBook]:
    """A new cash ledger and bank ledger; their deposits and the ledgers are deleted after the test."""
    book = CashTransferBook(garments_page, cash_bank_ledgers(data))
    try:
        book.open()
        yield book
    finally:
        book.close()
