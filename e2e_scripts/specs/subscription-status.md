# Plan: J34 Subscription / pricing / payment status (subscription-status)

Status: DRAFT for QA/BA review (2026-10-09). Scenarios: `scenarios/subscription-status.md`. Tests: `tests/journeys/subscription/`. Page objects: `pages/subscription/`.
Explored live on the QA tenant (login `garments`, company Garments New 29-08) with throwaway probe tests (deleted).

SAFETY: read-only. No test clicks Buy Now, Proceed, Apply (coupon), Contact Us, Company Mapping or anything that creates an order or leaves the app. Unit counts typed on the Add On tab are computed in the browser only (no request was sent while typing, checked in the probe); the page is closed at the end of each test, nothing is saved.

## What the live app shows
- Entry: header link "Settings" opens the Dashboard Setting panel; row "Manage subscription and plan" has a "Configure" button (`#btnAddonsubscription`). It opens `/support/managesubscription` (the route `/managesubscription` also works).
- Manage-Subscription (h1) with a "Back" button (returns to `/dashboard`) and four tabs (links in a tablist): My Current Plan (active on open), Manage Plan, Add On, Payment History.
- My Current Plan: card "Current Plan" with the plan name (Enterprise on this tenant), price (₹ 29,700), "Subscription Date : 01-Sept-2026", "Activation on : 01-Sept-2026", "Next Due Date : 01-Sept-2027" and a "Manage Plan" button that switches to the Manage Plan tab. "Add-ons Stats": Users 0/2, Invoice 99714/286 (one minute later 99713/287), Organisation 0/12, GSTIN 0/0, Whatapp Credits 2500/0; "Functional Add-ons Stats (Days)": Invoice Design 3/6, Barcode Design 3/6. Date format is dd-Mon-yyyy with "Sept".
- Manage Plan tab: wizard "Select Plan / Plan Details", cards Gold ₹ 5400/-, Diamond ₹ 8100/-, Platinum ₹ 15300/-, Platinum Plus ₹ 29700/- (each with "Buy Now", an `<a>` without href), Enterprise "Contact Us"; "GST Exclusive". Same content at `/subscription`.
- `/upgradesubscription` (no menu entry found; opened by URL): order table "Item / No. of Units / Amount (₹)/Yearly" with row "Enterprise Yearly - 29,700.00" and USERS / GSTIN add-on rows at 0.
- Public `/pricing` (marketing page, also reachable when logged in): old BASIC ₹8,991, SILVER ₹12,600, GOLD ₹25,200 cards and new Gold Lite ₹2,700, Gold ₹5,400, Diamond ₹8,100, Platinum ₹15,300, Enterprise ₹25,300, Platinum Plus ₹29,700; "Prices are exclusive of GST."; buttons "Try Now" -> /registration.
- Add On tab: table ADD-ONS / No. of Units / Total. Rows: Organisation ₹ 6120, SMS ₹ 0.25 (pack dropdown), USER ₹ 1530, GSTIN ₹25300, INVOICE ₹0.80, WHATSAPP CREDITS ₹.30, GST-VERIFICATION ₹10, Pro Plan (Verified) ₹12999, Basic Plan (Verified) ₹4499, Starter Plan (Unverified) ₹0, Business website ₹1000, Payroll ₹2500. Order Summary: Add-Ons, Tax @18%, Total; Cancel button, Proceed link, Apply Coupon Code.
  - USER units 1 / 2 / 3 gave line totals 1,370.71 / 2,741.42 / 4,112.14 on 2026-10-09 with Next Due Date 01-Sept-2027 (327 days left): line total = units x unit price x days left / 365, rounded to paise. Tax = 18% of the unrounded line total (4,112.137 -> 740.18), Total = line + tax (4,852.32).
  - Units -1 or "abc": line total 0.00.
- Payment History tab: Search box, "Time Period" select (Last 1 / 2 / 3 Month, default Last 1 Month), one entry per payment: h1 "Success ₹ 2,500.00" + "2026-10-08 11:03:22.23Z | TXN ID: ...". Clicking an entry shows its detail on the right (title e.g. "Payment for plan purchase(Enterprise)" or "Add On Payroll", amount, "Invoice Date- <same timestamp>", billing address). Raw ISO timestamps are shown.
- The header and the profile menu show the company, books year and licence number but no plan, validity or expiry. No renewal / expiry notice is shown (plan due in 2027). Status is shown only per payment ("Success").

## Test cases (all P2, read-only)
| ID | Test | Assertion source |
|---|---|---|
| SS-01 | `test_settings_configure_opens_current_plan` | live: URL + Current Plan card |
| SS-01 | `test_manage_plan_button_opens_manage_plan_tab` | live |
| SS-08 | `test_back_returns_to_dashboard` | live |
| SS-02 | `test_current_plan_shows_name_price_and_dates` | live (format only, no hardcoded values) |
| SS-12 | `test_next_due_date_is_one_billing_year_after_subscription` | derived: yearly billing (order summary "Yearly") |
| SS-12 | `test_active_plan_is_due_in_the_future` | derived |
| SS-03 | `test_current_plan_matches_renewal_order_summary` | cross-screen: name + price |
| SS-07 | `test_add_on_stats_show_two_counts` | live format n/m |
| SS-06 | `test_every_priced_plan_offers_buy_now` | live (visible only, never clicked) |
| SS-06 | `test_in_app_plan_prices_match_public_pricing` | cross-screen, plans priced on both |
| SS-05 | `test_add_on_line_total_is_pro_rated_to_next_due_date` | derived from unit price + Next Due Date |
| SS-05 | `test_order_summary_adds_18_percent_tax` | derived (label "Tax @18%") |
| SS-11 | `test_negative_units_cost_nothing` | live |
| SS-04 | `test_payment_history_entries_show_status_amount_and_txn` | live format |
| SS-04 | `test_selected_payment_detail_matches_entry` | cross-panel |
| SS-04 | `test_search_without_match_lists_no_payment` | expected behaviour of a search box; FAILS: defect D1 |

## App defects found
- D1 Payment History search does not filter. Steps: Manage-Subscription > Payment History, type a text that matches no entry ("zzzz") in Search, press Enter. Expected: no entries (or a "no record" message). Actual: all entries still listed (also for an amount "21789" and "Payroll").

## NEEDS DECISION
- ND1 Current plan "Enterprise" is shown at ₹ 29,700 with an invoice quota of 100000 (99714 + 286), which are the price and quota of Platinum Plus; Manage Plan shows Enterprise as "Contact Us" and public `/pricing` shows Enterprise ₹25,300. Is the tenant licence mislabelled, or is the current-plan card wrong? No test asserts plan-name-vs-catalogue until decided.
- ND2 "Last 1 Month" lists payments of 2026-09-01 on 2026-10-09 (38 days ago); Last 1/2/3 Month show the same list. Rolling month or calendar month? Suspected defect, not asserted.
- ND3 Add-ons Stats order is inconsistent: Invoice reads remaining/used (99714/286 -> 99713/287), Users and Organisation read used/total (0/2, 0/12), Whatapp Credits 2500/0. Which number is which? Tests assert only the n/m format.
- ND4 GSTIN add-on unit price ₹25300 equals the public Enterprise plan price; plausible data error.
- ND5 Public `/pricing` lists both "GOLD ₹25,200" (old) and "Gold ₹5,400"; old BASIC/SILVER/GOLD cards look stale. Price comparison uses exact, case-sensitive names, so "GOLD" is not compared.
- ND6 `/upgradesubscription` has no menu path found; opened by URL.
- ND7 Pro-rata depends on the date: the test uses the machine's local date; near midnight IST the app and test may differ by a day.
- ND8 Expiry / renewal notice (SS-09, SS-10) and Trial Expired cannot be produced on the shared tenant (plan due 01-Sept-2027): not covered.
- Typos seen: "Whatapp Credits", public page "verion", "Custome Report", "shoft copy", "Brakeage".

## Data and cleanup
No data is created. Add On unit fields are never saved (the browser context is closed after each test). Plan and licence are per login, so no company pin is needed.
