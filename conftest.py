import json
import logging
import time
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

from config.settings import settings
from framework.base_page import BasePage
from framework.auth import login
from framework import safety
from framework.browser import launch, describe_window
from framework.locator_store import store

logging.basicConfig(level=logging.INFO, format="%(message)s")
RESULTS: list[dict] = []


def pytest_configure(config):
    """Har pytest run ka apna timestamped folder."""
    settings.init_run("pytest run")
    config.option.htmlpath = str(settings.ARTIFACTS / "report.html")


def pytest_addoption(parser):
    parser.addoption("--tags", default="", help="Comma separated tags filter, e.g. --tags smoke,sales")
    parser.addoption("--case", default="", help="Run a single case id, e.g. --case TC_SALE_001")


@pytest.fixture(scope="session")
def browser_ctx():
    settings.validate()
    settings.ARTIFACTS.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as pw:
        browser, ctx = launch(pw, record_video=True)
        ctx.tracing.start(screenshots=True, snapshots=True, sources=True)
        yield ctx
        ctx.tracing.stop(path=str(settings.ARTIFACTS / "trace.zip"))
        ctx.close()
        browser.close()
        store.save()   # self-healed locator order persist


@pytest.fixture(scope="session")
def logged_in(browser_ctx):
    """Session-level login. storage_state reuse hone se baaki tests fast chalte hain."""
    page = browser_ctx.new_page()
    login(page)
    yield page
    page.close()


@pytest.fixture
def app(logged_in):
    return BasePage(logged_in)


@pytest.fixture(autouse=True)
def guard_destructive(request):
    if request.node.get_closest_marker("destructive") and not settings.ALLOW_DESTRUCTIVE:
        pytest.skip("ALLOW_DESTRUCTIVE=false -- data likhne wale tests skip. Demo account pe true karo.")


@pytest.fixture(autouse=True)
def skip_if_module_off(request):
    """'You are not authorized' = Control Room me module OFF = SKIP, FAIL nahi."""
    yield


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    if rep.when == "call":
        RESULTS.append({
            "nodeid": rep.nodeid,
            "case_id": getattr(item, "case_id", None),
            "outcome": rep.outcome,
            "duration": round(rep.duration, 2),
            "error": str(rep.longrepr)[:4000] if rep.failed else None,
            "ts": time.time(),
        })


def pytest_sessionfinish(session, exitstatus):
    settings.ARTIFACTS.mkdir(parents=True, exist_ok=True)
    (settings.ARTIFACTS / "results.json").write_text(json.dumps(RESULTS, indent=2))
    passed = sum(1 for r in RESULTS if r["outcome"] == "passed")
    failed = sum(1 for r in RESULTS if r["outcome"] == "failed")
    print(f"\n{'='*55}")
    print(f"  {passed} passed, {failed} failed")
    print(f"  Report: {settings.ARTIFACTS / 'report.html'}")
    print(f"{'='*55}")
