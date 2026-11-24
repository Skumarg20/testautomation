# Plan: J22 Dashboard widgets and summary tiles (dashboard)

Scenario pack: `scenarios/dashboard.md`. Tests: `tests/journeys/dashboard/`. Page objects: `pages/dashboard/` (`figures.py`, `period_filter.py`, `dashboard_links.py`); `pages/dashboard_page.py` is unchanged.
Status: DRAFT for QA/BA review. Observed live on 2026-10-09 (QA tenant, `chemist` login, company "Garments New 29-08 (GANE29)", books 01-04-2026..31-03-2027, app V. 4.3.598.b). No test ids on this screen.

## Preconditions and test data
- Company pinned to Garments New 29-08 (`CompanySwitchPage.ensure_company`), because the login's company is shared state.
- The chosen period is kept for the login (it is stored as `DashBoardPeriod` and came back in a new browser process), so the `period_filter` fixture chooses the starting period again after each test and the period tests share the xdist group `dashboard-period`.
- Only one test creates data: `QA-<run_id>-Item` (Master > Item, mandatory fields, no opening stock), deleted in teardown.
- Card figures are not owned: other suites post sales/purchases on this company in parallel. Card figures are compared only with other dashboard figures read moments apart.

## Screen (verified live)
| Thing | What and locator |
|---|---|
| Route | `/dashboard` (also `/`). Title "Dashboard", button "Refresh Dashboard", h3 "Last Sync : dd-mm-yyyy \| hh:mm AM" |
| Period picker | button named by the period ("Last 30 Days" by default, or "dd-mm-yyyy To dd-mm-yyyy"); its menu has links Today, This Week, This Month, Previous Month, Yesterday, Last 7 Days, Last 30 Days, then "Custom" with two text boxes (From, To; min 2026-04-01 max 2027-03-31) and "Apply" |
| Summary cards | links "Net Sale", "Net Purchase", "Gross Profit"; each with a change "x.xxx%" and h4 "₹current from ₹previous" (three decimals); a small line chart per period |
| Tile sections | Fund Summary (Bank Balance, Cash Balance, Cash Deposited, Withdrawal, Cheque For Deposit), Outstanding In Value (Current/Overdue Receivable, Current/Overdue Payable), Business In Value (CGST/SGST/IGST Payable), New Added In No. (Items, Agency, Customer, Category, Supplier), Stock In No. (Reorder, Dump Stock, Minimum Stock), Pending In No. (Sales Challan, Sales Order, Purchase Order, Purchase Challan). Each tile is a link "Name ₹figure" or "Name count" |
| Header | "Shortcut" opens the SHORTCUT KEYS panel (COMMON KEYS ... NAVIGATION HOME/DASHBOARD Alt + H ...) |
| Data calls | `POST DashBoard/MainDashboardHeaderData` (Total/Previous Sale, Purchase, Income, Expense), `NEWLYADDEDASHBOARD`, `GetFundSummary`, `Dashboardoutstanding`, `DashboardBusinessData`, `Dashboardstock`, `PENDINGDASHBOARDDATA`, `GET GetGrossProfit`. Body has `dateType`, `fromDate`, `toDate`, `callType`. |
| Caching | First paint = figures of the last sync (`callType` 0). A period choice or Refresh recalculates (`callType` 1); Refresh also moves Last Sync to now. `DashboardFigures` waits for these calls and for the screen to show what they returned. |

## Observed figures (sample values, not asserted)
This Month: Net Sale ₹0.000 from ₹444.000; Previous Month: ₹444.000 from ₹4260.000 (so "from" = the whole previous month). Today: Items 1, after creating an item 2. Sale Register for September shows 568.32 = 444 x 1.28, i.e. the register includes GST and Net Sale does not.

## Tests
| Test | Scenario | Asserts |
|---|---|---|
| `test_summary_card_shows_current_and_previous_figure[3 cards]` | DB-01 | h4 matches "₹n from ₹n", a percentage shown |
| `test_tile_section_shows_its_tiles[6 sections]` | DB-02 | section title and every tile listed above |
| `test_shortcut_keys_panel_lists_the_home_shortcut` | DB-08 | panel heading, "HOME/DASHBOARD", "Alt + H" |
| `test_home_shortcut_returns_to_the_dashboard` | DB-08 | Sale Register, then Alt+H -> `/dashboard` |
| `test_summary_card_title_opens_its_report[3 cards]` | DB-07 | `/report/register/sale` "Sale Register", `/report/register/purchase` "Purchase Register", `/report/grossreport/gp-default` "Gross Profit" (was `/report/grossProfitLoss` "Gross Profit/Loss" until V 4.3.599.b; new target confirmed by the user 2026-10-14) |
| `test_picker_offers_predefined_periods_and_a_custom_range` | DB-03 | seven options + From/To/Apply |
| `test_choosing_a_period_relabels_the_picker` | DB-04 | label "Today", figures recalculated |
| `test_chosen_period_is_kept_when_the_dashboard_is_opened_again` | DB-05 | "This Week" after navigating to the dashboard again |
| `test_refresh_moves_last_sync_to_today` | DB-06 | Last Sync date = today |
| `test_custom_from_date_keeps_the_day_typed_in_app_format` | DB-13 | typed "01-mm-yyyy" stays after Tab (FAILS: defect D1) |
| `test_previous_figure_of_this_month_is_the_previous_month_figure` | DB-10 | per card: This Month "from" = Previous Month current |
| `test_change_percent_follows_from_current_and_previous_figure` | DB-11, DB-17 | per card for Previous Month: (cur - prev) / prev x 100 to 3 places, 0.000 when prev is 0 |
| `test_item_added_today_is_counted_in_new_added_items` | DB-09 | Today's Items tile = before + 1 after Refresh |

## Defects seen
- D1 (DB-13): the custom From/To boxes read typed text as mm-dd-yyyy while every date on the screen is dd-mm-yyyy. Typing "01-10-2026" and pressing Tab shows "10-01-2026", and Apply sends `fromDate 2026-01-10` (seen in the request body); "09-10-2026" became 2026-09-10. Typing "01-04-2026" gave 2026-01-04, before the books year, and was accepted. Possibly the cause of MB-024396 "date filter is not working".
- D2 (DB-14, not asserted, see N2): From 31-03-2027 To 04-01-2026 was applied without any message; the cards showed ₹0.000 and the reversed range stayed chosen after a reload.

## NEEDS DECISION
- N1 (DB-12): Net Sale is net of GST, while the Sale Register it opens includes GST (Sep: 444 vs 568.32), and the register opens on the whole books year instead of the dashboard period. Which report should Net Sale agree with (Sales Analysis? Sale register taxable value?), and should the drill-down carry the period? Until then no tile-vs-report figure test.
- N2 (DB-14, DB-15): what should happen for From after To, or a range outside the books year: refuse with a message, or swap? Test to be written once decided.
- N3 (DB-16): Fund Summary, Outstanding, Business, New Added, Stock and Pending tiles are links but a click (and a double click on Cash Balance) stays on the dashboard. Should they drill into the matching report?
- N4: change percent when previous is 0 and current is not (0 or "100%"?) is unverified; the test only covers what this month data shows.
- N5: is a custom range expected to persist for the login like predefined periods (it does today)? The teardown cannot restore a custom range exactly and falls back to Last 30 Days.
- N6 (DB-09): the Items count is tenant-wide; an item added by another suite in the same seconds would make the count +2. Accept the small flake risk or move this test to a quiet window.

## Not covered (and why)
- DB-18 role-based tiles (no limited user), DB-19 financial-year switch (J company-switch owns it), Dashboard Setting panel (Control Room, theme, language: tenant-wide settings), customise dashboard (`/dash-config`, changes the shared layout), charts' points (canvas, no accessible values), Alt+N and other shortcuts that open new bills (would leave unsaved drafts), visual layer (J22 also lists `visual`; out of scope of this e2e pass).
