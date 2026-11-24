"""Entry steps that bills and challans share because both receive stock: batches, expiry and sale prices."""

from playwright.sync_api import Page

from pages.purchase.documents.entry_grid import EntryGrid
from pages.purchase.documents.feedback import appears_within
from pages.purchase.documents.line_items import PurchaseLineItem

BATCH_DETAILS_TIMEOUT_MS = 2_000


def enter_batch_and_expiry(grid: EntryGrid, lines: tuple[PurchaseLineItem, ...]) -> None:
    """For documents whose items came from an earlier document: only the batch and expiry are new."""
    for row, line in enumerate(lines):
        grid.type_batch(row, line.batch)
        grid.enter_expiry(row, line.expiry_serial)


def enter_sale_prices(page: Page, line: PurchaseLineItem) -> None:
    """A new batch opens a "Batch Details" window for MRP and sale rate; both are set to the rate."""
    window = page.locator("ngb-modal-window").filter(has_text="Batch Details").locator("app-modal")
    if not appears_within(window, BATCH_DETAILS_TIMEOUT_MS):
        return
    # The two price inputs have ids and no labels.
    window.locator("#txtmrp").fill(str(line.rate))
    sale_rate = window.locator("#txtratea")
    sale_rate.fill(str(line.rate))
    sale_rate.press("Enter")
