"""J04 scenarios that cannot run yet: each skip names the open question or the missing data.

Two scenarios were answered from the knowledge base (KB) and run: SI-21 (refresh mid-bill) and the future-date
part of SI-14. Their KB sources are cited above each test.
"""

from collections.abc import Callable, Iterator
from datetime import date, timedelta
from decimal import Decimal

import pytest
from playwright.sync_api import Page

from config.settings import Account
from pages.dashboard_page import DashboardPage
from pages.sale.documents.flows import open_sales_page
from pages.sale.garments.garments_sale_page import GarmentsSalePage
from pages.sale.manual import messages
from pages.sale.manual.pharma_bill import PharmaBill
from pages.settings.control_room_state import ControlRoomState
from pages.settings.control_room_switch import SwitchValue, switch_held

pytestmark = [pytest.mark.p0, pytest.mark.journey("sale-bill-creation")]

INTRA_STATE_PARTY = "Ajay"
SAMPLE_ITEM = "Sample Item"
QUANTITY = Decimal(3)
ONE_UNIT = Decimal(1)
FUTURE_BILLING = "Sale Future Date Billing"


@pytest.fixture
def pharma_page(page_as: Callable[[Account], Page]) -> Page:
    return open_sales_page(page_as)


@pytest.fixture
def future_billing_off(pharma_page: Page) -> Iterator[None]:
    """Sale Future Date Billing = No (Control Room); the tenant's original choice is put back after."""
    switch = SwitchValue(FUTURE_BILLING, "No")
    with switch_held(ControlRoomState(pharma_page), switch, DashboardPage(pharma_page).open):
        yield


@pytest.fixture
def pharma_bill(pharma_page: Page) -> Iterator[PharmaBill]:
    """A pharma-company sale bill (Cash Account, item 44646015), closed unsaved before any restore."""
    bill = PharmaBill(pharma_page)
    yield bill
    if bill.is_open():
        bill.leave_without_saving()


@pytest.mark.skip(
    reason=(
        "SI-05 save then list, SI-28 ledger balance. KB answers how a bill is removed: Sale > Bill "
        "list, Delete icon, 'Yes', 'Record deleted successfully' (careportal:298501); the manual suite "
        "already saves and deletes pharma bills that way (SavedBills). Open: Q1, may tests save bills "
        "in the garments company too, and which ledger screen gives the party balance for SI-28?"
    )
)
def test_saved_bill_appears_in_the_list() -> None:
    raise NotImplementedError


@pytest.mark.skip(
    reason=(
        "SI-06 GSTR-1 deltas after a saved bill (cross-reference J06). Deleting is documented "
        "(careportal:298501); the KB has no rule for when a saved bill enters GSTR-1. Open: Q1 for "
        "the garments company, and does a bill saved today show in GSTR-1 at once?"
    )
)
def test_saved_bill_adds_to_gstr1() -> None:
    raise NotImplementedError


@pytest.mark.skip(
    reason=(
        "SI-08 odd-paise bases (0.50 and 250.10 at 5%) differ between half-up and half-even. KB has "
        "only code: per-line round(amount, N) and totals to decimalForAmount (06-calculation-engine.md "
        "CALC-011, dataCalculation.ts:206-209, :293-294) and a 2-dp F2 tax header on the server "
        "(SaleChallanBill.cs:1730); no business rule names the mode. Open D5: half-up or half-even "
        "for tax, and at 2 or 3 decimals?"
    )
)
def test_odd_paise_tax_rounding() -> None:
    raise NotImplementedError


@pytest.mark.skip(
    reason=(
        "SI-09/10 zero and negative quantity. KB: the API refuses a zero line with '<item> Quantity "
        "should be greater than 0' (InventoryProcess.cs:552-555); the client silently drops rows with "
        "quantity and free <= 0 from the save (row-editing-and-commit.md, processout:11171); a "
        "negative quantity is allowed only with the billing parameter on (jira:MBC-18403). Open: what "
        "the garments quantity window must show for 0 and -2 (live: no row, no text), and its wording."
    )
)
def test_zero_and_negative_quantity_message() -> None:
    raise NotImplementedError


@pytest.mark.skip(
    reason=(
        "SI-12 fractional (2.5) and 13-digit quantity. KB: decimals follow the item's 'Unit in "
        "Decimal' and Control Room 4198 / 159 (transaction-flow.md section 7, registry); F8 on a unit "
        "without decimals warns 'Decimal for Unit is disabled' (global.ts:19379); no rule or message "
        "for an over-long quantity. Open: is Sample Item's unit decimal (data), and what must "
        "9999999999999 show?"
    )
)
def test_fractional_and_huge_quantity() -> None:
    raise NotImplementedError


@pytest.mark.usefixtures("future_billing_off")
@pytest.mark.xdist_group("chemist-tenant")
def test_future_date_is_refused_when_future_billing_is_off(pharma_bill: PharmaBill) -> None:
    """SI-14, future date. The back date with back billing off is in manual/test_manual_bill_lifecycle.py."""
    # KB: careportal:309030 (a future date is allowed only with 'Sale Future Date Billing' = Yes);
    # KB: 16a-matrix-rows.md M12, dataCalculation.ts:3780-3788 ("Future Date Billing Not Allowed")
    pharma_bill.start_on(date.today() + timedelta(days=1))
    pharma_bill.add_line(0, ONE_UNIT)

    pharma_bill.try_save()

    pharma_bill.messages.expect_warning(messages.FUTURE_DATE_REFUSED)


@pytest.mark.skip(
    reason=(
        "SI-14 date outside the books year (e.g. 05-10-2027 for books 01-04-2026..31-03-2027). KB: "
        "the server refuses a bill number for a date outside FinFromdate..FinTodate with "
        "StringResource.InvalidDate (VoucherCodeDal.cs:220-228), a language-resource text; "
        "jira:MBC-1608 only asks to test it. Open D6: refused at the date field or at save, and with "
        "which wording?"
    )
)
def test_date_outside_the_books_year_is_refused() -> None:
    raise NotImplementedError


@pytest.mark.skip(
    reason=(
        "SI-16 save with no party. The no-item text ('Please select minimum one item!') is scripted "
        "in manual/. KB: the save stops in isInvalidControl (processout.transaction.component.ts:"
        "10487-10533), documented as 'Please enter <Customer|Patient> Name' for the patient fields "
        "(02-frontend-architecture.md F-37); the text for an empty party (ledgerName) is not shown. "
        "Open: the exact warning for a bill with no party."
    )
)
def test_save_without_party_or_item() -> None:
    raise NotImplementedError


@pytest.mark.skip(
    reason=(
        "SI-17 bad-format GSTIN on the party form. KB (code only): CheckValidGSTNo sets the field "
        "error 'Not a valid GSTIN <value>. Required 15 character GST No. ' for a GSTIN that is not 15 "
        "characters once a state is chosen (createledger.component.ts:4573-4615), while the app "
        "team's spec expects 'Invalid GSTNo' from minLength(15) (accountsmaster.spec.ts TC-0439). "
        "Open: which text the form must show; LedgerForm also needs a state selector and an error reader."
    )
)
def test_invalid_gstin_format_is_rejected() -> None:
    raise NotImplementedError


@pytest.mark.skip(
    reason=(
        "SI-18 wrong GSTIN check digit on the party form. KB (code only): checkGst asks the server "
        "(Util/CheckGSTIN, GSTINValidation.IsValidGSTIN) and sets 'Not a valid GSTIN <value>. "
        "Required 15 character GST No.  GSTIN should contain State Code/PAN/Entity No./Z/Checksum!' "
        "(createledger.component.ts:4635-4669). Open: is that the intended wording and does it block "
        "Save; LedgerForm also needs a state selector and an error reader."
    )
)
def test_invalid_gstin_check_digit_is_rejected() -> None:
    raise NotImplementedError


@pytest.mark.skip(
    reason=(
        "SI-19 B2B versus B2C for an invalid-GSTIN party. KB: the ledger form refuses an invalid "
        "GSTIN (createledger.component.ts:4573-4669), so no such party can be made in the UI; "
        "jira:MBC-5123 only covers B2B/B2C by GSTIN history. Open: the classification rule, and a "
        "seeded invalid-GSTIN party."
    )
)
def test_sale_to_party_with_invalid_gstin() -> None:
    raise NotImplementedError


@pytest.mark.skip(
    reason=(
        "SI-20 duplicate bill number and double Save: scripted for the pharma bill in "
        "manual/test_manual_bill_lifecycle.py (any notification asserted). KB wording conflicts: "
        "'Bill No already exists' (jira:MBC-12557, purchase) vs 'Sale Bill Already Exist' "
        "(support:MB-36233), and jira:MBC-12559 wants it on entry, not on save. Open: the sale "
        "wording and when it shows."
    )
)
def test_duplicate_bill_number_and_double_save() -> None:
    raise NotImplementedError


def test_refresh_mid_bill_offers_the_unsaved_bill(sale_page: GarmentsSalePage) -> None:
    """SI-21: the bill is not lost; the next new bill offers it back ("Select Unsaved Bills")."""
    # KB: careportal:309424 (unsaved bills listed by party on the next new bill), jira:MBC-17122
    sale_page.choose_party(INTRA_STATE_PARTY)
    sale_page.add_item(0, SAMPLE_ITEM, QUANTITY)

    sale_page.refresh()

    sale_page.expect_unsaved_bill_offered(INTRA_STATE_PARTY)
    sale_page.discard_unsaved_bills()


@pytest.mark.skip(
    reason=(
        "SI-22 edit of a saved bill. Modify is documented (careportal:309042) and recalculation after "
        "a change is scripted for pharma (manual/test_manual_saved_bill.py rows 22, 109, 110). Open: "
        "Q1 for the garments company, and the GSTR-1 timing asked in SI-06."
    )
)
def test_edit_saved_bill_recalculates() -> None:
    raise NotImplementedError


@pytest.mark.skip(
    reason=(
        "SI-23 Save As Draft. KB: drafts are held per user (jira:MBC-12711) and can be recovered "
        "(jira:MBC-3140); nothing says whether a draft is left out of GSTR-1. Open: Q1, and is a "
        "draft excluded from GSTR-1 and the party balance?"
    )
)
def test_draft_is_listed_but_not_in_gstr1() -> None:
    raise NotImplementedError


@pytest.mark.skip(
    reason=(
        "SI-24 discounts before tax. Item discount 1 and bill discounts 1, 2 and amount are asserted "
        "one at a time in test_sales_gst_discount.py (AJ-013, AJ-016..018); the field-structure doc "
        "taxes (rate x qty - discount) (onedrive: KIRANA Sale_Bill_1.0.0.xls#4). Open: is the bill "
        "discount taken on the amount after the item discount (code only: calculation-catalog BR-C07, "
        "dataCalculation.ts:639)? Item discount 2 also needs its setting (careportal:308988)."
    )
)
def test_discounts_reduce_the_taxable_base() -> None:
    raise NotImplementedError


@pytest.mark.skip(
    reason=(
        "SI-25. Q2 answered: the labels are Inclusive / Exclusive / Tax on MRP (inc.) "
        "(careportal:296904), and Inclusive runs in test_sales_gst_discount.py AJ-014. Open for Tax "
        "on MRP: the tax base is the MRP in code only (transaction-flow.md 7ad, "
        "dataCalculation.ts:641-645); no doc states the formula and Sample Item's MRP is not recorded."
    )
)
def test_inclusive_and_tax_on_mrp_modes() -> None:
    raise NotImplementedError


@pytest.mark.skip(
    reason=(
        "SI-26 operator, admin and accountant rights. Access to the sale bill list is scripted for "
        "the optional operator / accountant logins (manual/test_manual_access.py); a per-user rate "
        "ban is documented (careportal:308723). Open D10: a role whose delete, modify, rate and "
        "discount rights are recorded, and its login."
    )
)
def test_sale_rights_by_role() -> None:
    raise NotImplementedError


@pytest.mark.skip(
    reason=(
        "SI-27 tenancy. No second company is available; support:MB-30329 shows a past cross-company "
        "leak in reports, so the check matters. Open: a second company for the QA login."
    )
)
def test_other_company_bills_are_absent() -> None:
    raise NotImplementedError
