# Porting notes: from `margbooks-automation-margbooksteam` (TypeScript) to this project (Python)

## What was ported
| Original | Here |
|---|---|
| `src/pages/LoginPage.ts`, `login-setup/login.js` (git history) | `pages/login_page.py`, `fixtures/session.py` (single-step and two-step login, sessionStorage saved) |
| `src/components/Header.ts`, `Footer.ts`, `Popup.ts` | `pages/components/` |
| `ChemistGridAction.ts` (git history), `GeneralGridAction.ts` | `pages/grid/chemist_sale_grid.py` (+ `ag_grid.py`, `item_picker.py`, `batch_window.py`) |
| `SaleBillPage.ts`, ledger/rate pages | `pages/sale/` (`sale_bill.py` is a new facade over header, grid, footer, saved bill) |
| `CommonPage.ts`, GST/item-discount settings, `DataBaseRepairPage.ts` | `pages/settings/` |
| `src/test-data/**` | `test_data/` (typed dataclasses) |
| `src/tests/chemist/**` (about 50 tests) | `tests/journeys/chemist/` |

## Deliberate changes
- Accounts are trades (`chemist`, `pharma`, `retail`, `grocery`), not roles.
- Random 0-9 offsets in discount and rate data are now fixed constants, so runs repeat.
- `waitForTimeout` sleeps were replaced with waits on elements. This is the riskiest change: it was not run against the app.
- Flag arguments were split (`replace_item` versus `add_item`; the party-wise page's two booleans became "apply the values that are set").
- `test.only` (in the rate and special-discount specs) was dropped, so all tests run.
- Rate H originally set the default rate to G; the parametrised test uses the right letter.
- EXP batch: the original selected a batch again after the "Expired" popup; this port stops after the popup. Confirm against the app.
- Tests that created a bill and only clicked Save now assert that the print preview appears. This assumes the preview opens after saving (the old modification flow clicked its Close button first).
- Tests that changed global settings share one xdist group so they do not race on the tenant.

## Not ported (and why)
- Outlook email test and `reporters/`, `runner-ui/`, `runner-server/`: not test logic.
- k6 load tests in `src/performance/`: JavaScript load scripts; keep using them as they are.
- Pharma grid (`PharmaGridAction.ts`): unfinished upstream ("new code 9th sept"), no pharma tests exist.
- Item-wise, agency-wise and party-wise discount pages: their specs were removed from the original repo. Their test data is ported (`test_data/discounts.py`).
- GST and bill-discount amount checks (GS-01/02): the original calculation helper (`chemistCalculation`) was never committed.

## Verified vs not verified
- Verified offline (`tests/framework/`): grid reading and editing, discount entry order, header date and field filling, login flows, data and matrix integrity, with HTML mocks.
- NOT verified: anything that needs the real app. Selectors, waits, the assumed print-preview check, batch handling and Control Room flows were ported by reading the TypeScript and have never run in Python.

## Security finding in the original repo (act on it)
`src/config/.env*` files with usernames and passwords are committed to GitLab, and `auth/**/auth.json` and `session.json` (session tokens) appear in its history. Rotate those credentials, remove the files from history, and keep real values only in a local `.env`.
