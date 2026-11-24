"""framework.test_data: shared test data that a test used up is put back and the test runs again."""
import pytest

from framework import test_data as td
from framework.step_runner import RunContext, StepRunner
from framework.test_env import EnvironmentNotReady


def test_registry_lists_the_garment_variants():
    e = td.entry_for("QA Garment", "11110001")
    assert e and e["kind"] == "variant" and e["item"] == "QA_Shirt" and e["min"] <= e["target"]
    assert td.entry_for("QA Garment", "99999999") is None
    assert td.entry_for("QA Chemist", "11110001") is None


def test_balance_text_is_read_with_its_sign():
    assert td._num("- 6.00") == -6.0
    assert td._num("1,020.50") == 1020.5
    assert td._num("") is None


class _P:
    page = None


def _runner(monkeypatch, repair_ok, fail_times=1):
    r = StepRunner.__new__(StepRunner)
    r.p, r.ctx = _P(), RunContext()
    calls = {"n": 0, "restart": 0}

    def run_steps(steps):
        calls["n"] += 1
        if calls["n"] <= fail_times:
            err = EnvironmentNotReady("data gone")
            err.missing = ["11110001"]
            raise err
    monkeypatch.setattr(r, "_run_steps", run_steps)
    monkeypatch.setattr(td, "repair", lambda bp, names, log=None: repair_ok)
    r.on_restart = lambda: calls.__setitem__("restart", calls["restart"] + 1)
    return r, calls


def test_missing_data_is_put_back_and_the_test_runs_again(monkeypatch):
    r, calls = _runner(monkeypatch, repair_ok=True)
    r.run([{"action": "sleep", "value": 0}])
    assert calls == {"n": 2, "restart": 1}


def test_no_recipe_keeps_the_test_blocked(monkeypatch):
    r, calls = _runner(monkeypatch, repair_ok=False)
    with pytest.raises(EnvironmentNotReady):
        r.run([{"action": "sleep", "value": 0}])
    assert calls["n"] == 1


def test_it_is_retried_only_once(monkeypatch):
    r, calls = _runner(monkeypatch, repair_ok=True, fail_times=5)
    with pytest.raises(EnvironmentNotReady):
        r.run([{"action": "sleep", "value": 0}])
    assert calls["n"] == 2


def test_any_shared_item_of_a_plain_trade_has_a_recipe_but_batch_and_empty_items_do_not():
    e = td.entry_for("QA Billing General", "QA_Item_GST18")
    assert e and e["kind"] == "item" and e["min"] <= e["target"]
    assert td.entry_for("QA Chemist", "QA_Item_GST12") is None            # batches: never auto-filled
    assert td.entry_for("QA GST Pharma Distribution", "QA_Item_GST5") is None
    assert td.entry_for("QA Billing General", "QA_Item_NoStock") is None   # the test needs it empty
    assert td.entry_for("QA Billing General", "QA_Party_Debtor") is None


class _Page:
    def __init__(self, text):
        self.text = text

    def evaluate(self, js, *a):
        return self.text


def _sr(case_text, page_text, steps):
    r = StepRunner.__new__(StepRunner)
    r.p = type("P", (), {"page": _Page(page_text)})()
    r._case_text, r._steps_seen = case_text, steps
    return r


def test_a_stock_message_names_the_items_the_test_used():
    r = _sr("sale of qa_item_gst12", "Negative Stock Not Allowed", [{"action": "fill", "value": "QA_Item_GST12"}])
    assert r._stock_ran_out() == "QA_Item_GST12"


def test_a_test_about_stock_shortage_is_never_restocked():
    r = _sr("qa_item_nostock shows negative stock message", "Negative Stock Not Allowed",
            [{"action": "fill", "value": "QA_Item_NoStock"}])
    assert r._stock_ran_out() is None


def test_no_stock_message_no_restock():
    r = _sr("sale", "Saved Successfully", [{"action": "fill", "value": "QA_Item_GST12"}])
    assert r._stock_ran_out() is None


def test_fixed_document_numbers_are_recognised():
    f = StepRunner._FIXED_DOC
    assert f.search('xpath=//div[@col-id="entryNo" and normalize-space()="0000001"]')
    assert f.search("CN00002") and f.search("ST000006")
    assert not f.search("{ctx.bill}") and not f.search("Rate 1000.00") and not f.search("QA_Item_GST12")


# ---- fixed figures replaced by read value + expected change (23-Nov-2026) ----

def test_assert_same_side_takes_the_expected_change():
    from framework.step_runner import _side_number
    assert _side_number("123.00 - 4") == 119.0
    assert _side_number("-5.00 + 2") == -3.0
    assert _side_number("1,020.50 Dr") == 1020.5
    assert _side_number("119.00") == 119.0


def test_fixed_stock_pairs_become_read_plus_delta():
    from tools.rewrite_fixed_stock import rewrite
    cell = 'xpath=//div[@role="row"][.//div[@col-id="Product" and normalize-space()="QA_Item_GST12"]]//div[@col-id="Opening"'
    case = {"id": "X", "steps": [
        {"action": "assert_visible", "target": cell + ' and number(normalize-space())=100]', "note": "stock 100"},
        {"action": "press", "value": "F10"},
        {"action": "assert_visible", "target": cell + ' and number(normalize-space())=98]', "note": "stock 98"},
    ]}
    new, n = rewrite(case)
    assert n == 2
    acts = [s["action"] for s in new["steps"]]
    assert acts == ["read_value", "press", "read_value", "assert_same"]
    assert new["steps"][0]["target"] == cell + "]"
    assert new["steps"][3]["value"] == "{ctx.stock_0_0} - 2 = {ctx.stock_0_1}"


def test_a_lone_stock_figure_and_barcodes_are_left_alone():
    from tools.rewrite_fixed_stock import rewrite
    lone = {"id": "Y", "steps": [{"action": "assert_visible", "note": "shows stock 0.00",
            "target": 'xpath=//div[@col-id="Opening"][normalize-space()="0.00"]'}]}
    assert rewrite(lone)[1] == 0
    bar = 'xpath=//ngb-modal-window//div[@role="row"][.//div[@col-id="balanceQty"]]//div[@col-id="BarCode" and contains(.,"1111000{}")]'
    two = {"id": "Z", "steps": [{"action": "assert_visible", "target": bar.format(1), "note": "stock"},
                                {"action": "assert_visible", "target": bar.format(5), "note": "stock"}]}
    assert rewrite(two)[1] == 0


def test_modal_row_literal_is_found_for_scrolling():
    from framework.step_runner import StepRunner
    t = 'xpath=//ngb-modal-window//div[@role="row"]//*[normalize-space(text())="A23134216"]'
    assert StepRunner._LITERAL.findall(t) == ["A23134216"]
