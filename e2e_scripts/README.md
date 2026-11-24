# How this project works (start here)

This project opens the MargBooks website in a real browser (Playwright), clicks through it like a user, and checks the results. Tests are written in Python and run by `pytest`.

## The one idea to understand

```
   tests/            "WHAT to check"       e.g. a sales invoice charges IGST
      │  uses
      ▼
   pages/            "HOW to click"        e.g. fill the Email box, press Sign in
      │  uses
      ▼
   Playwright ──► the MargBooks website (QA server)

   conftest.py + fixtures/ + test_data/    prepare things for the tests:
   logged-in browser, API client, fake customers/GSTINs
```

You write **tests** (what to check) and **pages** (how to click). Everything else is already built and you rarely touch it.

## What each folder does

| Folder / file | What it is | Do you edit it? |
|---|---|---|
| `tests/journeys/<journey>/` | The real tests, one folder per business journey (auth, sales, purchase...). **Most of your code goes here.** | Yes, daily |
| `pages/` | One file per screen of the website (`login_page.py`, `dashboard_page.py`). Holds the clicking and the locators. | Yes, when a new screen is tested |
| `pages/sale/`, `pages/purchase/` | Split by app generation: `chemist/` (chemist sale bill, ledger discounts, rates), `garments/` (garments Alt+N / Alt+P windows), `documents/` (Sale and Purchase order, challan, bill, return screens). | Yes |
| `pages/accounting/`, `pages/settings/`, `pages/reports/` | Voucher screens, Control Room and GST settings, GST report. | Yes |
| `pages/components/`, `pages/grid/` | Shared widgets (footer, popup, totals) and grid helpers. | Rarely |
| `scenarios/` | Lists of cases to test, as tables (what, expected result, source). The analyst agent writes these. | Review, sometimes edit |
| `specs/` | Test plans written by the planner agent after exploring the site. You approve them. | Review only |
| `test_data/factory.py` | Makes fake data: unique names, valid and invalid GSTINs. | Add a method when you need new data |
| `fixtures/api_client.py` | Talks to the backend API directly (fast data setup and cleanup). | Add API calls when needed |
| `fixtures/session.py` | Logs in each role (chemist, pharma, retail, grocery) once and reuses it. | Rarely |
| `conftest.py` | Hands the above to tests: `page_as`, `api`, `data`, `run_id`. | Rarely |
| `config/settings.py` | Reads `.env` (QA URL, logins) and refuses production URLs. | Rarely |
| `tests/framework/` | Self-checks of this framework. They need no website. | Only when you change framework code |
| `coverage/journey-matrix.json` | The list of 10 journeys and their status (not started / planned / generated / passing). Feeds the dashboard. | Yes, update status |
| `scripts/report_coverage.py` | Turns the matrix and last run into the dashboard data. | No |
| `docs/` | Rules (`clean-code-rules.md`) and the edge-case checklist. | Read |
| `.claude/agents/` | The four AI helpers: analyst, planner, generator, healer. | Rarely |
| `.env` | Your private QA URL, login style and trade-account logins. **You create it from `.env.example`. Never commit it.** | Once |
| `results/`, `.auth/` | Generated reports and saved logins. Ignore them. | No |
| `Makefile`, `pyproject.toml` | Commands and settings for pytest, ruff, mypy. | Rarely |

Outside this folder: `../dashboard/` is the progress page, `../.github/workflows/` runs the tests in CI.

## First-time setup (once)

```bash
cd ~/margProject/ai-projects/margbooks-test-automation/e2e
cp .env.example .env        # then open .env and fill the QA URL, login style and the trade accounts' logins
make framework              # should show passed; proves the setup works
```

## Daily commands

| Command | What it does |
|---|---|
| `make smoke` | Runs only the most important tests (`@p0`) |
| `make test` | Runs all tests, in parallel |
| `.venv/bin/python -m pytest tests/journeys/auth -k chemist --headed` | Runs one test and shows the browser |
| `make lint typecheck` | Checks code quality (run before committing) |
| `make coverage` | Rebuilds the dashboard data |

## Where do I write code? A worked example

Goal: test "create a customer".

1. **Page object, in `pages/customer_page.py`:** how to click.
   ```python
   from pages.base_page import BasePage


   class CustomerPage(BasePage):
       PATH = "/customers"

       def open(self) -> None:
           self.goto(self.PATH)

       def create(self, name: str, gstin: str) -> None:
           self.page.get_by_label("Name").fill(name)
           self.page.get_by_label("GSTIN").fill(gstin)
           self.page.get_by_role("button", name="Save").click()
   ```
2. **Test, in `tests/journeys/masters/test_customer.py`:** what to check.
   ```python
   import pytest
   from playwright.sync_api import expect
   from pages.customer_page import CustomerPage

   pytestmark = [pytest.mark.p1, pytest.mark.journey("masters")]


   def test_customer_with_valid_gstin_is_saved(page_as, data) -> None:
       customers = CustomerPage(page_as("chemist"))
       name = data.party_name("Customer")

       customers.open()
       customers.create(name, data.valid_gstin())

       expect(customers.page.get_by_text(name)).to_be_visible()
   ```
3. **Matrix:** set the journey's `status` in `coverage/journey-matrix.json` to `generated`. A human changes it to `passing` once it is green and reviewed.
4. Run it: `.venv/bin/python -m pytest tests/journeys/masters --headed`, then `make lint typecheck`.

Inside a test you get these helpers automatically (you just name them as parameters):
- `page_as("chemist")`: a browser page already logged in as that role (or the test skips if no login is set).
- `data`: fake data, e.g. `data.party_name()`, `data.valid_gstin()`, `data.invalid_gstin()`.
- `api`: direct backend calls for fast setup and cleanup.
- `run_id`: a short unique id for this run.

## The easier way: let the AI helpers write it

You don't have to hand-write every test. For each journey, in Claude Code from this folder:

1. **test-analyst**: "Write the scenario pack for journey `sales-invoice`." It reads your KB and code and fills `scenarios/sales-invoice.md`.
2. **test-planner**: "Plan `sales-invoice` from its scenarios." It explores the live site and writes `specs/sales-invoice.md`. **You review this.**
3. **test-generator**: "Generate tests from the approved plan." It writes the page objects and tests for you.
4. **test-healer**: "Fix the failing tests." It repairs broken locators but never changes expected values; real app bugs are reported to you.

Your job: review the plan, review the generated tests, and decide on any "NEEDS DECISION" or "APP DEFECT" it reports.

## Rules in one minute

- Tests say *what*; page objects say *how*. A test never contains a raw selector or URL.
- Each test makes its own data and does not depend on other tests.
- Mark every test file with a priority (`p0`/`p1`/`p2`) and a `journey("<id>")`.
- Names say what they do. Functions are small. No commented-out code. Full list: `docs/clean-code-rules.md`.
- Never edit an expected value just to make a test pass.
