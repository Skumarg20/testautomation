"""'Write as a script': the AI test is kept only when it passes the checks, else the skeleton is written."""
from pathlib import Path

import pytest

from ui_studio import e2e, script_writer, state


@pytest.fixture
def journey(tmp_path, monkeypatch):
    (tmp_path / "pages").mkdir()
    (tmp_path / "pages" / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / "pages" / "base_page.py").write_text(
        "class BasePage:\n    def __init__(self, page):\n        self.page = page\n    def goto(self, path):\n        pass\n",
        encoding="utf-8")
    (tmp_path / "pages" / "bill.py").write_text(
        "from pages.base_page import BasePage\n\nclass Bill(BasePage):\n"
        "    def open_new(self) -> None:\n        '''Open a new bill.'''\n"
        "    def expect_abha_red(self) -> None:\n        '''The Abha button is red.'''\n", encoding="utf-8")
    folder = tmp_path / "tests" / "journeys" / "abha"
    folder.mkdir(parents=True)
    (folder / "conftest.py").write_text(
        "import pytest\nfrom pages.bill import Bill\n\n@pytest.fixture\ndef bill(page) -> Bill:\n"
        "    '''A sale bill page object.'''\n    return Bill(page)\n", encoding="utf-8")
    monkeypatch.setattr(e2e, "E2E", tmp_path)
    monkeypatch.setattr(e2e, "PY", tmp_path / "no-python")          # no scripts environment: static checks only
    return folder


GOOD = '''"""Abha button. Scenario: abha.md AB-01. Test case: TC_ABHA_001. Written by Test Studio AI."""
import pytest
from pages.bill import Bill

pytestmark = [pytest.mark.p2, pytest.mark.journey("abha-health-flows")]


def test_red(bill: Bill) -> None:
    """AB-01."""
    bill.open_new()
    bill.expect_abha_red()
'''


def test_reads_fixtures_and_page_methods_with_their_base(journey):
    assert "bill(page) -> Bill" in script_writer.fixtures_of(journey)["bill"]
    mod, methods = script_writer.page_classes(journey)["Bill"]
    assert mod == "pages.bill" and {"open_new", "expect_abha_red", "goto", "page"} <= set(methods)


def test_checks_catch_invented_methods_fixtures_and_weak_asserts(journey):
    fx, cl = script_writer.fixtures_of(journey), script_writer.page_classes(journey)
    assert script_writer.check_code(GOOD, fx, cl) == []
    bad = GOOD.replace("bill.expect_abha_red()", "bill.click_abha()")
    assert any("no method or attribute 'click_abha'" in p for p in script_writer.check_code(bad, fx, cl))
    assert any("not a fixture" in p for p in script_writer.check_code(GOOD.replace("(bill: Bill)", "(bill: Bill, mystery)"), fx, cl))
    weak = GOOD.replace("    bill.expect_abha_red()\n", "    assert bill.page.inner_text('x').upper() == 'A'\n")
    assert any(".upper" in p for p in script_writer.check_code(weak, fx, cl))
    assert any("checks nothing" in p for p in script_writer.check_code(GOOD.replace("    bill.expect_abha_red()\n", ""), fx, cl))
    assert any("journey" in p for p in script_writer.check_code(GOOD.replace('pytest.mark.journey("abha-health-flows")', ""), fx, cl))
    assert any("syntax" in p.lower() for p in script_writer.check_code("def (", fx, cl))


class Case:
    id, title, priority, expected, preconditions, steps = "TC_ABHA_001", "Abha button", "p2", ["red"], [], []


def test_keeps_a_good_answer_and_retries_a_bad_one(journey, monkeypatch):
    answers = [{"code": GOOD.replace("bill.expect_abha_red()", "bill.nope()"), "unsure": []},
               {"code": GOOD, "unsure": ["label text"]}]
    monkeypatch.setattr(state, "ai_json", lambda *a, **k: (answers.pop(0), 100, False))
    path = journey / "test_studio_tc_abha_001.py"
    got = script_writer.write(Case(), journey, path, "test_red", "", "AB-01", "abha.md")
    assert got["ok"] and got["attempts"] == 2 and got["notes"] == ["label text"]
    assert path.read_text(encoding="utf-8").startswith('"""Abha button.')


def test_gives_up_after_three_bad_answers_and_writes_nothing(journey, monkeypatch):
    monkeypatch.setattr(state, "ai_json", lambda *a, **k: ({"code": "x = 1\n"}, 10, False))
    path = journey / "test_studio_tc_abha_001.py"
    got = script_writer.write(Case(), journey, path, "test_red", "", "AB-01", "abha.md")
    assert not got["ok"] and "did not pass" in got["notes"][0] and not Path(path).exists()


def test_script_failures_are_explained_in_plain_words():
    login = ['E     - waiting for locator("input#password") to be visible']
    assert "Settings > App under test" in e2e.explain(login)
    assert "ABHA precondition" in e2e.explain(["SKIPPED [1] ... ABHA precondition: QA Pharma has business type 13"])
    assert e2e.explain(["1 passed in 3.2s"]) == ""


def test_write_as_script_runs_in_the_background_with_stages(monkeypatch, tmp_path):
    import time as _t
    monkeypatch.setattr(state, "DB", tmp_path / "studio.db")          # the activity log must not touch the real one
    from ui import store
    monkeypatch.setattr(store, "get", lambda cid: type("C", (), {"id": "TC_X"})())
    monkeypatch.setattr(e2e, "scripts_for_case", lambda cid: [])

    def slow(case_id, progress=None):
        progress("AI is writing the test (try 1 of 3)", 2)
        _t.sleep(0.3)
        return {"node": "tests/x.py::test_x", "created": True, "ai": True, "notes": []}

    monkeypatch.setattr(e2e, "new_script", slow)
    first = e2e.new_script_start("TC_X")
    assert e2e.new_script_start("TC_X") == {"job": first["job"]}        # a second click joins the same job
    _t.sleep(0.1)
    s = e2e.new_script_status(first["job"])
    assert s["state"] == "running" and s["step"] == 2 and "try 1" in s["stage"]
    _t.sleep(0.5)
    assert e2e.new_script_status(first["job"])["result"]["node"] == "tests/x.py::test_x"


def test_a_case_with_a_script_opens_it_without_writing(monkeypatch):
    from ui import store
    monkeypatch.setattr(store, "get", lambda cid: type("C", (), {"id": "TC_Y"})())
    monkeypatch.setattr(e2e, "scripts_for_case", lambda cid: [{"node": "tests/y.py::test_y"}])
    r = e2e.new_script_start("TC_Y")
    assert r["state"] == "done" and r["result"] == {"node": "tests/y.py::test_y", "created": False}
