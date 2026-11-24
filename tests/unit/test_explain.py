"""Failures in simple words for manual QAs: the errors this project really meets."""
import pytest

from ui_studio.explain import explain

FIXED_BALANCE = ('Step 6 failed: Before: supplier balance 19,960.00 Cr (purchase QAA1)\nNot visible: '
                 'xpath=//div[@col-id="0"][normalize-space(translate(.," "," "))="19,960.00 Cr"]')


@pytest.mark.parametrize(("err", "result", "words", "side"), [
    (FIXED_BALANCE, "Fail", ["Step 6", "19,960.00 Cr", "change every time"], "test"),
    ("Step 3 failed: x\nLocator.wait_for: Target page, context or browser has been closed", "Fail",
     ["closed in the middle", "same login"], "login"),
    ("Step 2 failed: fill\nRefused to run 'fill': the open company is '(none)', not a QA test company", "Fail",
     ["stopped before it could save", "QA test company"], "test"),
    ("AssertionError: Locator expected to have text '₹4739.250 from ₹0.000'\nActual value: ₹4739.25 from ₹0.00 ",
     "Fail", ["showed “₹4739.25 from ₹0.00”", "expected “₹4739.250 from ₹0.000”"], "app"),
    ("Step 61 failed: wait_text  Bill Adjustment\nno visible text 'Bill Adjustment' after 60 s", "Fail",
     ["did not show “Bill Adjustment”"], "test"),
    ("Not run: this test saves or changes data and “Allow tests that create or change data” is off.", "Skip",
     ["not run", "saving is switched off"], "setup"),
    ('Locator.wait_for: Timeout 30000ms exceeded.\n - waiting for locator("input#password") to be visible', "Fail",
     ["could not log in"], "login"),
    ("[studio-guard] BLOCKED POST https://x/CallGrpcSaveSaleBill: a write in company 9", "Fail",
     ["stopped before it could save"], "test"),
    ("Step 4 failed: click\nElement is not enabled - disabled", "Fail", ["greyed out", "setting"], "setup"),
    ("Step 5 failed: click\n<div class=modal> intercepts pointer events", "Fail", ["popup"], "test"),
])
def test_known_failures_read_in_simple_words(err, result, words, side):
    x = explain(err, "", result)
    text = " ".join((x["what"], x["why"], x["next"]))
    assert all(w.lower() in text.lower() for w in words), text
    assert x["side"] == side and x["side_text"]
    assert "xpath" not in x["what"] and "Locator" not in x["what"]          # no technical words in the headline


def test_unknown_error_is_still_explained_and_a_pass_has_nothing():
    x = explain("KeyError: 'x'", "Click Save")
    assert x["what"].startswith("A step failed") and "KeyError" in x["why"] and "Explain" in x["next"]
    assert explain("", "", "Pass") == {}


def test_run_detail_and_bug_pack_carry_the_summary(monkeypatch, tmp_path):
    from ui_studio import tests
    row = {"id": "R-1", "test_id": "TC_X", "name": "n", "module": "m", "author": "a", "at": "", "passed": 5,
           "total": 7, "result": "Fail", "err": FIXED_BALANCE, "fail_at": 5, "ai_fixes": 0, "run_by": "",
           "steps": '[{"text": "s", "status": "ok"}]', "dir": str(tmp_path)}
    monkeypatch.setattr(tests, "_run_row", lambda rid: row)
    d = tests.run_detail("R-1")
    assert "19,960.00 Cr" in d["explain"]["what"]
    assert "Why:" in tests.report_html("R-1") and "Technical message" in tests.report_html("R-1")


def test_summary_is_stored_with_the_run_and_ai_one_wins(tmp_path, monkeypatch):
    import json
    from ui_studio import state, tests
    monkeypatch.setattr(state, "DB", tmp_path / "studio.db")
    with state.db() as c:
        c.execute("INSERT INTO runs(id,test_id,name,module,author,at,passed,total,result,err,fail_at,steps,dir,ai_fixes,"
                  "ts,run_by) VALUES('R-9','TC_X','n','m','a','',0,1,'Fail',?,0,'[{\"text\":\"s\",\"status\":\"bad\"}]',"
                  "?,0,0,'')", (FIXED_BALANCE, str(tmp_path)))
    first = tests.run_detail("R-9")["explain"]                        # an old run: made now and stored
    with state.db() as c:
        assert json.loads(c.execute("SELECT explain FROM runs WHERE id='R-9'").fetchone()[0])["what"] == first["what"]
    tests.store_ai_explain("R-9", {"what": "AI words", "why": "w", "next": "n", "side": "app", "side_text": "x"})
    again = tests.run_detail("R-9")["explain"]
    assert again["what"] == "AI words" and again["ai"] is True
