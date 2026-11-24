# MargBooks E2E (Python): conventions

New here? Read `README.md` first (folder guide and a worked example).

Python 3.10+ · pytest · Playwright (sync API) via pytest-playwright · pytest-xdist. Targets the MargBooks (Angular + .NET 8) QA tenant, never production.

## Commands (from `e2e/`, venv at `.venv`)
- `make setup`      venv + deps + browsers
- `make framework`  framework self-checks, no app needed
- `make smoke`      `-m p0` in parallel
- `make test`       everything in parallel (`WORKERS=4` default; `WORKERS=50 make test` needs a `QA_POOL` with one user per worker)
- `make lint` / `make typecheck`
- `make coverage`   rebuild `../dashboard/public/data/summary.json`
- Single test: `.venv/bin/python -m pytest tests/journeys/auth/test_login.py -k chemist --headed`

## Setup
`cp .env.example .env`, fill the QA URL, `LOGIN_STYLE` and the trade accounts (chemist, pharma, retail, grocery). Tests that need an account skip, with a reason, if it has no credentials.

## Test folders
`tests/journeys/` holds the browser journey tests (the `e2e` layer in the QA Console and the matrix). The other folders are named for their layer: `tests/api/`, `tests/a11y/`, `tests/visual/`, `tests/framework/`.

## Rules
0. Tests that change tenant-wide settings (Control Room, GST type, rates) share one tenant: mark them `pytest.mark.xdist_group("chemist-tenant")` so they run on one worker (`--dist=loadgroup`).
1. Fixtures only from `conftest.py`: `page_as(account)`, `api`, `data`, `run_id`. One login per account per xdist worker (sessionStorage is saved and restored too).
2. Locators: test id > role > label > text. No CSS/XPath, no `time.sleep`; rely on `expect()` auto-wait.
3. Page objects in `pages/` (one class per screen, snake_case modules). Shared widgets in `pages/components/`.
4. Every test creates its own data via `data`/`api` and never depends on other tests or order.
5. Mark every module: `pytestmark = [pytest.mark.p0|p1|p2, pytest.mark.journey("<id>")]`, id from `coverage/journey-matrix.json`. Markers are strict; register new ones in `pyproject.toml`.
6. Type-hint everything; `ruff` and `mypy` must pass. Settings via `config/settings.py` only; never read `os.environ` in tests.
7. Secrets only in `.env`/CI secrets. `.auth/`, `.env`, `results/` are gitignored; never read them.
8. Healer rule: locator/timing fixes are fine. Never change an expected value or loosen an assertion to pass; report an app defect instead. Assertion changes need human review.
9. Update journey `status` in `coverage/journey-matrix.json` (not_started, planned, generated, passing). Only a human promotes to `passing`.

## Clean Code rules
Full rule set from R. C. Martin's *Clean Code* (all chapters and the ch. 17 smell catalogue), adapted to this project. Mandatory for all code, including agent-written code.

@docs/clean-code-rules.md

Most-used reminders: names reveal intent; functions do one thing, hardly ever 20 lines, at most 3 args, no boolean flags; comments say why, never commented-out code; one concept per test; no duplication; no `float` for money; never override a safety (lint, types, tests) to get green; leave code cleaner than you found it.

## Agent workflow (Claude Code subagents in `.claude/agents/`)
test-analyst (KB + code -> `scenarios/<id>.md`, cited) -> test-planner (live app -> `specs/<id>.md`, human review) -> test-generator (-> `tests/journeys/`) -> test-healer (on failures).
Playwright's own Node-based agents are not used; these subagents use the Playwright MCP (`.mcp.json`, needs Node only to launch the MCP server).
