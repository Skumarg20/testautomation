"""Detailed manual steps (config/case_details.json) shown for draft cases, and the merge checks that keep customer data
and passwords out of them."""
import json

from tools import merge_case_details as m
from ui_studio import tests


class Case:
    def __init__(self, cid, steps=None, pre=None, expected=None):
        self.id, self.steps, self.preconditions, self.expected = cid, steps or [], pre or [], expected or []
        self.title = "Title only"


def test_written_detail_replaces_the_title_only_steps(tmp_path, monkeypatch):
    f = tmp_path / "case_details.json"
    f.write_text(json.dumps({"TC_X": {"preconditions": ["QA Chemist"], "steps": ["Open Sale > Bill", "Press F10"],
                                      "expected": [], "refs": ["a.ts:1"], "checked_live": False}}), encoding="utf-8")
    monkeypatch.setattr(tests, "CASE_DETAILS", f)
    tests._details_cache.update(sig=None, data={})
    assert tests.text_test(Case("TC_X")) == ["Open Sale > Bill", "Press F10"]
    assert tests.text_test(Case("TC_Y")) == ["Title only"]                       # no detail: as before
    auto = Case("TC_X", steps=[{"action": "click", "note": "Save"}])
    assert tests.text_test(auto) == ["Save"]                                       # automated steps win
    d = tests._detail_of(Case("TC_X", expected=["Bill saved"]))
    assert d["preconditions"] == ["QA Chemist"] and d["expected"] == ["Bill saved"] and d["refs"] == ["a.ts:1"]


def test_merge_checks_keep_out_passwords_and_customer_contacts():
    ok = {"preconditions": [], "steps": ["Open Master > Ledger"], "expected": ["Ledger list opens"], "refs": []}
    assert m.check_entry("A", ok, ["Secret#123"]) == []
    assert m.check_entry("A", {**ok, "steps": []}, []) == ["no steps"]
    assert m.check_entry("A", {**ok, "steps": "x"}, [])[0].startswith("steps")
    assert any("password" in x for x in m.check_entry("A", {**ok, "refs": ["pw Secret#123"]}, ["Secret#123"]))
    assert any("e-mail" in x for x in m.check_entry("A", {**ok, "refs": ["raised by ram.kumar@gmail.com"]}, []))
    assert any("mobile" in x for x in m.check_entry("A", {**ok, "steps": ["Type 9812345678"]}, []))
    assert m.check_entry("A", {**ok, "steps": ["Type 9876543210 (a made-up test number)"]}, []) == []
    assert m.check_entry("A", {**ok, "steps": ["Scan 000003@0.35"]}, []) == []           # POS barcode@qty
    assert m.check_entry("A", {**ok, "steps": ["Type qa.no.account.1@margbooks-qa.invalid"]}, []) == []


def test_spec_table_links_each_function_to_its_own_scenario(tmp_path, monkeypatch):
    from ui_studio import e2e
    (tmp_path / "specs").mkdir()
    (tmp_path / "specs" / "abha-health-flows.md").write_text(
        "| Test | Scenario | Asserts |\n|---|---|---|\n"
        "| `test_red_button` | AB-01 | red |\n| `test_no_button` | AB-02 / MBC-2139 | none |\n", encoding="utf-8")
    f = tmp_path / "tests" / "journeys" / "abha" / "test_sale_bill_abha.py"
    f.parent.mkdir(parents=True)
    f.write_text('"""ABHA in the sale bill (AB-01, AB-02)."""\nimport pytest\n'
                 'pytestmark = [pytest.mark.journey("abha-health-flows")]\n\n'
                 'def test_red_button():\n    pass\n\ndef test_no_button():\n    pass\n', encoding="utf-8")
    monkeypatch.setattr(e2e, "E2E", tmp_path)
    got = {s["func"]: s["ids"] for s in e2e._read_file(f, e2e._spec_ids())}
    assert got == {"test_red_button": ["AB-01"], "test_no_button": ["AB-02"]}
    assert {s["func"]: s["ids"] for s in e2e._read_file(f, {})} == {"test_red_button": [], "test_no_button": []}
