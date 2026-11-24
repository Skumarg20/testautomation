"""
Keep every test independent of what earlier tests left behind in the shared QA test companies.

Found in the Studio sample run (artifacts/studio_regress, 20-Nov-2026): 16 of 56 verified cases failed only
because the company was not in the state they were verified in:
  - a Control Room setting changed by another test that did not put it back (Ask Party, Sale Challan, Barcode)
  - a date written as a fixed day ("19-11-2026" meant "tomorrow" on the day it was verified)
  - data another test used up or added (a variant sold out, a pending order on the party)

What this module does, for every test, without the test having to ask:
  1. Settings baseline: each QA company has a saved "known good" settings file (config/qa_baseline/).
     When a test switches to its company, settings that differ from the file are put back first.
  2. A test's own setting changes are undone after the test (pass or fail) - see StepRunner.
  3. Preconditions written in the case ("Setting: X = Y" lines, or assert_setting steps before the first
     screen is opened) are SET, not only checked.
  4. Fixed dates are moved by the number of days since the case was verified.
  5. When the company cannot be brought into the needed state, the test is reported as
     "Blocked - environment" with the reason, not as a failure of the app.
"""
from __future__ import annotations

import datetime as _dt
import json
import re
import time
from pathlib import Path

from config.settings import ROOT

BASELINE_DIR = ROOT / "config" / "qa_baseline"


class EnvironmentNotReady(RuntimeError):
    """The QA company could not be put into the state the test needs (not an app failure)."""


def _slug(company: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", company.lower()).strip("_")


def baseline_path(company: str) -> Path:
    return BASELINE_DIR / f"{_slug(company)}.json"


def load_baseline(company: str) -> dict | None:
    p = baseline_path(company)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None


# ---------------------------------------------------------------- settings baseline

def capture_baseline(bp, company: str, overrides: dict | None = None) -> dict:
    """Read all Control Room settings of the open company and save them as its baseline.
    overrides: {"Label" or "Label #2": "Value"} to record a value other than the current one."""
    from framework import control_room as cr
    data = cr.capture(bp)
    rows = [{"css": r["css"], "label": r.get("label", ""), "value": r.get("value", ""),
             "options": r.get("options") or []} for r in data.get("raw", []) if r.get("css")]
    for key, val in (overrides or {}).items():
        lab, nth = cr._split_nth(key)
        hit = cr._pick_row(rows, lab, nth)
        hit["value"] = val
    out = {"company": company, "captured_at": time.strftime("%Y-%m-%d %H:%M"), "settings": rows}
    BASELINE_DIR.mkdir(parents=True, exist_ok=True)
    baseline_path(company).write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    return out


def apply_values(bp, wanted: list[tuple[str, str, str]], log=None) -> list[dict]:
    """Set several Control Room controls in ONE open + save. wanted = [(css, label, value)].
    Returns what changed. Raises EnvironmentNotReady when a value does not stick."""
    from framework import control_room as cr, safety, qa_company
    if not wanted:
        return []
    qa_company.require_test_company(bp.page, "put settings back to the company baseline")
    if not cr.open_control_room(bp):
        raise EnvironmentNotReady("Control Room did not open, so the company settings could not be checked.")
    live = {r["css"]: r for r in cr._rows_live(bp)}
    changed, failed = [], []
    for css, label, value in wanted:
        row = live.get(css)
        if not row:
            failed.append(f"{label}: not on the Control Room page")
            continue
        if str(row.get("value", "")).strip().lower() == str(value).strip().lower():
            continue
        res = cr._set_control(bp, css, value)
        if res.get("ok") and res.get("changed", True):
            changed.append({"label": label, "from": row.get("value", ""), "to": value, "css": css})
        elif not res.get("ok"):
            failed.append(f"{label} -> {value}: {res.get('why')}")
    if changed:
        cr._save_setting(bp)
        if not cr.open_control_room(bp):
            raise EnvironmentNotReady("Control Room did not reopen to check the saved settings.")
        now = {r["css"]: r.get("value", "") for r in cr._rows_live(bp)}
        for c in changed:
            if str(now.get(c["css"], "")).strip().lower() != str(c["to"]).strip().lower():
                failed.append(f"{c['label']}: asked {c['to']!r}, after save it is {now.get(c['css'])!r}")
    safety.force_close_modal(bp.page)
    for c in changed:
        if log is not None:
            log.append(f"      setting {c['label']}: {c['from']} -> {c['to']}")
    if failed:
        raise EnvironmentNotReady("These settings could not be set: " + "; ".join(failed[:6]))
    return changed


def restore_baseline(bp, company: str, log=None) -> list[dict]:
    """Put every setting that differs from the company's baseline file back (one save). No file: nothing."""
    base = load_baseline(company)
    if not base:
        return []
    from framework import control_room as cr, safety
    if not cr.open_control_room(bp):
        raise EnvironmentNotReady("Control Room did not open, so the company settings could not be checked.")
    live = {r["css"]: r.get("value", "") for r in cr._rows_live(bp)}
    diff = [(s["css"], s["label"], s["value"]) for s in base["settings"]
            if s["css"] in live and str(live[s["css"]]).strip().lower() != str(s["value"]).strip().lower()]
    if not diff:
        safety.force_close_modal(bp.page)
        if log is not None:
            log.append("      company settings match the baseline")
        return []
    if log is not None:
        log.append(f"      {len(diff)} setting(s) differ from the baseline; putting them back")
    safety.force_close_modal(bp.page)
    return apply_values(bp, diff, log)


# ---------------------------------------------------------------- preparing a case's steps

_SET_LINE = re.compile(r"^\s*settings?\s*:\s*(.+)$", re.I)


def precondition_settings(preconditions: list[str] | None) -> list[str]:
    """'Setting: Ask Party in Retail Billing (Sale) = Don't Ask (QA Garment test setup ...)' -> 'Ask Party in
    Retail Billing #1 = Don't Ask'. Several 'X = Y' pairs separated by ';' are allowed."""
    out = []
    for line in preconditions or []:
        m = _SET_LINE.match(str(line))
        if not m:
            continue
        # "M.R.Master = Yes, M.R Required In Sale? = Yes then No": several pairs split by ';' or ','
        for part in re.split(r";|,(?=[^,=]*=)", m.group(1)):
            if "=" not in part:
                continue
            if re.search(r"(set|changed|turned) (by|in) the steps|by the test itself", part, re.I):
                continue                                    # the case sets it itself
            lab, _, val = part.partition("=")
            # "Yes -> ESC -> Save" / "Yes > Default Qty" / "1, then 3": the value is the first word(s) only
            val = re.split(r"\s*(?:->|>|,\s*then\b|\bthen\b)", val)[0]
            parts = [x.strip() for x in lab.split(">")]
            cfg = next((k for k, x in enumerate(parts[:-1]) if re.search(r"\(\s*configure\s*\)", x, re.I)), None)
            if cfg is not None:      # "Control Room > Loss Indication (Configure) > Net Loss ...?": a Configure window
                row = re.sub(r"\s*\(\s*configure\s*\)", "", parts[cfg], flags=re.I).strip()
                val = re.sub(r"\s*\(.*$", "", val).strip().rstrip(".")
                if row and parts[-1] and val and len(val) <= 40:
                    out.append(f"{row} > {parts[-1]} = {val}")
                continue
            lab = re.sub(r"^.*>\s*", "", lab).strip()          # "Control Room > X" -> "X"
            val = re.sub(r"\s*\(.*$", "", val).strip().rstrip(".")     # drop "(explanation)"
            if not lab or not val or len(val) > 40:
                continue
            q = re.search(r"\((sale|purchase|challan)[^)]*\)\s*$", lab, re.I)
            lab = re.sub(r"\s*\([^)]*\)\s*$", "", lab).strip()
            if q:
                lab += {"sale": " #1", "purchase": " #2", "challan": " #3"}[q.group(1).lower()]
            lab = lab.strip().strip("'\"").strip()               # "'Patient & Doctor Name Must'" -> no quotes
            out.append(f"{lab} = {val}")
    return out


# Settings that only shape how a screen STARTS (not what a test checks). When a step note names one of
# them, the test relies on it, so it is set first. Label -> which repeated row (Sale = #1).
ENV_NOTE_SETTINGS = {"ask party in retail billing": " #1"}
_NOTE_PAIR = re.compile(r"\(([A-Za-z][^=()]{3,60}?)\s*=\s*([^()=]{1,25}?)\)")


def note_settings(steps: list[dict]) -> list[str]:
    out = []
    for s in steps:
        for lab, val in _NOTE_PAIR.findall(str(s.get("note") or "")):
            base = re.sub(r"\s*#\d+$", "", lab.strip()).lower()
            if base in ENV_NOTE_SETTINGS:
                nth = re.search(r"#\d+$", lab.strip())
                out.append(f"{lab.strip() if nth else lab.strip() + ENV_NOTE_SETTINGS[base]} = {val.strip()}")
                break
        if out:
            break                                   # the first one a test names is its starting state
    return out


_OPENS = {"open_screen", "goto", "click", "click_text", "press", "fill", "set_party", "add_item"}


def prepare_steps(case: dict, today: _dt.date | None = None) -> list[dict]:
    """The steps to run for a case, made independent of the company's history (see module doc)."""
    steps = [dict(s) for s in case.get("steps") or []]
    # 3a. assert_setting steps before the first screen is used are preconditions: set them (auto-undone after)
    for s in steps:
        if s.get("action") in _OPENS:
            break
        if s.get("action") == "assert_setting":
            s["action"] = "ensure_setting"
    # 3b. "Setting: X = Y" lines in the case's preconditions, and the few environment settings a step note
    #     names, e.g. "New bill opens with the party list (Ask Party in Retail Billing = Ask)"
    wanted = precondition_settings(case.get("preconditions")) + note_settings(steps)
    seen, extra = set(), []
    for v in wanted:
        key = v.split("=")[0].strip().lower()
        if key not in seen:
            seen.add(key)
            extra.append({"action": "ensure_setting", "value": v, "note": f"Precondition: {v}", "optional_env": True})
    if extra:
        at = next((i + 1 for i, s in enumerate(steps) if s.get("action") == "use_company"), 0)
        steps[at:at] = extra
    # 4. fixed dates
    ver = (case.get("verification") or {}).get("date") or ""
    creates = _creates_data(steps)
    steps = rebase_dates(steps, ver, today, keep_report_dates=not creates)
    if not creates:
        steps = pin_report_period(steps, ver)
    return steps


_TODAY = re.compile(r"\{today([+-]\d+)?\}")


def pin_report_period(steps: list[dict], verified_on: str) -> list[dict]:
    """A case that creates nothing and reads a report 'for today' was checking figures of bills made on the
    day it was verified (TC_GST_019: GSTR-1 for {today} expected that day's B2C 500.00). Run on a later day,
    'today' has other bills. So the report period is pinned to the verification day."""
    vday = _parse_day(verified_on)
    if not vday:
        return steps
    out = []
    for s in steps:
        v = s.get("value")
        # live_date: the case compares two reports for the same live period itself ({month_start}..{today})
        if isinstance(v, str) and _TODAY.search(v) and _REPORT_DATE.search(str(s.get("target") or ""))                 and not s.get("live_date"):
            s = dict(s, value=_TODAY.sub(lambda m: (vday + _dt.timedelta(days=int(m.group(1) or 0))).strftime("%d-%m-%Y"), v),
                     note_dates=f"report period pinned to the verification day ({verified_on})")
        out.append(s)
    return out




# ---------------------------------------------------------------- dates

_DMY = re.compile(r"(?<!\d)(\d{2})([-/])(\d{2})\2(\d{4})(?!\d)")
_YMD = re.compile(r"(?<!\d)(\d{4})-(\d{2})-(\d{2})(?!\d)")


def _parse_day(s: str) -> _dt.date | None:
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d-%b-%Y"):
        try:
            return _dt.datetime.strptime(str(s)[:11].strip(), fmt).date()
        except ValueError:
            continue
    return None


_INPUT_ACTIONS = {"fill", "type", "select", "set_value", "press_sequentially", "fill_date"}
_SAVE_WORDS = re.compile(r"\bsave\b", re.I)
_REPORT_DATE = re.compile(r"from|todate|to_date|txtto|period|start|end", re.I)


def _creates_data(steps: list[dict]) -> bool:
    for s in steps:
        if s.get("action") in ("save_form", "save", "create_party", "create_item", "bulk_sale_bills"):
            return True
        if str(s.get("value") or "").upper() in ("F10", "END", "F9") or _SAVE_WORDS.search(str(s.get("note") or "")):
            return True
    return False


def rebase_dates(steps: list[dict], verified_on: str, today: _dt.date | None = None,
                 window_days: int = 60, keep_report_dates: bool = False) -> list[dict]:
    """Move dates written as fixed days by the days since the case was verified.
    Only dates within `window_days` of the verification day are moved (they mean 'today', 'tomorrow',
    'last week'); far-away dates (financial-year start, a birthday) stay as written.
    A step with `fixed_date: true` is never changed. keep_report_dates: a case that creates nothing and reads
    a report for a date range is looking at data made on the verification day, so its From/To dates stay."""
    vday = _parse_day(verified_on)
    today = today or _dt.date.today()
    if not vday or vday == today:
        return steps
    shift = today - vday

    def move(m, ymd=False):
        try:
            d = (_dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3))) if ymd
                 else _dt.date(int(m.group(4)), int(m.group(3)), int(m.group(1))))
        except ValueError:
            return m.group(0)
        if abs((d - vday).days) > window_days:
            return m.group(0)
        n = d + shift
        return n.strftime("%Y-%m-%d") if ymd else f"{n:%d}{m.group(2)}{n:%m}{m.group(2)}{n:%Y}"

    out = []
    for s in steps:
        # Only dates the test TYPES are moved. A date the test CHECKS on screen (a report period "01-11-2026",
        # a heading) describes the app's output and must stay (TC_CACC_076).
        if s.get("action") not in _INPUT_ACTIONS or s.get("fixed_date")                 or (keep_report_dates and _REPORT_DATE.search(str(s.get("target") or ""))):
            out.append(s)
            continue
        s = dict(s)
        for k in ("value", "target"):
            v = s.get(k)
            if isinstance(v, str) and ("-" in v or "/" in v):
                v2 = _DMY.sub(move, v)
                v2 = _YMD.sub(lambda m: move(m, True), v2)
                if v2 != v:
                    s[k] = v2
                    s.setdefault("note_dates", f"date moved from the verification day ({verified_on})")
        out.append(s)
    return out
