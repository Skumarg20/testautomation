"""Logged-in browser sessions: each account logs in once per xdist worker and is reused.

The app keeps its tokens in sessionStorage, which Playwright's storage_state does not save,
so the sessionStorage of the logged-in app page is saved and restored separately.
"""

import json
import os
import re
from pathlib import Path
from typing import Any, NoReturn

import pytest
from playwright.sync_api import Browser, BrowserContext

from config.settings import STUDIO_DEFAULT_COMPANY, Account, Credentials, settings, worker_index
from fixtures import console_capture, steps, studio_guard
from fixtures.recording import OVERLAY_SCRIPT
from pages.dashboard_page import DashboardPage
from pages.login_page import LoginPage

AUTH_DIRECTORY = Path(".auth")
PER_TAB_LOCAL_STORAGE_KEYS = frozenset({"app-tab-lock"})
SAVED_SESSION_STORAGE = "() => ({ ...sessionStorage })"
RESTORED_MARKER = "__qa_session_restored"
# Init scripts run on every navigation: restore once per tab, so a logout or a token the app refreshes
# afterwards is not overwritten with the login-time snapshot on the next reload. The once-per-tab flag
# lives in window.name, which survives reloads and same-origin navigation and which a logout's
# sessionStorage.clear() does not touch. The sessionStorage copy covers a tab the app opens itself:
# it inherits the opener's sessionStorage (marker included) but not its window.name.
RESTORE_SESSION_STORAGE = """
([origin, entries, marker]) => {
    if (window.location.origin !== origin) return;
    if (window.name.split(" ").includes(marker)) return;
    if (window.sessionStorage.getItem(marker) !== null) return;
    for (const [key, value] of Object.entries(entries)) window.sessionStorage.setItem(key, value);
    window.sessionStorage.setItem(marker, "1");
    window.name = window.name ? `${window.name} ${marker}` : marker;
}
"""


def recording_folder_for(root: Path, test_id: str) -> Path:
    """One folder per test under `root`, named so it is safe on any file system."""
    return root / re.sub(r"[^A-Za-z0-9._-]+", "-", test_id).strip("-")


def with_recording(options: dict[str, Any], folder: Path | None) -> dict[str, Any]:
    """Context options that also record a video into `folder`; unchanged when there is no folder."""
    return options if folder is None else {**options, "record_video_dir": str(folder)}


def auth_file_stem(worker_id: str, account: Account, process_id: int) -> str:
    """Two pytest processes both have a gw0, so the process id keeps their saved sessions apart."""
    return f"{process_id}-{worker_id}-{account}"


class MissingCredentialsError(Exception):
    def __init__(self, account: Account) -> None:
        super().__init__(f'No credentials for account "{account}" (set QA_{account.upper()}_USER/PASS)')


def report_missing_credentials(error: MissingCredentialsError) -> NoReturn:
    """A skip locally; a failure where credentials are required (CI), so an empty secret is never green."""
    if settings.qa_require_credentials:
        pytest.fail(f"{error} and QA_REQUIRE_CREDENTIALS is set")
    pytest.skip(str(error))


def instrument_context(context: BrowserContext, recording_folder: Path | None) -> None:
    """Recording overlay, console steps, console capture and (Test Studio mode) the QA guard: the same for every
    context a test opens."""
    studio_guard.arm(context)
    if recording_folder is not None:
        context.add_init_script(script=OVERLAY_SCRIPT)
    if steps.enabled():
        steps.attach_context(context)
    if console_capture.enabled():
        console_capture.attach_context(context)


class AccountSessions:
    def __init__(self, browser: Browser, context_options: dict[str, Any], worker_id: str) -> None:
        self._browser = browser
        self._context_options = context_options
        self._worker_id = worker_id
        self._logged_in: set[Account] = set()
        self._written: list[Path] = []

    def context_for(self, account: Account, recording_folder: Path | None = None) -> BrowserContext:
        if account not in self._logged_in:
            self._log_in(account)
            self._logged_in.add(account)
        return self._restored_context(account, recording_folder)

    def remove_saved_sessions(self) -> None:
        """The saved files hold live tokens under per-process names; nothing reuses them after the run."""
        for path in self._written:
            path.unlink(missing_ok=True)
        self._written.clear()

    def _log_in(self, account: Account) -> None:
        credentials = self._credentials_or_raise(account)
        context = self._blank_context()
        studio_guard.arm(context)
        try:
            page = context.new_page()
            self._sign_in(page, credentials)
            self._save_session(account, context, page)
        finally:
            context.close()

    def _sign_in(self, page: Any, credentials: Credentials) -> None:
        login_page = LoginPage(page)
        login_page.open()
        login_page.sign_in(*credentials)
        if STUDIO_DEFAULT_COMPANY:          # Test Studio mode: the saved session starts in a QA test company
            _open_studio_company(page)
        DashboardPage(page).expect_loaded()
        page.goto(settings.margbooks_qa_url, wait_until="load")

    def _save_session(self, account: Account, context: BrowserContext, page: Any) -> None:
        AUTH_DIRECTORY.mkdir(exist_ok=True)
        self._written += [self._storage_state_file(account), self._session_storage_file(account)]
        context.storage_state(path=str(self._storage_state_file(account)))
        _drop_per_tab_keys(self._storage_state_file(account))
        entries = page.evaluate(SAVED_SESSION_STORAGE)
        self._session_storage_file(account).write_text(json.dumps(entries))

    def _restored_context(self, account: Account, recording_folder: Path | None) -> BrowserContext:
        context = self._blank_context(self._storage_state_file(account), recording_folder)
        entries = json.loads(self._session_storage_file(account).read_text())
        context.add_init_script(script=_restore_script(entries))
        instrument_context(context, recording_folder)
        return context

    def _blank_context(
        self, storage_state: Path | None = None, recording_folder: Path | None = None
    ) -> BrowserContext:
        options = with_recording(
            {**self._context_options, "base_url": settings.margbooks_qa_url}, recording_folder
        )
        return self._browser.new_context(
            **options,
            storage_state=str(storage_state) if storage_state else None,
        )

    def _storage_state_file(self, account: Account) -> Path:
        return AUTH_DIRECTORY / f"{self._auth_stem(account)}.json"

    def _session_storage_file(self, account: Account) -> Path:
        return AUTH_DIRECTORY / f"{self._auth_stem(account)}.session.json"

    def _auth_stem(self, account: Account) -> str:
        return auth_file_stem(self._worker_id, account, os.getpid())

    def _credentials_or_raise(self, account: Account) -> Credentials:
        credentials = settings.credentials(account, worker_index(self._worker_id))
        if credentials is None:
            raise MissingCredentialsError(account)
        return credentials


def _open_studio_company(page: Any) -> None:
    """An account with many companies lands on the Organisation List after signing in: pick the QA test company
    Test Studio runs in. One that lands on a dashboard is switched to it."""
    from pages.company_switch_page import CompanySwitchPage

    page.wait_for_url(re.compile(r"/(dashboard|user-company)"), timeout=150_000)
    switcher = CompanySwitchPage(page)
    if "/user-company" in page.url:
        switcher.switch_company(STUDIO_DEFAULT_COMPANY)
    else:
        switcher.ensure_company(STUDIO_DEFAULT_COMPANY)


def _restore_script(entries: dict[str, str]) -> str:
    return restore_script_for(_origin(settings.margbooks_qa_url), entries)


def restore_script_for(origin: str, entries: dict[str, str]) -> str:
    arguments = json.dumps([origin, entries, RESTORED_MARKER])
    return f"({RESTORE_SESSION_STORAGE})({arguments});"


def _origin(url: str) -> str:
    scheme, rest = url.split("://", 1)
    return f"{scheme}://{rest.split('/')[0]}"


def _drop_per_tab_keys(storage_state_file: Path) -> None:
    """The app's single-tab lock, restored in a new context, shows "open in another tab"."""
    state = json.loads(storage_state_file.read_text())
    for origin in state["origins"]:
        origin["localStorage"] = [
            entry for entry in origin["localStorage"] if entry["name"] not in PER_TAB_LOCAL_STORAGE_KEYS
        ]
    storage_state_file.write_text(json.dumps(state))
