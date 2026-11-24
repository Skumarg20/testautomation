"""Module report: tests grouped by module, with the reason a test failed or was skipped and its recordings."""

from html import escape
from pathlib import Path
from typing import Any

import pytest

from scripts.module_report import build_modules, render_html

pytestmark = pytest.mark.framework

SKIP_REASON = 'No credentials for account "grocery" (set QA_GROCERY_USER/PASS)'


def _entry(nodeid: str, outcome: str, **phases: Any) -> dict[str, Any]:
    return {"nodeid": nodeid, "outcome": outcome, "call": {"outcome": outcome, "duration": 2.5}, **phases}


FAILED = _entry(
    "tests/journeys/accounting/test_contra.py::test_contra_voucher[chromium-CON-001]",
    "failed",
    call={"outcome": "failed", "duration": 30.0, "crash": {"message": "Locator expected to be visible"}},
)
SKIPPED = _entry(
    "tests/journeys/auth/test_login.py::test_every_account[chromium-grocery]",
    "skipped",
    setup={"outcome": "skipped", "longrepr": f"('conftest.py', 82, 'Skipped: {SKIP_REASON}')"},
)
PASSED = _entry("tests/journeys/auth/test_login.py::test_wrong_password[chromium]", "passed")


def test_tests_are_grouped_by_the_folder_under_journeys() -> None:
    modules = build_modules([FAILED, SKIPPED, PASSED], Path("results/recordings"))
    assert [module.name for module in modules] == ["accounting", "auth"]
    assert [len(module.tests) for module in modules] == [1, 2]


def test_a_failed_test_carries_its_error_and_a_skipped_one_its_reason() -> None:
    by_name = {t.nodeid: t for m in build_modules([FAILED, SKIPPED], Path("r")) for t in m.tests}
    assert by_name[FAILED["nodeid"]].reason == "Locator expected to be visible"
    assert by_name[SKIPPED["nodeid"]].reason == SKIP_REASON


def test_recording_files_are_listed_when_the_folder_exists(tmp_path: Path) -> None:
    folder = tmp_path / "tests-journeys-auth-test_login.py-test_wrong_password-chromium"
    folder.mkdir()
    (folder / "page@1.webm").write_bytes(b"v")
    (folder / "final.png").write_bytes(b"p")
    test = build_modules([PASSED], tmp_path)[0].tests[0]
    assert sorted(path.name for path in test.recordings) == ["final.png", "page@1.webm"]


def test_html_shows_each_module_test_status_reason_and_a_run_command() -> None:
    html = render_html(build_modules([FAILED, SKIPPED, PASSED], Path("r")))
    for expected in (
        escape(SKIP_REASON),
        "accounting",
        "Locator expected to be visible",
        "pytest",
        "test_contra_voucher",
    ):
        assert expected in html
