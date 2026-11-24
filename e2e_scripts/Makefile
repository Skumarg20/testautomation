PY := .venv/bin/python
# The framework run keeps its own reports so it never overwrites results/report.json of the last real run.
FRAMEWORK_REPORTS := --junitxml=results/framework/junit.xml --json-report-file=results/framework/report.json --html=results/framework/report.html
# The planning workbook kept outside the repo; override with `make coverage TIMELINE_XLSX=/path/to/file.xlsx`.
TIMELINE_XLSX ?= $(HOME)/Downloads/MargBooks_E2E_Test_Automation_Timeline_updated.xlsx
.PHONY: setup framework smoke test parallel lint typecheck healer-check coverage report

setup:            ## create venv, install deps and browsers
	python3 -m venv .venv && .venv/bin/pip install -e '.[dev]' && .venv/bin/playwright install chromium webkit
framework:        ## framework self-checks, no app needed (reports in results/framework/, not the run report)
	$(PY) -m pytest -m framework $(FRAMEWORK_REPORTS)
smoke:            ## @p0 journeys
	$(PY) -m pytest -m p0 -n $${WORKERS:-4}
test:             ## everything, in parallel
	$(PY) -m pytest -n $${WORKERS:-4}
lint:
	.venv/bin/ruff check . && .venv/bin/ruff format --check .
typecheck:
	.venv/bin/mypy config fixtures test_data pages scripts tests plugins visual conftest.py
healer-check:     ## healer log, assertion and skip governance versus BASE (default origin/main)
	$(PY) scripts/check_healer_log.py --base $${BASE:-origin/main}
coverage:         ## rebuild dashboard data and the timeline workbook's Journey Matrix sheet (skipped if absent)
	$(PY) -m scripts.report_coverage
	$(PY) -m scripts.update_timeline "$(TIMELINE_XLSX)"
report:           ## open last HTML report
	xdg-open results/report.html
