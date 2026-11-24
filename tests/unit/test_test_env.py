"""framework.test_env: tests must not depend on what earlier tests left in the shared QA companies."""
import datetime as dt
import glob
import re

import yaml

from framework import test_env as te


def test_fixed_date_near_the_verification_day_moves_with_today():
    steps = [{"action": "fill", "target": "x", "value": "19-11-2026"},          # "tomorrow" on 18-11
             {"action": "fill", "target": "x", "value": "17-11-2026"},          # "yesterday"
             {"action": "fill", "target": "x", "value": "2026-11-18"}]
    out = te.rebase_dates(steps, "2026-11-18", today=dt.date(2026, 11, 20))
    assert [s["value"] for s in out] == ["21-11-2026", "19-11-2026", "2026-11-20"]


def test_far_dates_and_fixed_dates_stay():
    steps = [{"action": "fill", "value": "01-04-2026"},                          # financial-year start
             {"action": "fill", "value": "19-11-2026", "fixed_date": True}]
    out = te.rebase_dates(steps, "2026-11-18", today=dt.date(2026, 11, 20))
    assert [s["value"] for s in out] == ["01-04-2026", "19-11-2026"]


def test_same_day_changes_nothing():
    steps = [{"action": "fill", "value": "19-11-2026"}]
    assert te.rebase_dates(steps, "2026-11-20", today=dt.date(2026, 11, 20)) == steps


def test_precondition_lines_become_settings():
    pre = ["Setting: Ask Party in Retail Billing (Sale) = Don't Ask (QA Garment test setup: a new bill starts on Cash)",
           "Settings: Calculation Type in Sale = Exclusive (company default); Ask Party in Retail Billing = Ask",
           "Item QA_Shirt exists"]
    assert te.precondition_settings(pre) == ["Ask Party in Retail Billing #1 = Don't Ask",
                                             "Calculation Type in Sale = Exclusive",
                                             "Ask Party in Retail Billing = Ask"]


def test_leading_assert_setting_is_set_and_later_one_is_still_checked():
    case = {"steps": [{"action": "use_company", "value": "QA Chemist"},
                      {"action": "assert_setting", "value": "Barcode Required = Master wise"},
                      {"action": "open_screen", "target": "sale_bill"},
                      {"action": "assert_setting", "value": "Sale Challan = Yes"}]}
    out = te.prepare_steps(case, today=dt.date(2026, 11, 20))
    assert [s["action"] for s in out] == ["use_company", "ensure_setting", "open_screen", "assert_setting"]


def test_note_naming_the_party_setting_sets_it_first():
    case = {"steps": [{"action": "use_company", "value": "QA Mobile Trade"},
                      {"action": "open_screen", "target": "sale_bill"},
                      {"action": "press", "value": "Enter",
                       "note": "New bill opens with the party list (Ask Party in Retail Billing = Ask)"}]}
    out = te.prepare_steps(case, today=dt.date(2026, 11, 20))
    assert out[1] == {"action": "ensure_setting", "value": "Ask Party in Retail Billing #1 = Ask",
                      "note": "Precondition: Ask Party in Retail Billing #1 = Ask", "optional_env": True}


def test_other_note_pairs_are_not_treated_as_settings():
    # "(Exp. Date column = hidden)" describes what the test CHECKS; setting it would change the test
    case = {"steps": [{"action": "use_company", "value": "QA Chemist"},
                      {"action": "assert_visible", "target": "x", "note": "Column shown (Exp. Date column = hidden)"}]}
    assert [s["action"] for s in te.prepare_steps(case)] == ["use_company", "assert_visible"]


def test_every_case_prepares_without_error():
    loader = getattr(yaml, "CSafeLoader", yaml.SafeLoader)
    n = 0
    for f in glob.glob("testcases/**/*.yaml", recursive=True):
        for c in yaml.load(open(f, encoding="utf-8"), Loader=loader) or []:
            te.prepare_steps(c, today=dt.date(2026, 11, 20))
            n += 1
    assert n > 1000


def test_new_cases_do_not_write_fixed_dates():
    """A case written from now on (no live-app verification yet) uses {today}, {today+1}, ... not a day."""
    loader = getattr(yaml, "CSafeLoader", yaml.SafeLoader)
    bad = []
    for f in glob.glob("testcases/**/*.yaml", recursive=True):
        for c in yaml.load(open(f, encoding="utf-8"), Loader=loader) or []:
            if (c.get("verification") or {}).get("date") or c.get("draft"):
                continue
            for s in c.get("steps") or []:
                v = f"{s.get('value') or ''} {s.get('target') or ''}"
                if not s.get("fixed_date") and re.search(r"(?<!\d)\d{2}-\d{2}-20\d{2}(?!\d)", v) \
                        and not re.search(r"01-04-20\d{2}|31-03-20\d{2}", v):
                    bad.append(f"{c['id']}: {v.strip()[:60]}")
    assert not bad, "Use {today+N} instead of a fixed date (or fixed_date: true):\n" + "\n".join(bad[:20])


def test_read_only_report_for_today_is_pinned_to_the_verification_day():
    case = {"verification": {"date": "2026-11-19"},
            "steps": [{"action": "use_company", "value": "QA GST Pharma Distribution"},
                      {"action": "fill", "target": "input#fromDateFilter", "value": "{today}"},
                      {"action": "fill", "target": "input#toDateFilter", "value": "{today}"},
                      {"action": "assert_visible", "target": "x", "note": "B2C(Small) taxable 500.00"}]}
    out = te.prepare_steps(case, today=dt.date(2026, 11, 20))
    assert [s["value"] for s in out[1:3]] == ["19-11-2026", "19-11-2026"]


def test_report_dates_of_a_case_that_saves_bills_stay_today():
    case = {"verification": {"date": "2026-11-19"},
            "steps": [{"action": "press", "value": "F10", "note": "Save the bill"},
                      {"action": "fill", "target": "input#fromDateFilter", "value": "{today}"}]}
    assert te.prepare_steps(case, today=dt.date(2026, 11, 20))[1]["value"] == "{today}"


def test_dates_the_test_checks_are_not_moved():
    steps = [{"action": "assert_text", "value": "01-11-2026"}, {"action": "wait_text", "value": "19-11-2026"}]
    assert te.rebase_dates(steps, "2026-11-19", today=dt.date(2026, 11, 20)) == steps


def test_a_live_period_the_case_reconciles_is_not_pinned():
    case = {"verification": {"date": "2026-11-19"},
            "steps": [{"action": "fill", "target": "input#fromDateFilter", "value": "{month_start}", "live_date": True},
                      {"action": "fill", "target": "input#toDateFilter", "value": "{today}", "live_date": True}]}
    assert [s["value"] for s in te.prepare_steps(case, today=dt.date(2026, 12, 3))] == ["{month_start}", "{today}"]


def test_a_setting_written_as_a_menu_path_keeps_only_its_name():
    assert te.precondition_settings(["Settings: Control Room > Sale BackDate Billing = No"]) == \
        ["Sale BackDate Billing = No"]


def test_a_setting_the_case_sets_itself_is_not_a_precondition():
    assert te.precondition_settings(["Settings: Mode of Payment required in Sale = Yes set by the steps"]) == []


def test_configure_window_setting_keeps_its_row():
    from framework import test_env
    got = test_env.precondition_settings([
        "Setting: Control Room > Loss Indication (Configure) > Net Loss and Margin Loss Indication Required? = "
        "Forcefully (Configure card, set by hand, default Indicate)"])
    assert got == ["Loss Indication > Net Loss and Margin Loss Indication Required? = Forcefully"]


def test_precondition_value_stops_at_arrows_and_quotes_go():
    from framework import test_env
    assert test_env.precondition_settings(["Setting: Transport Required = Yes -> Esc -> Save -> Ok"]) == \
        ["Transport Required = Yes"]
    assert test_env.precondition_settings(["Setting: 'Patient & Doctor Name Must' = Yes -> Esc"]) == \
        ["Patient & Doctor Name Must = Yes"]


def test_one_way_settings_are_recognised():
    from framework.control_room import _is_one_way, _config_path
    assert _is_one_way("POS?") and _is_one_way("Multi Unit Required In Sale")
    assert not _is_one_way("Sale Return") and not _is_one_way("Pos Billing Mode")
    assert _config_path("Control Room > Loss Indication (Configure) > Net Loss?") == ("Loss Indication", "Net Loss?")
    assert _config_path("Sale Return") is None
