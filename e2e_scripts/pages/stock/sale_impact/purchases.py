"""Purchases that make a test batch with an expiry of the test's choosing (seed ones use a fixed expiry)."""

from dataclasses import replace

from playwright.sync_api import Page

from pages.purchase.documents.bill_page import PurchaseBillEntryPage
from pages.purchase.documents.dates import timestamp_label, todays_serial
from pages.purchase.documents.line_items import standard_line
from pages.purchase.documents.seed_documents import SeededBill, seed_draft


def buy_batch_expiring_in(page: Page, days: int) -> SeededBill:
    """A purchase bill of the standard line (100 + 50 free) in a new batch that expires `days` from today."""
    batch = timestamp_label()
    line = replace(standard_line(), batch=batch, expiry_serial=todays_serial() + days)
    number = PurchaseBillEntryPage(page).create(replace(seed_draft(batch), lines=(line,)))
    return SeededBill(number, batch, line)
