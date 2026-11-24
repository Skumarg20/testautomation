# Python test scripts in this project

This folder is a copy of `margbooks-test-automation/e2e` from the ai-projects repo
(commit `c234577`). Read `README.md` here for how the scripts themselves work.

Test Studio lists every script under **Test cases > Scripts**, module wise, and a test case
imported from the same scenario shows its script under "Python script" with a Run button.

## Where they run

**From Test Studio: exactly like Studio tests.** The URL, the login and the company come from Test Studio's
Settings > App under test (team mode: each QA's own MargBooks login). `e2e_scripts/.env` is not used for them.

* The companies the scripts were written for are replaced by QA test companies
  (`config/e2e_company_map.json`, e.g. "Pharma New Company 23-09" -> QA Chemist). After signing in, the session
  opens the Settings company when it is a QA test company, else QA Chemist.
* **QA guard** (`fixtures/studio_guard.py`): every request that saves, changes or deletes data goes out only when
  its `complinkid` is a QA test company; anything else is aborted and logged as `[studio-guard] BLOCKED`. Control
  Room / User Power saves are refused everywhere (settings change only through Studio steps, which refuse one-way
  settings). With "Allow tests that create or change data" off in Settings, no write goes out at all.
* The QA companies' ids are read once from the app's company list and cached in `config/qa_company_ids.json`
  (delete it to read them again, e.g. after new QA companies are made).
* The production host is accepted by `config/settings.py` only with `STUDIO_QA_GUARD=1`, which only Test Studio
  sets, together with the guard.

**Outside Test Studio** (`pytest` by hand): as before, only premargbooks.com / localhost with the `.env` logins.

## One-time setup (Windows)

The scripts need Playwright below 1.64 and pytest-playwright, so they have their own virtualenv,
separate from the project's `.venv`:

```
cd e2e_scripts
python -m venv .venv
.venv\Scripts\pip install "playwright>=1.50,<1.64" "pytest>=8" "pytest-playwright>=0.7" "pytest-xdist>=3.6" ^
    "pytest-timeout>=2.3" "pytest-json-report>=1.5" "pytest-html>=4" "pydantic>=2.7" "pydantic-settings>=2.3" ^
    "python-dotenv>=1.0" "axe-playwright-python>=0.1.4" "httpx>=0.27" "pillow>=10" "pixelmatch>=0.3" ^
    "pytest-rerunfailures>=14" tzdata
.venv\Scripts\python -m playwright install chromium
copy .env.example .env
```

Fill `.env` with the premargbooks.com QA URL, `LOGIN_STYLE` and the `QA_*_USER` / `QA_*_PASS`
accounts. A test whose account has no login is skipped with a reason, not failed.

## Running outside Test Studio

```
set PYTHONUTF8=1
.venv\Scripts\python -m pytest tests/journeys/sales/test_sales_invoice_gst.py -n 0
```

`PYTHONUTF8=1` matters on Windows: some scripts read files without naming an encoding.
Reports go to `results/` (git-ignored).

## Changes made here, compared with the ai-projects copy

- `fixtures/visual.py`, `scripts/healer_log.py`: file locks fall back to `msvcrt` on Windows
  (the originals use `fcntl`, which exists only on Linux/macOS).
- Test Studio mode (only with `STUDIO_QA_GUARD=1`): `config/settings.py` (Studio hosts, company map),
  `fixtures/studio_guard.py` (new), `fixtures/session.py` (guard on every context, QA company after sign-in,
  Organisation List after sign-in), `pages/company_switch_page.py` (company names mapped),
  `tests/framework/test_studio_guard.py` (new).
- `plugins/studio_live.py` (new, only with `STUDIO_LIVE_DIR`): every browser action and expect() of a script is a
  step with a screenshot (`steps.jsonl`, `stepNNN.png`); with `QA_RECORD=1` the run's video. Test Studio shows the
  steps live like its own runs and saves the run in Reports (steps, screenshots, video). Typed logins and passwords
  are shown as ***. Tests: `tests/framework/test_studio_live.py`.
- `conftest.py`: `pytest.register_assert_rewrite("fixtures.steps", "fixtures.console_capture")` before the
  imports. `fixtures/session.py` imports both plugin modules before pytest loads them, which printed
  "PytestAssertRewriteWarning: Module already imported so cannot be rewritten" on every run.

## Accounts (only for runs outside Test Studio)

Every `QA_*_USER` must be a **registered premargbooks.com account**. A books5 / books6 (margbooks.com) login
does not exist on premargbooks: the login page answers "Please Enter The Registered Mobile No. Or Email Id",
the password step never comes, and every script stops in its login with
`waiting for locator("input#password") to be visible`. Test Studio shows this as "could not log in to
premargbooks.com" under the script's run.

Known on Windows: 5 framework self-checks still fail (`test_healer_scripts.py` uses `os.pread`,
Linux only; two `test_console_events.py` checks). They test the healer and QA-console tooling, not
the website journeys. 733 of 738 self-checks pass.
