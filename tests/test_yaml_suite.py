"""
Ye ek hi file poore testcases/*.yaml suite ko chalati hai.
Naya test add karne ke liye Python likhne ki zaroorat nahi -- bas YAML me case add karo.

    pytest --tags smoke
    pytest --case TC_SALE_001
    pytest -m "sales and p1"
"""
import pytest

from framework.case_loader import load_all
from framework.step_runner import StepRunner, RunContext

CASES = load_all()


def _id(c):
    return f"{c.id}::{c.title[:45]}"


@pytest.mark.parametrize("case", CASES, ids=[_id(c) for c in CASES])
def test_case(case, app, request, pytestconfig):
    only = pytestconfig.getoption("--case")
    if only and case.id != only:
        pytest.skip(f"--case {only} filter")

    tags = [t for t in pytestconfig.getoption("--tags").split(",") if t]
    if tags and not set(tags) & set(case.marks):
        pytest.skip(f"--tags {tags} filter")

    # A draft (e.g. an imported scenario) has no runnable steps yet. Without this it
    # would run zero steps and show as PASSED. The UI runner skips drafts the same way.
    if case.draft or not case.steps:
        pytest.skip("DRAFT -- no steps yet (record or write them in Test Studio)")

    for m in case.marks:
        request.node.add_marker(getattr(pytest.mark, m))
    request.node.case_id = case.id

    ctx = RunContext()
    runner = StepRunner(app, ctx)
    try:
        runner.run(case.steps)
    finally:
        print(f"\n--- {case.id} :: {case.title}")
        print("\n".join(ctx.log))
