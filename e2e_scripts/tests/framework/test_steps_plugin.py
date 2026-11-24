"""The console steps plugin (F04 5.6) on a throw-away suite. No MargBooks app needed.

Each case writes a tiny test file, runs pytest in a subprocess with the plugin switched on, and reads the
pytest-json-report metadata the console ingester will read.
"""

import json
import textwrap
from pathlib import Path
from typing import Any

import pytest

from fixtures import steps

pytest_plugins = ["pytester"]
pytestmark = pytest.mark.framework

E2E_DIR = Path(__file__).resolve().parents[2]
REPORT = "steps-report.json"


@pytest.fixture(autouse=True)
def _console_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PYTHONPATH", str(E2E_DIR))
    monkeypatch.setenv(steps.ENV_ENABLED, "1")


def run_suite(pytester: pytest.Pytester, source: str, *extra: str) -> dict[str, Any]:
    """Run `source` as a test module and return the first test entry of the JSON report."""
    pytester.makepyfile(test_sample=textwrap.dedent(source))
    pytester.runpytest_subprocess(
        "-p", "fixtures.steps", "--json-report", f"--json-report-file={REPORT}", *extra
    )
    report = json.loads((pytester.path / REPORT).read_text())
    entry: dict[str, Any] = report["tests"][0]
    return entry


def metadata_of(entry: dict[str, Any]) -> dict[str, Any]:
    metadata: dict[str, Any] = entry["metadata"]
    return metadata


def test_steps_plugin_records_keyword_text_code_duration(pytester: pytest.Pytester) -> None:
    entry = run_suite(
        pytester,
        """
        import time
        from fixtures.steps import given, then, when

        def test_flow():
            with given("a session stored for the garments account"):
                account = "garments"
            with when("the dashboard opens"):
                time.sleep(0.05)
            with then("the header shows the company"):
                assert account
        """,
    )

    recorded = metadata_of(entry)["steps"]

    assert [(s["seq"], s["keyword"], s["text"], s["outcome"]) for s in recorded] == [
        (1, "Given", "a session stored for the garments account", "passed"),
        (2, "When", "the dashboard opens", "passed"),
        (3, "Then", "the header shows the company", "passed"),
    ]
    assert recorded[0]["code"] == 'account = "garments"'
    assert recorded[1]["code"] == "time.sleep(0.05)"
    assert recorded[1]["duration_ms"] >= 50


def test_steps_plugin_marks_failed_step_and_reraises(pytester: pytest.Pytester) -> None:
    entry = run_suite(
        pytester,
        """
        from fixtures.steps import and_, given, step, then

        def test_flow():
            step.plan([("Given", "a"), ("Then", "b"), ("And", "c")])
            with given("a"):
                pass
            with then("b"):
                total = 1
                assert total == 2, "expected value differs"
            with and_("c"):
                pass
        """,
    )

    recorded = metadata_of(entry)["steps"]

    assert entry["outcome"] == "failed"
    assert "expected value differs" in entry["call"]["crash"]["message"]
    assert [(s["outcome"]) for s in recorded] == ["passed", "failed", "not_run"]
    assert recorded[1]["code"] == 'assert total == 2, "expected value differs"'
    assert recorded[2]["duration_ms"] == 0


def test_steps_plugin_masks_password_arguments(pytester: pytest.Pytester) -> None:
    entry = run_suite(
        pytester,
        """
        from fixtures.steps import given

        def sign_in(user, password):
            return user

        def test_flow():
            with given("the user signs in", user="amit", password="s3cret-value", otp="123456"):
                sign_in("amit", password="s3cret-value")
        """,
    )

    code = metadata_of(entry)["steps"][0]["code"]

    assert "s3cret-value" not in json.dumps(entry["metadata"])
    assert "123456" not in code
    assert "password=***" in code
    assert "user='amit'" in code


def test_run_without_json_report_does_not_break_steps_plugin(pytester: pytest.Pytester) -> None:
    pytester.makepyfile(
        test_sample="""
        from fixtures.steps import given

        def test_flow():
            with given("anything"):
                pass
        """
    )

    result = pytester.runpytest_subprocess("-p", "fixtures.steps", "-p", "no:jsonreport")

    result.assert_outcomes(passed=1)


def test_plugin_is_inert_when_the_console_switch_is_off(
    pytester: pytest.Pytester, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv(steps.ENV_ENABLED)
    entry = run_suite(
        pytester,
        """
        from fixtures.steps import given

        def test_flow():
            with given("anything"):
                pass
        """,
    )

    assert "metadata" not in entry
    assert entry["outcome"] == "passed"


def test_test_without_steps_reports_empty_steps(pytester: pytest.Pytester) -> None:
    entry = run_suite(pytester, "def test_plain():\n    assert True\n")

    assert metadata_of(entry)["steps"] == []
    assert metadata_of(entry)["network"] == []


def test_setup_failure_is_flagged(pytester: pytest.Pytester) -> None:
    entry = run_suite(
        pytester,
        """
        import pytest

        @pytest.fixture
        def broken():
            raise RuntimeError("login timed out")

        def test_needs_broken(broken):
            pass
        """,
    )

    assert entry["outcome"] == "error"
    assert metadata_of(entry)["setup_error"] is True


def test_axe_violation_mapped_to_finding_fields() -> None:
    violation = {
        "id": "button-name",
        "impact": "critical",
        "help": "Buttons must have discernible text",
        "nodes": [{"target": ["header", ["#shadow-host", ".company-switch"]]}, {"target": [".other"]}],
    }

    finding = steps.finding_from_violation(violation)

    assert finding == {
        "rule": "button-name",
        "impact": "critical",
        "target": "header >> #shadow-host >> .company-switch",
        "detail": "Buttons must have discernible text",
        "node_count": 2,
    }


def test_axe_violation_without_impact_is_minor() -> None:
    finding = steps.finding_from_violation({"id": "x", "impact": None, "help": "h", "nodes": []})

    assert finding["impact"] == "minor"
    assert finding["target"] == ""


BROWSER_SUITE = """
    import pytest
    from playwright.sync_api import expect, sync_playwright
    from fixtures import steps

    @pytest.fixture
    def page():
        with sync_playwright() as playwright:
            try:
                browser = playwright.chromium.launch()
            except Exception:
                try:
                    browser = playwright.chromium.launch(channel="chrome")
                except Exception:
                    pytest.skip("no browser available")
            context = browser.new_context()
            steps.attach_context(context)
            yield context.new_page()
            context.close()
            browser.close()

    def test_failing_page(page):
        page.route("**/*", lambda route: route.fulfill(status=200, body="{}", content_type="text/html"))
        page.goto("http://app.test/home?token=abc123")
        page.set_content("<header id='company'></header>")
        page.evaluate("fetch('http://app.test/api/company/switch?session=zzz9', {method: 'POST'})")
        page.wait_for_timeout(200)
        expect(page.locator("#company")).to_have_text("Demo Traders", timeout=500)
"""


@pytest.fixture
def browser_run(pytester: pytest.Pytester, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, dict[str, Any]]:
    monkeypatch.setenv(steps.ENV_NETWORK, "1")
    entry = run_suite(pytester, BROWSER_SUITE, "--output", "out")
    if entry["outcome"] == "skipped":
        pytest.skip("no browser available")
    return pytester.path / "out", entry


def test_failed_test_with_context_produces_trace_and_screenshot(
    browser_run: tuple[Path, dict[str, Any]],
) -> None:
    out, entry = browser_run

    kinds = {item["kind"]: item["file"] for item in metadata_of(entry)["artifacts"]}

    assert entry["outcome"] == "failed"
    folder = out / metadata_of(entry)["artifact_slug"]
    assert (folder / kinds["trace"]).stat().st_size > 0
    assert (folder / kinds["screenshot"]).stat().st_size > 0


def test_network_rows_keep_only_method_path_status_and_duration(
    browser_run: tuple[Path, dict[str, Any]],
) -> None:
    _, entry = browser_run

    rows = metadata_of(entry)["network"]

    assert {key: rows[-1][key] for key in ("method", "path", "status")} == {
        "method": "POST",
        "path": "/api/company/switch",
        "status": 200,
    }
    assert all(set(row) == {"method", "path", "status", "duration_ms"} for row in rows)
    assert "abc123" not in json.dumps(rows)
    assert "zzz9" not in json.dumps(rows)


def test_failed_expect_records_element_state(browser_run: tuple[Path, dict[str, Any]]) -> None:
    _, entry = browser_run

    state = metadata_of(entry)["element_state"]

    assert state["locator"] == "#company"
    assert state["text"] == ""
