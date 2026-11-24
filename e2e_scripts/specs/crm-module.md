# Spec: crm-module (J36, P3) - DRAFT for QA/BA review

Scenario pack: `scenarios/crm-module.md`. Explored live on premargbooks (app V. 4.3.598.b) on 2026-10-09/10, login "garments" (super admin), companies "Garments New 29-08" and "Pharma New Company 23-09".
Tests: `tests/journeys/crm/` (9 tests), page objects `pages/crm/`, data `test_data/loyalty.py`.

## What the CRM menu holds (live)
| Company | CRM entries in the sidebar |
|---|---|
| Garments New 29-08 | Loyalty Management System, Pending Approvals |
| Pharma New Company 23-09 | Pending Approvals |

No lead / enquiry / follow-up / activity / pipeline screen exists in MargBooks (KB and live). Home Delivery and Prescription Reminder (KB) are not in either company's CRM menu.

## Screens
### Loyalty Management System (garments only) -> `/crm/loyalty/create-loyalty`
- Heading "Loyalty Setup"; fields (labelled textboxes/comboboxes): Point Apply on (Item Wise / Bill Amount), a disabled All/Selected Items combobox, Point Redeem Rate, Point Round Off (Auto/No), Point Calculation Method (Fraction / Range of Amount), Rs., Point, Minimum Amount, Minimum Points Required, Maximum Points Avail, OTP Required (No/Yes). Buttons "F10 Save" (no setup yet) or "F10 Update" (setup exists), "Esc Close", "Back".
- One setup per company: the screen loads `GET LoyalityPoints/GetLoyalitySetup` and updates it; there is no delete in the UI and no delete endpoint in the API (`codekb:MargBooks:api#c84bab19`, `#ecfffb4e`, `#20fe1588`).
- Save with nothing entered, or with only Point Redeem Rate: toast "Please Enter The Required Details!". Save with redeem rate, Rs. and Point: "Record Saved Successfully."; later saves: "Record Updated Successfully.".
- Update with Rs. emptied: refused with the same toast; the stored value is unchanged.
- Esc Close: confirmation "Are you sure you want to close?" (Yes/No).
- The Rs. field has a decimal input mask: `fill("")` and select-all + Backspace leave the value; Backspace key by key empties it.
- `/crm/loyalty/list` ("Loyalty/Coupon List", Create/F2, search, columns S.No., Point Apply On, Point Redeem Rate, Point Round Off, Point Calculation Method, Point, Action) stays EMPTY after a setup is saved (`POST LoyalityPoints/LoyalitySetupList` returns `Data: []`). Not in the menu. See N4.

### Pending Approvals -> `/crm/pending-grid`
- Heading "Pending Approvals", searchbox, radios Pending (default checked) / Approved / Reject / All, "Count: N", grid columns S.No., Transaction No, Transaction Type, Comment, Requested By, Created On, Action. Count 0 on garments.

### Home Delivery -> `/homedelivery` (by URL only, N2)
- Heading "Home Delivery", Excel / PDF links, button "Assign To/Alt+Y", Back, searchbox, "Last 7 Days" period button, radios Pending (checked) / Delivered / Counter Delivery / All, "Total Pending Orders : 0", columns Date, Invoice No., Customer, Amount, Total Discount, PaymentStatus, Area Name, Route Name, Contact Number, Status, Sale Person, Delivery Date.

## Test map
| Test | Case |
|---|---|
| test_crm_menu.py::test_crm_group_lists_loyalty_and_pending_approvals | CRM-01 |
| test_pending_approvals.py::test_pending_approvals_open_on_pending_requests | PA-01 |
| test_pending_approvals.py::test_all_requests_can_be_shown | PA-03 |
| test_home_delivery.py::test_home_delivery_opens_on_pending_bills | HD-01 |
| test_home_delivery.py::test_delivered_bills_can_be_shown | HD-04 |
| test_loyalty_setup.py::test_changed_loyalty_points_are_kept | LY-02 (edit, reopen, value kept; fixture restores) |
| test_loyalty_setup.py::test_loyalty_setup_without_amount_is_refused | LY-03 |
| test_loyalty_setup.py::test_loyalty_setup_keeps_amount_after_refused_update | LY-04 |
| test_loyalty_setup.py::test_closing_loyalty_setup_asks_for_confirmation | LY-05 |

Loyalty tests run in `xdist_group("garments-loyalty")`; the `loyalty_setup` fixture saves the earning rule (Rs., Point) it found back in teardown.

## NEEDS DECISION
- N1: The brief's "leads / enquiries / follow-ups / reminders / pipeline" CRM does not exist in MargBooks. Journey scoped to the real CRM menu. Confirm the scope (or retire J36 in favour of per-screen journeys).
- N2: Home Delivery and Prescription Reminder are not in the CRM menu of either company (they likely need Control Room / trade switches; enabling is tenant-wide, not done). Home Delivery is tested by URL; Prescription Reminder is untested (its route needs a `:type` not known).
- N3: Loyalty setup has no create -> delete life cycle: it is a single per-company record, saved once and then only updated. The tests cover edit + validations and restore the values. Create and delete cannot be automated without a DB reset.
- N4: The "Loyalty/Coupon List" (`/crm/loyalty/list`) stays empty although a setup exists. Defect or a list of something else (coupons)? Not asserted.
- N5: Pending Approvals end to end (send a purchase order for approval, approve/reject it) needs an approval workflow (`/approval-process`), which is tenant-wide and e-mails approvers (`careportal_enriched_v5.csv#eead3cf6`). Not done.
- N6: Home Delivery assign / status update needs a bill flagged for home delivery and a salesperson; not explored (time-boxed).

## Left on the tenant
- Garments New 29-08 now has a loyalty setup (Bill Amount, Point Redeem Rate 1, Round Off Auto, Fraction, Rs. 100 = 7 points, OTP No). It was created by the planner probe on 2026-10-09; before that the company had none. The app cannot delete it. Loyalty points may now show in garments POS / sale flows.
