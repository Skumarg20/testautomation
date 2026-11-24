"""Contract C2: shared fixtures. Specs use `page_as(account)`, `api`, `data`, `run_id`, plus page objects."""

import uuid
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest
from playwright.sync_api import Browser, BrowserContext, Page

# fixtures.session imports these two plugin modules before pytest loads them from pytest_plugins below; registering
# them first keeps pytest's assert rewriting for them (else: PytestAssertRewriteWarning "Module already imported").
pytest.register_assert_rewrite("fixtures.steps", "fixtures.console_capture")

from config.settings import Account, settings  # noqa: E402
from fixtures.api_client import ApiClient
from fixtures.recording import finish_recording
from fixtures.session import (
    AccountSessions,
    MissingCredentialsError,
    instrument_context,
    recording_folder_for,
    report_missing_credentials,
    with_recording,
)
from test_data.factory import DataFactory

# Console plugins are inert unless the QA Console enables them (env switches) or a data file exists.
pytest_plugins = [
    "plugins.quarantine",
    "plugins.permanent_gate",
    "fixtures.steps",
    "fixtures.console_capture",
    "fixtures.visual",
    "plugins.studio_live",  # inert unless Test Studio runs the script (STUDIO_LIVE_DIR)
]

RUN_ID_LENGTH = 8
RECORDINGS_ROOT = Path("results/recordings")


@pytest.fixture(scope="session")
def base_url() -> str:
    return settings.margbooks_qa_url


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args: dict[str, Any]) -> dict[str, Any]:
    """Every context blocks service workers: the app's worker answers API calls itself, which Playwright
    cannot see, so `page.route` stubs and send-guards on logged-in pages were silently bypassed (J21, N5)."""
    return {**browser_context_args, "service_workers": "block"}


@pytest.fixture
def run_id() -> str:
    return uuid.uuid4().hex[:RUN_ID_LENGTH]


@pytest.fixture
def data(run_id: str) -> DataFactory:
    return DataFactory(run_id)


@pytest.fixture
def api(run_id: str) -> Iterator[ApiClient]:
    client = ApiClient(settings.api_base_url, run_id)
    yield client
    client.cleanup()
    client.close()


@pytest.fixture(scope="session")
def sessions(
    browser: Browser, browser_context_args: dict[str, Any], worker_id: str
) -> Iterator[AccountSessions]:
    account_sessions = AccountSessions(browser, browser_context_args, worker_id)
    yield account_sessions
    account_sessions.remove_saved_sessions()


@pytest.fixture
def page_as(sessions: AccountSessions, request: pytest.FixtureRequest) -> Iterator[Callable[[Account], Page]]:
    """Opens a page as an account; skips the test if the account has no credentials (fails in CI)."""
    opened_contexts: list[BrowserContext] = []
    recording = recording_folder_for(RECORDINGS_ROOT, request.node.nodeid) if settings.qa_record else None

    def open_page(account: Account) -> Page:
        context = _context_or_skip(sessions, account, recording)
        opened_contexts.append(context)
        return context.new_page()

    yield open_page
    for context in opened_contexts:
        finish_recording(context, recording)
        context.close()


@pytest.fixture
def context(
    browser: Browser, browser_context_args: dict[str, Any], request: pytest.FixtureRequest
) -> Iterator[BrowserContext]:
    """The plain-browser context (login-screen tests); recorded and captured like `page_as`."""
    recording = recording_folder_for(RECORDINGS_ROOT, request.node.nodeid) if settings.qa_record else None
    new_context = browser.new_context(**with_recording(browser_context_args, recording))
    instrument_context(new_context, recording)
    yield new_context
    finish_recording(new_context, recording)
    new_context.close()


def _context_or_skip(sessions: AccountSessions, account: Account, recording: Path | None) -> BrowserContext:
    try:
        return sessions.context_for(account, recording)
    except MissingCredentialsError as error:
        report_missing_credentials(error)
