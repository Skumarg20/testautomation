"""J05 conditions that are not automated, each with the reason (see the J05 journal for the full list)."""

import pytest

pytestmark = [pytest.mark.p0, pytest.mark.journey("purchase-itc")]


@pytest.mark.skip(
    reason="PU-03/20 ITC in GSTR-2/3B: careportal:304846 (filing GSTR-3B) says the report is produced per "
    "return type and month and exported as Excel or JSON; the in-app GSTR-3B body was empty in a quiet run. "
    "Still needs a saved bill from a registered supplier. Question (Q8): where is the month's ITC read back "
    "(the exported Excel's eligible-ITC section, or a grid after a generate step), and which ledgers carry "
    "the input tax for the PU-20 reconcile?"
)
def test_saved_purchase_raises_itc_in_the_month() -> None:
    raise NotImplementedError


@pytest.mark.skip(
    reason="PU-12 invalid-GSTIN supplier: the composition half is covered in test_purchase_itc.py. The "
    "ledger form refuses an invalid GSTIN client-side, and the GSTIN/state-code check is disabled "
    "(ledger-flow.md, 'Two independent GSTIN/state validations ... both are disabled'), so such a supplier "
    "cannot be made through the UI. Question: must input tax be blocked for a supplier whose GSTIN is "
    "invalid or does not match its state, and may tests seed one through the API?"
)
def test_invalid_gstin_supplier_input_tax_is_blocked() -> None:
    raise NotImplementedError


@pytest.mark.skip(
    reason="PU-17 inclusive purchase: careportal:296572 gives the rule, goods value = rate x 100 / "
    "(100 + tax %), e.g. 100 at 12% = 89.29, set by 'Calculation Type in Purchase' (a tenant-wide setting, "
    "not safe on the shared tenant) or by Ctrl+R during billing. Question: does Ctrl+R switch only the "
    "open bill on the web app (so the test can avoid the setting), and what does the screen show for it?"
)
def test_inclusive_purchase_calculation_mode() -> None:
    raise NotImplementedError


@pytest.mark.skip(
    reason="PU-18 purchase rights by role: roles are made by the supervisor in User Access & Privileges, "
    "with per-menu powers such as Purchase (careportal:296923); 'operator'/'accountant' are not fixed roles. "
    "D10: the QA tenant has no limited account. Question (Q11): may tests create a limited user and role, "
    "and which purchase powers should it lack?"
)
def test_purchase_rights_by_role() -> None:
    raise NotImplementedError


@pytest.mark.skip(reason="PU-19 tenancy: no second company is available on the QA tenant (KB not needed).")
def test_other_company_purchases_are_absent() -> None:
    raise NotImplementedError


@pytest.mark.skip(
    reason="J05 e-invoice / e-way bill on purchase (no PU id): the client's e-way and e-invoice prompts "
    "check only sale bill, sale return, sale challan and stock issue (dataCalculation.ts:2697-2711), and "
    "e-way bills are generated as Excel/JSON for the government portal (careportal:301308). Question: "
    "should a purchase bill prompt for an e-way bill at all? Any upload is an external government service."
)
def test_e_invoice_and_eway_bill_prompts() -> None:
    raise NotImplementedError
