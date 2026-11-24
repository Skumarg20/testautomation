"""The `permanent` gate: tests that leave an irreversible change on QA run only with --allow-permanent."""

from pathlib import Path

import pytest

pytest_plugins = ["pytester"]
pytestmark = pytest.mark.framework

E2E_DIR = Path(__file__).resolve().parents[2]
PERMANENT_TEST = """
import pytest

@pytest.mark.permanent("a new online store")
def test_creates_a_store():
    pass
"""


@pytest.fixture
def project(pytester: pytest.Pytester, monkeypatch: pytest.MonkeyPatch) -> pytest.Pytester:
    monkeypatch.setenv("PYTHONPATH", str(E2E_DIR))  # the subprocess imports plugins.permanent_gate from here
    pytester.makepyfile(test_sample=PERMANENT_TEST)
    return pytester


def run(project: pytest.Pytester, *args: str) -> pytest.RunResult:
    gate = ("-p", "plugins.permanent_gate", "-p", "no:cacheprovider", "-rs")
    return project.runpytest_subprocess(*gate, *args)


def test_a_permanent_test_is_skipped_by_default(project: pytest.Pytester) -> None:
    result = run(project)

    result.assert_outcomes(skipped=1)
    result.stdout.fnmatch_lines(["*leaves a new online store on QA; run with --allow-permanent*"])


def test_allow_permanent_runs_it(project: pytest.Pytester) -> None:
    run(project, "--allow-permanent").assert_outcomes(passed=1)
