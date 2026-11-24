# Test environment (W1-01)

Recorded 2026-10-05 from a live check. No secrets here; credentials live in `e2e/.env` (gitignored) and CI secrets.

| Item | Value |
|---|---|
| Environment | pre-production ("premargbooks") |
| App host (`MARGBOOKS_QA_URL`) | `https://premargbooks.com` |
| Login host (`MARGBOOKS_LOGIN_URL`) | `https://accounts.premargbooks.com/login` |
| Login style | `two_step`: `#userid` + `#SIGNin`, then `input#password` + submit |
| Captcha / OTP on this login | none seen for this account (decision D2 stays open for other accounts) |
| Landing page | `/dashboard` (about 15 s after submit) |
| App version seen | V. 4.3.597.b |
| Company behind the known account | "Garments New 29-08 (GANE29)", books 01-04-2026 to 31-03-2027, trade: garments |
| Settings host guard | accepts `premargbooks` hosts; production `margbooks.com` is rejected |

## Accounts
| Account key | Env vars | Status |
|---|---|---|
| garments | `QA_GARMENTS_USER/PASS` | available |
| chemist, pharma, retail, grocery | `QA_<TRADE>_USER/PASS` | not provided; tests skip with a reason |
| admin, operator, accountant | `QA_<ROLE>_USER/PASS` | not provided; role tests skip until supplied (W1-03 lists exactly what is needed) |

## Reset / seed
Not yet decided (D3). The garments company holds existing data (for example a cash balance), so Week 1 tests create records prefixed `QA-<run_id>` and must not edit or delete data they did not create.

## Open items
Role accounts; a second company for isolation; a chemist account for the ported suite; permission to call the demo-restore endpoints; confirmation that this pre-prod tenant may receive test bills.
