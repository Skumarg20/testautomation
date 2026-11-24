# Flow: manual Excel cases to running Playwright tests

No test code is hand-written. Every test comes out of the project's Playwright MCP agents (`.claude/agents/`).

```
 [1] Excel files (3)                       DONE
      |  read with openpyxl, drop exact duplicates
      v
 [2] scenarios/manual-sale-purchase.md     DONE   329 unique cases, grouped, each tagged with what it needs
      |
      v
 [3] HUMAN: pick the pilot batch + confirm environment          <-- we are here
      |    - which account/trade (garments is the only one on file)
      |    - OK to create bills and flip settings on pre-prod
      v
 [4] test-analyst     scenarios + KB + code  -> scenarios/<id>.md (adds cited expected values)
      |               vague "works correctly" rows become NEEDS DECISION, not guessed
      v
 [5] test-planner     Playwright MCP drives the live app (real labels, test ids)
      |               -> specs/<id>.md
      v
 [6] HUMAN: review specs/<id>.md (approve / fix expected values)
      v
 [7] test-generator   Playwright MCP verifies each locator live
      |               -> pages/*.py + tests/journeys/<module>/test_*.py
      |               -> journey status = generated
      v
 [8] run              .venv/bin/python -m pytest <file>   (settings tests grouped on one xdist worker)
      |
      +-- all green ------------------------------> [10]
      |
      +-- fails
            v
 [9] test-healer      locator/timing fixes only
      |               wrong expected value => report APP DEFECT, never loosen the assertion
      +--> re-run [8]
      v
 [10] report          pass / fail / defect / skipped(with reason) per case ID,
                      make coverage -> dashboard. Only a human sets status to passing.
```

## Pilot order (smallest risk first)
1. Calculation cases: GST inclusive/exclusive, CGST+SGST vs IGST, item and bill discount, round-off. They create and delete their own bills.
2. Bill lifecycle: create, modify, delete, validation (blank/zero/negative qty and rate).
3. Settings toggles (one worker, restore settings after each test).
4. Chemist-only: batch, expiry, patient/doctor, stock effect. Needs a chemist account.
5. Skipped for now: WhatsApp/email/SMS (external), permissions and concurrency (need role accounts).
