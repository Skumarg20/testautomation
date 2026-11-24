"""Makes a general (expense) ledger GST-applicable, so a sale bill adds GST on it.

Ledger form (UI/Master/Ledger/createledger.component.html:215-262): `#ddlGSTApplicability` ("Applicable"),
HSN/SAC `#drpHSN`, Tax % Type `#drpSaleType` (both typeaheads, required when applicable,
createledger.component.ts:3204-3228). For an expense group only purchase-tax types are offered (:3210-3212).
The sale bill adds `amount x igst / 100` of that type to the tax rows (dataCalculation.ts:837-846), so
the rate
is read from the chosen type's own name (a "... 18%" text), never assumed.
"""

import re
from decimal import Decimal

from playwright.sync_api import Page, expect

from pages.accounting.waiting import appears_within
from pages.masters.ledger_form import LedgerForm
from pages.masters.typeahead import Typeahead

HSN = "12345678"
SEARCH_RATE = "18"
RATE_IN_NAME = re.compile(r"(\d+(?:\.\d+)?)\s*%")
SUGGESTIONS_TIMEOUT_MS = 5_000


class TaxTypeWithoutRateError(AssertionError):
    def __init__(self, name: str) -> None:
        super().__init__(f'The tax type "{name}" names no percentage, so the GST to expect is unknown')


def make_gst_applicable(page: Page, ledger: str) -> Decimal:
    """Edits the ledger: GST Applicable, HSN, a ~18 % tax type; returns that type's rate."""
    form = LedgerForm(page)
    form.open_existing(ledger)
    page.locator("#ddlGSTApplicability").select_option(label="Applicable")
    Typeahead(page).choose(page.locator("#drpHSN"), HSN)
    rate_name = _first_tax_type(page)
    form.update()
    form.expect_updated()
    match = RATE_IN_NAME.search(rate_name)
    if match is None:
        raise TaxTypeWithoutRateError(rate_name)
    return Decimal(match.group(1))


def _first_tax_type(page: Page) -> str:
    field = page.locator("#drpSaleType")
    field.click()
    field.press_sequentially(SEARCH_RATE, delay=100)
    first = page.get_by_role("listbox").get_by_role("option").first
    appears_within(first, SUGGESTIONS_TIMEOUT_MS)
    expect(first).to_be_visible()
    name = first.inner_text().strip()
    first.click()
    return name
