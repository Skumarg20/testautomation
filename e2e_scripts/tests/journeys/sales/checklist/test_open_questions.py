"""Sale checklist rows that cannot be scripted here. Each skip names what is missing; none guesses a rule.

PO = `processout.transaction.component.ts` of newmarg-webangular20. Rows marked "Covered by" already have
an active test elsewhere in `tests/journeys/sales/`; their placeholders stay only so the row is traceable
and can be deleted once the coverage matrix points at the covering test.
"""

import pytest

pytestmark = [
    pytest.mark.p2,
    pytest.mark.journey("sale-bill-creation"),
]


@pytest.mark.skip(
    reason=(
        "Row 23 (schemes: Item, Bill Value, Combo, Buy X Get Y, Rate wise, No scheme): covered by the "
        "active tests in tests/journeys/sales/round2_c1/test_sale_promotion.py, which create their own "
        "scheme per type for item 44646015 (Scheme.businesslogic.ts). Duplicate placeholder."
    )
)
def test_row_23_schemes_apply_as_configured() -> None: ...


@pytest.mark.skip(
    reason=(
        "Row 28 (save as draft): covered by round2_c3/test_bill_list.py::"
        "test_saved_as_draft_is_in_the_draft_list_and_not_in_the_bill_list (Control Room 'Sale Bill "
        "Draft Required'). Duplicate placeholder."
    )
)
def test_row_28_save_as_draft_is_listed() -> None: ...


@pytest.mark.skip(
    reason=(
        "Row 40 (each store branch bills correctly): covered by round2_c2/test_round2_stores.py "
        "(garments company, Main Store and Scrap Store, stock per store). Duplicate placeholder."
    )
)
def test_row_40_each_store_bills_correctly() -> None: ...


@pytest.mark.skip(
    reason=(
        "Row 41 (pending prescription list, chemist): the KB states the flow (Prescription_Master_v1.0.docx "
        "'Load Prescription on Sale Bill'; careportal:299535 saves a bill as a prescription) and PO:15228 "
        "onLoadprescription runs only for the chemist trade. Still needed: a chemist-trade company with a "
        "saved prescription for the test's own patient, and a page object for the Load Prescription "
        "window. Question: which columns and filter (patient / doctor / date) must the pending list show?"
    )
)
def test_row_41_pending_prescription_list() -> None: ...


@pytest.mark.skip(
    reason=(
        "Row 45 (last bill setting, ledger wise): the setting is the Control Room option 'Last 5 details "
        "showing on right side party wise' (careportal:307790); covered by round2_c3/"
        "test_history_and_bill_discount.py::test_previous_bills_panel_follows_the_last_five_setting. "
        "Duplicate placeholder."
    )
)
def test_row_45_last_bill_setting_by_ledger() -> None: ...


@pytest.mark.skip(
    reason=(
        "Row 46 (real-time stock after loading a prescription or the last bill): the KB describes loading "
        "(Prescription_Master_v1.0.docx) but says nothing about the stock shown afterwards. Needs a "
        "chemist-trade company with a saved prescription. Question: after loading, must the grid's stock "
        "be the batch's current stock (live), or the stock at the time the prescription/bill was saved?"
    )
)
def test_row_46_real_time_stock_after_loading_documents() -> None: ...


@pytest.mark.skip(
    reason=(
        "Row 48 (F8 voucher posting): the KB shortcut list (careportal:304692) gives no F8 action in the "
        "Sale window (F7 = Create Prescription, chemist; F8 = Group only in the item list), and in code "
        "F8 on the sale bill is load prescription for the chemist trade (PO:15228). Question: which screen "
        "and which key does the checklist mean by 'F8 voucher posting'?"
    )
)
def test_row_48_f8_voucher_posting() -> None: ...


@pytest.mark.skip(
    reason=(
        "Row 49 (settings survive logout and login): covered by round2_c2/test_round2_settings_persist.py::"
        "test_a_changed_setting_survives_sign_out_and_sign_in (own browser context, three sign-ins). "
        "Duplicate placeholder."
    )
)
def test_row_49_settings_survive_logout_and_login() -> None: ...


@pytest.mark.skip(
    reason=(
        "Row 55 (E-way bill calculations): the KB only repeats the check ('calculations and discounts in "
        "the e-way bill', Sale_Bill_Details.docx item 54; jira:MBC-1914 'Eway Bill upload in bill discount "
        "in amount', a passed QA subtask) with no expected values. Needs a saved bill with a party GSTIN, "
        "and generation would reach the government portal. Question: which E-way window fields (taxable "
        "value, tax, total) must equal which bill totals when the bill has a bill discount?"
    )
)
def test_row_55_eway_bill_calculations() -> None: ...


@pytest.mark.skip(
    reason=(
        "Row 65 (Ask Order No. and Order Date): covered by round2_c3/test_setting_codes.py::"
        "test_order_number_window_opens_with_ctrl_c_only_when_asked (PO:15290 openOrderNoWindow; "
        "careportal:308443 also enters Order No. & Date on the 'Other Detail' tab). Duplicate placeholder."
    )
)
def test_row_65_ask_order_number_and_date() -> None: ...


@pytest.mark.skip(
    reason=(
        "Row 66 (Expiry & MFG configuration): careportal:296928 states the rule: Advance Setting > Expiry "
        "& MFG > Configure offers 'Expiry Date Required' (Yes/No), 'MFG Date Required' (careportal:296927) "
        "and 'Expiry & MFG Date Format' (e.g. MM/YYYY); Yes enables the expiry date in the sale bill, No "
        "removes it. Not scriptable yet: no page object for the Expiry & MFG window "
        "(expiry-mfg.setting.ts, isExpiaryDate / isMfgDateRequired / expiryDateFormat) with a restore, and "
        "the sale grid's Exp. Date column id is not in pages/. Question: does the chosen format change "
        "how the grid displays the date, and is the MFG column shown in the sale bill at all?"
    )
)
def test_row_66_expiry_and_mfg_configuration() -> None: ...


@pytest.mark.skip(
    reason=(
        "Row 68 (Pick MR from Loop / Master / Direct): option codes are 1 Master, 2 Direct, 3 Loop (codekb "
        "registry setting 177, lookup MRfrom 1119). Behaviour is known only from code (sales-purchase doc "
        "13 section 2.4: not Loop takes the party ledger's MR, Direct disables the MR box, Loop keeps the "
        "last MR); no careportal or design source states it. Also needs an MR ledger linked to the party "
        "(careportal:296623). Question: is that code behaviour the intended rule for each option?"
    )
)
def test_row_68_pick_mr_from() -> None: ...


@pytest.mark.skip(
    reason=(
        "Row 74 (free deal from Master / Batch / Manual / Lot / Lot and Free): covered by round2_c1/"
        "test_item_deal.py (deal_held writes and restores the item's own deal; Master, Batch and the other "
        "sources). Duplicate placeholder."
    )
)
def test_row_74_free_deal_source() -> None: ...


@pytest.mark.skip(
    reason=(
        "Row 82 (multi-series billing, group wise, agency wise): covered by round2_c2/"
        "test_round2_rates_barcode_series.py::test_every_series_criteria_is_offered_in_a_new_bill. "
        "Duplicate placeholder."
    )
)
def test_row_82_multi_series_billing() -> None: ...


@pytest.mark.skip(
    reason=(
        "Row 84 (agency, salt, substitute, category wise billing): the expectation is stated by "
        "jira:MBC-5730 (applying one filter, agency/category/salt/rack, lists only matching items), but "
        "no item with a known agency, salt and category exists for the test and there is no page object "
        "for the item list's 'Filter Item Based On'. Question: is 'substitute' (F7 in the item list, "
        "careportal:304692) the list of items with the same salt, and may the test create its own items "
        "with an agency, salt and category for this?"
    )
)
def test_row_84_item_filter_billing() -> None: ...


@pytest.mark.skip(
    reason=(
        "Row 85 (counter sale real time and counter-sale-to-bill): the KB gives the path (Sale > Counter "
        "Sale, Alt+A, careportal:304692) and the conversion (Convert to Bill by customer id, or all "
        "merged transactions, careportal:297032); jira:MBC-12661 and jira:MBC-3176 are past defects in "
        "the conversion (unit changed, list amount differs). Not scripted: no counter-sale page object. "
        "Question: what does 'real time' mean for counter sale (stock deducted on counter entry, or only "
        "when converted to a bill)?"
    )
)
def test_row_85_counter_sale_to_bill() -> None: ...


@pytest.mark.skip(
    reason=(
        "Row 88 (* key net rate calculation): covered by round2_c3/test_setting_codes.py::"
        "test_star_key_net_rate_becomes_the_row_rate_without_discount and "
        "test_star_key_option_shows_the_net_rate_box_only_after_the_star ('Ask on * key', "
        "careportal:296817). Duplicate placeholder."
    )
)
def test_row_88_star_key_net_rate() -> None: ...
