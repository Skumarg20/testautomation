"""
YAML test case ko execute karta hai.

Ek step aisa dikhta hai:
    - action: fill
      target: sale_invoice.party
      value: "{{party_name}}"
      save_as: party      # baad ke steps me {ctx.party} se use kar sakte ho

Supported actions: goto, click, fill, select, press, wait_text, assert_text,
assert_no_text, assert_visible, assert_not_visible, sleep, screenshot, note.
"""
from __future__ import annotations

import re

from framework.test_env import EnvironmentNotReady
from pathlib import Path
import time
from dataclasses import dataclass, field
from typing import Any

from config.settings import settings
from framework.base_page import BasePage
from framework import data_factory
from framework.safety import ModuleNotEnabled, UnsafeClick, dismiss_modal

# Steps that can change data or settings. With "Allow writes" on they run only in a QA test company.
WRITE_ACTIONS = {"save_form", "click", "click_text", "fill", "select", "press", "bulk_sale_bills",
                 "require_setting", "retail_bill", "set_party", "fill_header", "add_item", "add_barcode",
                 "ensure_party", "set_bill_discount", "pick_batch", "set_setting"}

_SIGN_IN_ACTIONS = {"click", "click_text", "fill", "press"}


def _before_company(p, action: str) -> bool:
    """A login test types on the login page and picks from the Organisation List: no company is open there, so no
    data can be written and the QA-company check does not apply. Anywhere else the check runs as always."""
    if action not in _SIGN_IN_ACTIONS:
        return False
    page = getattr(p, "page", None)
    if page is None:
        return False
    try:
        url = page.url or ""
    except Exception:  # noqa: BLE001
        return False
    bare = url.split("?")[0].split("#")[0]
    # the login page: books6.../login redirects to margbooks.com/login/ (or accounts.margbooks.com)
    if bare.startswith(settings.LOGIN_URL) or re.match(r"https://(?:[\w-]+\.)*margbooks\.com/login/?$", bare) \
            or re.match(r"https://accounts\.margbooks\.com/", bare):
        return True
    try:                                   # the Organisation List, with no company open yet
        from framework.auth import on_org_page
        from framework import qa_company
        return bool(on_org_page(page)) and not qa_company.current(page)
    except Exception:  # noqa: BLE001
        return False


PLACEHOLDER = re.compile(r"\{\{(\w+)\}\}")
CTXREF = re.compile(r"\{ctx\.(\w+)([+-]\d+)?\}")       # {ctx.billno}, {ctx.billno+1} (keeps zero padding)
DATEREF = re.compile(r"\{today([+-]\d+)?\}")          # {today}, {today-1}, {today+7} -> dd-mm-yyyy
MONTHREF = re.compile(r"\{(month_start|month)\}")     # {month_start} -> 01-mm-yyyy, {month} -> Nov


def _date_ref(m) -> str:
    import datetime as _dt
    return (_dt.date.today() + _dt.timedelta(days=int(m.group(1) or 0))).strftime("%d-%m-%Y")


def _month_ref(m) -> str:
    import datetime as _dt
    d = _dt.date.today()
    return d.replace(day=1).strftime("%d-%m-%Y") if m.group(1) == "month_start" else d.strftime("%b")


def _last_number(v: str):
    nums = re.findall(r"-?\d+(?:\.\d+)?", str(v).replace(",", ""))
    return float(nums[-1]) if nums else None


_DELTA = re.compile(r"(-?\d+(?:\.\d+)?)[^\d+-]*?\s+([+-])\s+(\d+(?:\.\d+)?)\s*$")


def _side_number(v: str):
    """One side of assert_same: "119.00" -> 119.0; "123.00 - 4" -> 119.0 (a read value plus the change the case
    expects); "1,020.50 Dr" -> 1020.5."""
    t = str(v).replace(",", "").strip()
    if m := _DELTA.search(t):
        n = float(m.group(3))
        return float(m.group(1)) + (n if m.group(2) == "+" else -n)
    return _last_number(t)


class StepFailed(AssertionError):
    pass


class TradeMismatch(Exception):
    """
    Test kisi aur trade ke liye hai (pharma ka test general company pe).
    Ye BUG NAHI hai -- runner ise SKIP maanta hai.
    """


@dataclass
class RunContext:
    vars: dict[str, Any] = field(default_factory=dict)
    log: list[str] = field(default_factory=list)


class StepRunner:
    def __init__(self, page: BasePage, ctx: RunContext | None = None):
        self.p = page
        self.ctx = ctx or RunContext()

    # ---------- templating ----------

    def render(self, value: Any) -> Any:
        if not isinstance(value, str):
            return value
        out = PLACEHOLDER.sub(lambda m: str(data_factory.resolve(m.group(1))), value)
        out = CTXREF.sub(self._ctx_ref, out)
        out = DATEREF.sub(_date_ref, out)
        out = MONTHREF.sub(_month_ref, out)
        if "{now}" in out:                                   # unique per run: e.g. invoice "QA-{now}"
            out = out.replace("{now}", self.ctx.vars.setdefault("_now", time.strftime("%d%H%M%S")))
        return out

    def _ctx_ref(self, m) -> str:
        v = str(self.ctx.vars.get(m.group(1), ""))
        if not m.group(2):
            return v
        commas = "," in v
        nums = list(re.finditer(r"\d+(?:\.\d+)?", v.replace(",", "")))
        if not nums:
            if not v.strip():                                   # empty balance = 0
                return str(int(m.group(2)))
            raise StepFailed(f"{{ctx.{m.group(1)}{m.group(2)}}}: {v!r} has no number")
        v = v.replace(",", "")
        digits = nums[-1]                                      # last number in the value, e.g. "0000012", "96.00"
        d = digits.group()
        if "." in d:                                           # "100.00" - 4 -> "96.00"
            dec = len(d.split(".")[1])
            n = f"{float(d) + int(m.group(2)):{',' if commas else ''}.{dec}f}"
        else:
            n = str(int(d) + int(m.group(2)))
            if d.startswith("0") and len(d) > 1:               # "0000012" -> "0000013": keep bill-number padding
                n = n.zfill(len(d))
            elif commas:
                n = f"{int(n):,}"
        return v[:digits.start()] + n + v[digits.end():]

    # ---------- execution ----------

    def run(self, steps: list[dict]):
        """Run the steps. Steps marked `always: true` (clean-up: put settings back, delete test data) still run
        after an earlier step failed; the first failure is raised afterwards."""
        self._at = 0
        if getattr(self, "auto_undo", True) or not hasattr(self, "_setting_orig"):
            self._setting_orig, self._setting_last = {}, {}
        import json as _json
        self._case_text = _json.dumps(steps, default=str).lower()      # what this test itself mentions
        self._steps_seen = []
        try:
            self._run_steps(steps)
        except EnvironmentNotReady as env:
            self._cleanup_after_failure(steps)
            self._undo_settings()
            if getattr(env, "missing", None) and not getattr(self, "_repairing", False):
                if self._repair_and_rerun(steps, env):
                    return
            raise
        except BaseException:
            # Clean-up runs in order and STOPS at its first failing step: a failed check inside the clean-up
            # (e.g. "is this my bill?") must block the delete that follows it. (A clean-up that ran every step
            # as optional once deleted somebody else's bill.)
            self._cleanup_after_failure(steps)
            self._undo_settings()
            raise
        self._undo_settings()

    def _cleanup_after_failure(self, steps: list[dict]):
        for st in steps[self._at:]:
            if st.get("always"):
                try:
                    self._run_steps([{**st, "always": False}])
                    self.ctx.log.append(f"  CLEANUP OK   {st.get('note') or st.get('action')}")
                except BaseException as ce:  # noqa: BLE001
                    self.ctx.log.append(f"  CLEANUP STOP {st.get('note') or st.get('action')} -> {ce}")
                    break

    on_restart = None          # callback(): the caller resets its per-step state before the re-run

    def _repair_and_rerun(self, steps: list[dict], env) -> bool:
        """The test stopped because shared test data was used up. Put it back (config/qa_data.json recipes) and
        run the whole test again, once. False: no recipe or the repair failed (the test stays Blocked)."""
        from framework import test_data
        self.ctx.log.append(f"  DATA: putting back {', '.join(env.missing)} before running the test again")
        try:
            ok = test_data.repair(self.p, env.missing, self.ctx.log)
        except Exception as e:  # noqa: BLE001
            self.ctx.log.append(f"  DATA: repair failed: {str(e)[:200]}")
            ok = False
        if not ok:
            return False
        self.ctx.log.append("  DATA: back in place -> running the test again from the start")
        if callable(self.on_restart):
            self.on_restart()
        self._repairing = True
        try:
            self.run(steps)
        finally:
            self._repairing = False
        return True

    # Information windows the app opens because of data other tests left behind (a pending order on the
    # party, ...). A test that does not mention them must not be stopped by them (TC_CSAL_068: a 'Pending
    # Orders of <party>' window blocked Alt+H). A test that mentions them is left alone.
    SIDE_POPUPS = (("pending orders of", "pending order"),)

    def _close_side_popups(self):
        page = getattr(self.p, "page", None)
        if page is None:
            return
        try:
            titles = page.evaluate(r"""() => [...document.querySelectorAll('ngb-modal-window')]
                .filter(m => m.getClientRects().length).map(m => (m.innerText || '').split('\n')[0].trim().toLowerCase())""")
        except Exception:  # noqa: BLE001
            return
        for title in titles:
            for starts, word in self.SIDE_POPUPS:
                if title.startswith(starts) and word not in self._case_text:
                    try:
                        page.keyboard.press("Escape")
                        page.wait_for_timeout(800)
                        self.ctx.log.append(f"      closed the '{title[:60]}' window (left by other data; "
                                            f"this test does not use it)")
                    except Exception:  # noqa: BLE001
                        pass

    _ERR_MISSING = re.compile(r"(not visible|timeout|not found|nahi mila|no visible)", re.I)
    _DATA_NAME = re.compile(r"QA_[A-Za-z0-9_]+|(?<![\d.])\d{8,13}(?![\d.])")

    _SHORTAGE = re.compile(r"negative stock|stock (is )?not (available|sufficient|enough)|insufficient stock|"
                           r"out of stock|not enough stock|stock.{0,20}(exceed|less than)|"
                           r"(qty|quantity).{0,30}(exceeds?|more than).{0,20}stock|no stock", re.I)
    # The test itself is ABOUT a shortage (TC_SALE_022 QA_Item_NoStock): never restock behind its back.
    _ABOUT_SHORTAGE = re.compile(r"nostock|no stock|negative|out of stock|minlevel|min level|insufficient|shortage",
                                 re.I)

    def _stock_ran_out(self) -> str | None:
        """The step failed while the app says the stock is not enough, and the test is not a stock test: the
        QA_ items this test uses were sold by earlier tests. Returns those item names."""
        if self._ABOUT_SHORTAGE.search(getattr(self, "_case_text", "")):
            return None
        page = getattr(self.p, "page", None)
        if page is None:
            return None
        try:
            txt = page.evaluate("""() => {
                const t = (window.__mbToasts || []).filter(x => Date.now() - (x.at || 0) < 60000).map(x => x.t);
                const m = [...document.querySelectorAll('ngb-modal-window, .modal.show, .swal2-popup, .toast')]
                    .filter(e => e.getClientRects().length).map(e => e.innerText);
                return t.concat(m).join(' | ');
            }""")
        except Exception:  # noqa: BLE001
            return None
        if not self._SHORTAGE.search(str(txt or "")):
            return None
        names = []
        for st in self._steps_seen:
            for n in re.findall(r"QA_Item[A-Za-z0-9_]*", f"{st.get('target') or ''} {st.get('value') or ''}"):
                if n not in names and n != "QA_Item_":
                    names.append(n)
        return ", ".join(names) or None

    def _missing_test_data(self, step: dict, err: Exception) -> str | None:
        """A step failed looking for a QA_ record or a barcode that this test did not create, and the page does
        not show it at all: the shared test data was used up or changed by another test (TC_GARM_072: variant
        11110001 sold out). That is the environment, not the app."""
        if not self._ERR_MISSING.search(str(err)):
            return None
        # Only when the step PICKS existing data (a lookup window, a party/item/batch pick, reading a stock
        # figure). A step that checks the app's OUTPUT (a report line, a saved bill) stays a real failure.
        picking = (step.get("action") in ("add_item", "set_party", "pick_batch", "read_value")
                   or "ngb-modal-window" in str(step.get("target") or "")
                   or re.search(r"entryNo|invoiceno|billno|voucherno", str(step.get("target") or ""), re.I)
                   or re.search(r"\b(pick|choose|select|stock|balance|variant|batch)\b", str(step.get("note") or ""), re.I))
        if not picking:
            return None
        names = set(self._DATA_NAME.findall(f"{step.get('target') or ''} {step.get('value') or ''}"))
        tgt = str(step.get("target") or "")
        if re.search(r"entryNo|invoiceno|billno|voucherno", tgt, re.I):
            # a saved bill picked by its number from a list (TC_SALE_143: bill 0000001 of an earlier day is not
            # in the list, which opens on Today)
            names |= set(re.findall(r"(?<![\d.])0{3,}\d{1,4}(?![\d.])", tgt))
        if not names:
            return None
        made = set()
        for st in self._steps_seen[:-1]:
            if st.get("action") in ("fill", "type", "create_item", "create_party") or st.get("save_as"):
                made |= set(self._DATA_NAME.findall(f"{st.get('value') or ''}"))
        try:
            body = self.p.page.inner_text("body") or ""
            if "ngb-modal-window" in str(step.get("target") or ""):
                # it is only "missing data" when the lookup window IS open and does not list it; if the window
                # closed (TC_MCAU_079: an Enter picked the first row), the test's flow is the problem
                body = self.p.page.evaluate("() => [...document.querySelectorAll('ngb-modal-window')]"
                                            ".filter(m => m.getClientRects().length).map(m => m.innerText).join(' ')")
                if not body.strip():
                    return None
        except Exception:  # noqa: BLE001
            return None
        gone = [n for n in names if n not in made and n not in body]
        return ", ".join(sorted(gone)) if gone else None

    def _remember_setting(self, label: str, res: dict):
        """First time a test touches a setting, remember its value from before the test."""
        key = label.strip().lower()
        if key not in self._setting_orig:
            self._setting_orig[key] = (label.strip(), res.get("from") if res.get("changed") else res.get("value"))
        self._setting_last[key] = res.get("value")

    def _undo_settings(self):
        """Put back every Control Room setting this test changed (pass or fail), so the next test finds the
        company as it was. Explicit "put it back" steps in a case are fine: then nothing is left to do."""
        if not getattr(self, "auto_undo", True):     # caller runs one step at a time (live session): it undoes
            return
        todo = [(lab, orig) for key, (lab, orig) in getattr(self, "_setting_orig", {}).items()
                if orig is not None and str(self._setting_last.get(key, "")).strip().lower() != str(orig).strip().lower()]
        if not todo:
            return
        from framework import control_room as _cr
        for lab, orig in todo:
            try:
                _cr.set_setting(self.p, lab, str(orig))
                self.ctx.log.append(f"  SETTING BACK {lab} = {orig}")
                self._setting_last[lab.strip().lower()] = orig
            except Exception as e:  # noqa: BLE001
                self.ctx.log.append(f"  SETTING BACK FAILED {lab} = {orig}: {str(e)[:160]} "
                                    f"(the next test's baseline check puts it back)")

    def _run_steps(self, steps: list[dict]):
        for i, step in enumerate(steps, 1):
            self._at = getattr(self, "_at", 0) + 1 if len(steps) > 1 else getattr(self, "_at", 0)
            action = step.get("action")
            target = self.render(step.get("target"))
            value = self.render(step.get("value"))
            shown = step.get("value") if "{{config_password}}" in str(step.get("value") or "") else value
            desc = step.get("note") or f"{action} {target or ''} {shown or ''}".strip()   # never the password
            if hasattr(self, "_steps_seen"):
                self._steps_seen.append(step)
            try:
                if settings.ALLOW_DESTRUCTIVE and action in WRITE_ACTIONS and not _before_company(self.p, action):
                    # Writes are on: they may only happen inside a QA test company, never a real one.
                    from framework import qa_company
                    qa_company.require_test_company(self.p.page, f"run '{action}'")
                if step.get("optional") and getattr(self.p, "page", None) is not None:
                    self.p.page.set_default_timeout(8000)          # an optional step must not wait 60 s
                    try:
                        self._dispatch(action, target, value, step)
                    finally:
                        self.p.page.set_default_timeout(60000)
                else:
                    self._dispatch(action, target, value, step)
                self.ctx.log.append(f"  [{i}] OK   {desc}")
            except TradeMismatch as e:
                self.ctx.log.append(f"  [{i}] SKIP {desc} -> {e}")
                import pytest
                pytest.skip(str(e))
            except ModuleNotEnabled as e:
                # Bug nahi -- module Control Room me OFF hai
                self.ctx.log.append(f"  [{i}] SKIP {desc} -> {e}")
                import pytest
                pytest.skip(str(e))
            except EnvironmentNotReady:
                self.ctx.log.append(f"  [{i}] BLOCKED (environment) {desc}")
                raise
            except UnsafeClick as e:
                if step.get("optional"):
                    self.ctx.log.append(f"  [{i}] SKIP (optional, guard) {desc}")
                    continue
                self.ctx.log.append(f"  [{i}] BLOCKED {desc} -> {e}")
                self.p.screenshot(f"unsafe_step_{i}")
                raise StepFailed(f"Step {i} rok diya gaya (suraksha):\n{e}") from e
            except Exception as e:  # noqa: BLE001
                if step.get("optional"):
                    # e.g. a confirmation the app shows only sometimes ("exit without saving?")
                    self.ctx.log.append(f"  [{i}] SKIP (optional) {desc} -> {str(e)[:120]}")
                    continue
                gone = self._missing_test_data(step, e) if hasattr(self, "_steps_seen") else None
                short = None if gone or not hasattr(self, "_steps_seen") else self._stock_ran_out()
                if short:
                    self.ctx.log.append(f"  [{i}] BLOCKED (stock ran out: {short}) {desc}")
                    err = EnvironmentNotReady(
                        f"Step {i} ({desc}): the app says the stock of {short} is not enough (other tests sold it). "
                        f"Restock it, then run again.")
                    err.missing = [g.strip() for g in short.split(",") if g.strip()]
                    raise err from e
                if gone:
                    self.ctx.log.append(f"  [{i}] BLOCKED (test data missing: {gone}) {desc}")
                    err = EnvironmentNotReady(
                        f"Step {i} ({desc}): test data {gone} is not in this company any more (another test used "
                        f"it up or changed it). Recreate or restock it, then run again.")
                    err.missing = [g.strip() for g in gone.split(",") if g.strip()]
                    raise err from e
                self.ctx.log.append(f"  [{i}] FAIL {desc} -> {e}")
                self.p.screenshot(f"fail_step_{i}_{int(time.time())}")
                raise StepFailed(f"Step {i} failed: {desc}\n{e}") from e

            if (name := step.get("save_as")) and action != "read_value":
                self.ctx.vars[name] = value

    # ---- POM tak pahunch ----

    def _form(self):
        from pages.transaction_form import TransactionForm
        if not getattr(self, "_form_obj", None):
            self._form_obj = TransactionForm(self.p)
            self._form_obj.clear_popups()
        self._form_obj.refresh()      # naya tab khula ho to suffix dobara
        return self._form_obj

    def _sale(self):
        from pages.sale_bill_page import SaleBillPage
        if not getattr(self, "_sale_obj", None):
            self._sale_obj = SaleBillPage(self.p)
            self._sale_obj.clear_popups()
        self._sale_obj.refresh()
        return self._sale_obj

    def _retail(self):
        from pages.retail_billing import RetailBillPage
        if not getattr(self, "_retail_obj", None):
            self._retail_obj = RetailBillPage(self.p)
            self._retail_obj.clear_popups()
        self._retail_obj.refresh()
        return self._retail_obj

    def _check_totals(self, spec: str):
        """'cgst=5, sgst=5' jaisi cheez jaancho."""
        totals = self._form().get_totals()
        bad = []
        for part in str(spec).split(","):
            if "=" not in part:
                continue
            k, v = [x.strip() for x in part.split("=", 1)]
            got = totals.get(k)
            try:
                ok = got is not None and abs(float(got) - float(v)) < 0.01
            except (TypeError, ValueError):
                ok = str(got) == v
            if not ok:
                bad.append(f"{k}: mila {got}, chahiye tha {v}")
        if bad:
            raise StepFailed("Total galat hai --\n  " + "\n  ".join(bad)
                             + f"\n  Poore totals: {totals}")

    # The side menu opens a fly-out while the mouse rests on it (it stays there after a menu click) and the
    # fly-out covers the screen: "<a id=menu...> from <div class=lft-cmp> subtree intercepts pointer events"
    # (TC_GARM_056 clean-up). Move the mouse off the menu and try the step once more.
    _MENU_COVER = re.compile(r"intercepts pointer events", re.I)
    _MENU_HINT = re.compile(r"lft-cmp|id=\"menu|sidebar|side-menu|menu-\d", re.I)

    _COL_ID = re.compile(r'@col-id="([^"]+)"|\[col-id="([^"]+)"\]')
    _REVEAL_COL_JS = """([col, step]) => {
        const has = () => [...document.querySelectorAll('.ag-row [col-id="' + col + '"]')].length > 0;
        if (has()) return 'found';
        const vps = [...document.querySelectorAll('.ag-body-horizontal-scroll-viewport, .ag-center-cols-viewport, .ag-body-viewport')]
            .filter(v => v.scrollWidth > v.clientWidth + 2 && v.offsetParent !== null);
        if (!vps.length) return 'no-scroll';
        let moved = false;
        for (const v of vps) {
            const before = v.scrollLeft;
            v.scrollLeft = Math.min(v.scrollLeft + step, v.scrollWidth);
            v.dispatchEvent(new Event('scroll'));
            if (v.scrollLeft !== before) moved = true;
        }
        return moved ? 'moved' : 'end';
    }"""

    def _reveal_ag_column(self, target) -> bool:
        """ag-Grid draws only the columns in view: a cell of a column far to the right (GSTR-2 "Central Tax") is not
        in the page until the grid is scrolled to it. Scroll the grid right, step by step, until the column is drawn."""
        m = self._COL_ID.search(str(target or ""))
        if not m or getattr(self.p, "page", None) is None:
            return False
        col = m.group(1) or m.group(2)
        try:
            self.p.page.evaluate("""() => document.querySelectorAll('.ag-body-horizontal-scroll-viewport, .ag-center-cols-viewport, .ag-body-viewport')
                .forEach(v => { v.scrollLeft = 0; v.dispatchEvent(new Event('scroll')); })""")
            for _ in range(30):
                r = self.p.page.evaluate(self._REVEAL_COL_JS, [col, 250])
                if r == "found":
                    self.p.page.wait_for_timeout(400)
                    self.ctx.log.append(f"      scrolled the grid right to show column {col!r}")
                    return True
                if r != "moved":
                    return False
                self.p.page.wait_for_timeout(150)
        except Exception:  # noqa: BLE001
            return False
        return False

    def _text_on_screen(self, text: str) -> bool:
        try:
            return self.p.page.get_by_text(str(text), exact=False).first.is_visible(timeout=1000)
        except Exception:  # noqa: BLE001
            return False

    def _dispatch(self, action, target, value, step):
        # A step that depends on what the app shows: "if_text" runs it only when that text is on the screen (a popup
        # that comes only sometimes), "unless_text" skips it when the text is there (the next screen already came).
        if step.get("if_text") and not self._text_on_screen(step["if_text"]):
            self.ctx.log.append(f"      not needed: {step['if_text']!r} is not on the screen")
            return None
        if step.get("unless_text") and self._text_on_screen(step["unless_text"]):
            self.ctx.log.append(f"      not needed: {step['unless_text']!r} is already on the screen")
            return None
        try:
            out = self._dispatch_once(action, target, value, step)
        except Exception as e:  # noqa: BLE001
            msg = str(e)
            if self._MENU_COVER.search(msg) and self._MENU_HINT.search(msg):
                self._mouse_off_menu()
                self.ctx.log.append("      side menu covered the screen: moved the mouse away and tried again")
                out = self._dispatch_once(action, target, value, step)
            elif self._ERR_MISSING.search(msg) and (doc := self._FIXED_DOC.search(f"{target or ''} {value or ''}"))                     and self._widen_list_period(doc.group(1)):
                self.ctx.log.append("      the record is from an earlier day: list period widened to the whole "
                                    "financial year, trying again")
                out = self._dispatch_once(action, target, value, step)
            elif self._answer_unasked_popup():
                out = self._dispatch_once(action, target, value, step)
            elif self._ERR_MISSING.search(msg) and "ngb-modal-window" in str(target or "")                     and self._scroll_modal_grid_to(self._LITERAL.findall(str(target))):
                self.ctx.log.append("      the row was outside the visible part of the window's list: scrolled to it, "
                                    "trying again")
                out = self._dispatch_once(action, target, value, step)
            else:
                raise
        if action in ("open_screen", "open_menu"):
            self._mouse_off_menu()
        return out

    # Warnings the app raises because of what OTHER tests left behind (the item's cost moved, so a normal rate is
    # now "at loss"), which a test that does not talk about them never expects (TC_SALE_145: a Net Loss 0.00%
    # window after the rate). (words that identify the window, word the case would use, button that goes on)
    # A "key:<Key>" button presses that key instead (Select Store: Main Store is the highlighted first row; it
    # appears once another test made a second store, TC_SALE_048).
    UNASKED_POPUPS = ((("net loss", "loss amt"), "loss", "#btnYes"),
                      (("select store", "store name"), "store", "key:Enter"),
                      # "Discount / Item Discount %: 0.00" after the party, when a bill setting another test changed
                      # asks for it (TC_PUR_024): Enter keeps 0.00
                      (("discount", "item discount %"), "discount", "key:Enter"))

    def _answer_unasked_popup(self) -> bool:
        page = getattr(self.p, "page", None)
        if page is None:
            return False
        try:
            text = page.evaluate("""() => [...document.querySelectorAll('ngb-modal-window, .modal.show')]
                .filter(e => e.getClientRects().length).map(e => (e.innerText || '').toLowerCase()).join(' | ')""")
        except Exception:  # noqa: BLE001
            return False
        for words, topic, button in self.UNASKED_POPUPS:
            if text and all(w in text for w in words) and topic not in getattr(self, "_case_text", ""):
                if button.startswith("key:"):
                    page.keyboard.press(button[4:])
                    page.wait_for_timeout(1000)
                    self.ctx.log.append(f"      a '{topic}' window the test does not expect (left by other tests' "
                                        f"data) was in the way: pressed {button[4:]}, trying the step again")
                    return True
                btn = page.locator(button)
                try:
                    if not (btn.count() and btn.first.is_visible()):
                        continue
                    from framework import safety as _sf
                    _sf.guarded_click(btn.first, f"unasked:{topic}", inside_modal=True)
                    page.wait_for_timeout(800)
                except Exception:  # noqa: BLE001
                    continue
                self.ctx.log.append(f"      a '{topic}' warning the test does not expect (left by other tests' data) "
                                    f"was in the way: answered {button}, trying the step again")
                return True
        return False

    @staticmethod
    def _screen_marker_alternatives(text: str) -> list[str]:
        """A wait for one of a screen's marker texts ("Getting Started" = the dashboard) accepts any of that screen's
        markers: the dashboard shows "Getting Started" only in some companies (TC_SALE_149 on QA GST Pharma)."""
        from framework.screens import SCREENS
        for sc in SCREENS.values():
            m = sc.get("marker")
            if isinstance(m, list) and len(m) > 1 and text in m:
                return list(m)
        return []

    def _wait_any_text(self, texts: list[str], timeout_ms=None):
        import time as _t
        from config.settings import settings as _s
        end = _t.time() + (timeout_ms or _s.TIMEOUT) / 1000
        while True:
            for t in texts:
                try:
                    self.p.wait_for_text(t, 300)
                    return
                except Exception:  # noqa: BLE001
                    pass
            if _t.time() > end:
                raise TimeoutError(f"none of {texts!r} visible after {(timeout_ms or _s.TIMEOUT) // 1000} s")

    # A popup list (ag-grid) only renders the rows in view: a serial / batch / party the test just made can sit
    # below the first 10 rows (TC_MCAU_070: 21 serials, the new A<now> was row 17).
    _LITERAL = re.compile(r'normalize-space\((?:text\(\)|\.)?\)\s*=\s*"([^"]+)"')
    _SCROLL_FIND_JS = """async (texts) => {
        const modals = [...document.querySelectorAll('ngb-modal-window, .modal.show')].filter(m => m.getClientRects().length);
        const has = m => [...m.querySelectorAll('[role=row] *')].some(e => texts.includes((e.textContent || '').trim()));
        for (const m of modals) {
            for (const vp of m.querySelectorAll('.ag-body-viewport')) {
                if (vp.scrollHeight <= vp.clientHeight + 2) continue;
                vp.scrollTop = 0;
                for (let k = 0; k < 400; k++) {
                    await new Promise(r => setTimeout(r, 120));
                    if (has(m)) {
                        const hit = [...m.querySelectorAll('[role=row] *')].find(e => texts.includes((e.textContent || '').trim()));
                        if (hit) hit.scrollIntoView({block: 'center'});
                        return true;
                    }
                    if (vp.scrollTop + vp.clientHeight >= vp.scrollHeight - 1) break;
                    vp.scrollTop += Math.max(20, vp.clientHeight * 0.8);
                }
            }
        }
        return false;
    }"""

    def _scroll_modal_grid_to(self, texts: list[str]) -> bool:
        page = getattr(self.p, "page", None)
        texts = [t for t in texts if t.strip()]
        if page is None:
            return False
        if not texts:
            # a step on a row by its place (@row-index="0") after an earlier step scrolled the list down
            # (TC_MCAU_109): back to the top of the window's list
            try:
                moved = bool(page.evaluate("""() => { let moved = false;
                    for (const m of document.querySelectorAll('ngb-modal-window, .modal.show')) {
                      if (!m.getClientRects().length) continue;
                      for (const vp of m.querySelectorAll('.ag-body-viewport'))
                        if (vp.scrollTop > 0) { vp.scrollTop = 0; moved = true; } }
                    return moved; }"""))
            except Exception:  # noqa: BLE001
                return False
            if moved:
                page.wait_for_timeout(500)
            return moved
        try:
            found = bool(page.evaluate(self._SCROLL_FIND_JS, texts))
        except Exception:  # noqa: BLE001
            return False
        if found:
            page.wait_for_timeout(400)
        return found

    # A record named by its number ("0000001", "CN00002"): made on the verification day, so a list that opens on
    # "Today" no longer shows it a day later (TC_SALE_143).
    _FIXED_DOC = re.compile(r"(?<![\w{.])(0{3,}\d{1,4}|[A-Z]{2}0\d{3,})(?!\w)")

    def _widen_list_period(self, doc: str | None = None) -> bool:
        """Set the open list's period to 01-04 (start of the financial year) .. today with Custom + Apply, then
        type the document number into the list's own search box (a long list only renders the rows in view).
        False when the screen has no such period picker."""
        page = getattr(self.p, "page", None)
        if page is None:
            return False
        import datetime as _dt
        try:
            btn = page.locator("xpath=//button[normalize-space()='Today' or normalize-space()='Yesterday' or "
                               "normalize-space()='This Week' or normalize-space()='Last 7 Days' or "
                               "normalize-space()='This Month' or normalize-space()='Previous Month']")
            if not (btn.count() and btn.first.is_visible()):
                return False
            from framework import safety as _sf
            _sf.guarded_click(btn.first, "list.period")
            page.wait_for_timeout(800)
            frm, to = page.locator("#txtfromDate"), page.locator("#txttoDate")
            if not (frm.count() and frm.first.is_visible()):
                page.keyboard.press("Escape")
                return False
            d = _dt.date.today()
            fy = _dt.date(d.year if d.month >= 4 else d.year - 1, 4, 1)
            for loc, val in ((frm.first, fy.strftime("%d-%m-%Y")), (to.first, d.strftime("%d-%m-%Y"))):
                loc.focus()
                loc.press("Control+a")
                loc.type(val, delay=20)
            _sf.guarded_click(page.locator("#txtApply").first, "list.period.apply", inside_modal=True)
            page.wait_for_timeout(3000)
            if doc:
                box = page.locator("input[placeholder^='Search here']:not(#controlRoomSearchField)")
                if box.count() and box.first.is_visible():
                    box.first.fill(doc)
                    page.wait_for_timeout(2500)
            return True
        except Exception:  # noqa: BLE001
            return False

    _OPENS_WINDOW = re.compile(r"(?i)\bopens?\b[^.;]*?\b(select (?:party|item|batch|ledger|customer|supplier|"
                               r"patient|doctor|account))\b")

    # "Open the item list" / "opens the party list": the window the note names.
    _OPENS_LIST = re.compile(r"(?i)\bopens?\b[^.;]*?\b(item|party|batch|ledger) list\b")

    def _window_title_in_note(self, step: dict) -> str | None:
        note = str(step.get("note") or "")
        if m := self._OPENS_WINDOW.search(note):
            return m.group(1).lower()
        if m := self._OPENS_LIST.search(note):
            return f"select {m.group(1).lower()}"
        return None

    def _modal_with(self, title: str) -> bool:
        try:
            return bool(self.p.page.evaluate("""(t) => [...document.querySelectorAll('ngb-modal-window, .modal.show')]
                .filter(e => e.getClientRects().length)
                .some(e => (e.innerText || '').toLowerCase().slice(0, 80).includes(t))""", title))
        except Exception:  # noqa: BLE001
            return False

    def _wait_lookup_rows(self, timeout_ms: int = 6000):
        """Enter in a list window (Select Party / Item) picks the highlighted row. Pressed while the rows are still
        loading it does nothing and the window stays open (TC_SALE_087: 'take the first party'). Wait for rows."""
        page = getattr(self.p, "page", None)
        if page is None:
            return
        js = """() => { const m = [...document.querySelectorAll('ngb-modal-window')].filter(e => e.getClientRects().length).pop();
                 if (!m || !m.querySelector('.ag-root')) return true;
                 return m.querySelectorAll('.ag-center-cols-container .ag-row').length > 0; }"""
        for _ in range(max(1, timeout_ms // 250)):
            try:
                if page.evaluate(js):
                    return
            except Exception:  # noqa: BLE001
                return
            page.wait_for_timeout(250)

    def _enter_until_window(self, step: dict):
        """The note says this Enter opens a list window, but the cursor started one field earlier (a Store field
        some companies show: TC_SALE_041 in QA Grocery), so the first Enter only moved the cursor. One more Enter,
        only if no window opened and the cursor is now in the bill's grid."""
        title = self._window_title_in_note(step)
        page = getattr(self.p, "page", None)
        if not title or page is None:
            return
        for _ in range(12):
            page.wait_for_timeout(250)
            if self._modal_with(title):
                return
        try:      # cursor in the grid, and no other window open (an Enter there would act in that window)
            in_grid = page.evaluate("() => { const e = document.activeElement; "
                                    "const modal = [...document.querySelectorAll('ngb-modal-window, .modal.show')]"
                                    ".some(m => m.getClientRects().length); "
                                    "return !modal && !!(e && e.closest && e.closest('.ag-root, ag-grid-angular')); }")
        except Exception:  # noqa: BLE001
            in_grid = False
        if in_grid:
            page.keyboard.press("Enter")
            self.ctx.log.append(f"      Enter only moved the cursor into the grid: pressed it again to open {title}")

    def _window_already_open(self, step: dict) -> bool:
        """The step's note says this Enter OPENS a lookup window ("Enter in Party Name opens the Select Party
        window") and that window is already open, because the click before it opened it. Pressing Enter now would
        pick the first row and close it (TC_MCAU_079 picked Cash Account). Waits up to 2 s for it to show."""
        m = self._OPENS_WINDOW.search(str(step.get("note") or ""))
        page = getattr(self.p, "page", None)
        if not m or page is None:
            return False
        title = m.group(1).lower()
        for _ in range(8):
            try:
                hit = page.evaluate("""(t) => [...document.querySelectorAll('ngb-modal-window, .modal.show')]
                    .filter(e => e.getClientRects().length)
                    .some(e => (e.innerText || '').toLowerCase().slice(0, 80).includes(t))""", title)
            except Exception:  # noqa: BLE001
                return False
            if hit:
                return True
            page.wait_for_timeout(250)
        return False

    def _mouse_off_menu(self):
        try:
            vp = self.p.page.viewport_size or {"width": 1440, "height": 900}
            self.p.page.mouse.move(vp["width"] * 0.6, vp["height"] * 0.12)
            self.p.page.wait_for_timeout(600)
        except Exception:  # noqa: BLE001
            pass

    def _dispatch_once(self, action, target, value, step):
        match action:
            case "goto":
                self.p.goto(target or "/")
            case "open_menu":
                # "Sale > Bill" ya "sale.bill" -- dono chalega.
                # Tester ke liye menu ka naam yaad rakhna aasan hai,
                # screen ka technical naam nahi.
                from framework import menu_tree
                from framework.screens import open_screen
                want = str(target or value or "").strip()
                node = menu_tree.by_id(want)
                if not node:
                    for n, path in menu_tree.walk():
                        if " > ".join(path).lower() == want.lower() \
                                or n["label"].lower() == want.lower():
                            node = n
                            break
                if not node:
                    raise StepFailed(
                        f"Menu me '{want}' nahi mila.\n"
                        f"  Aise likho: 'Sale > Bill' ya 'sale.bill'")
                # value me "new"/"create" ho to "+" wala form
                want_new = str(value or "").strip().lower() in ("new", "create", "+")
                screen = (node.get("create") if want_new else None) \
                    or node.get("screen") or node.get("create")
                if not screen:
                    raise StepFailed(
                        f"'{want}' sirf ek folder hai -- uske andar ka item chuno")
                if not open_screen(self.p, screen):
                    raise StepFailed(f"'{want}' ({screen}) khul nahi paya")

            case "set_setting":
                # "Sale BackDate Billing = Yes"  (any Control Room label; 'Label #2' for a repeated label)
                from framework import control_room as _cr
                lab, _, want = str(value).rpartition("=")
                res = _cr.set_setting(self.p, lab.strip(), want.strip())
                self._remember_setting(lab, res)
                self.ctx.log.append(f"      setting {res['label']}: "
                                    + (f"{res.get('from')} -> {res['value']}" if res["changed"] else f"already {res['value']}"))

            case "ensure_setting":
                # A precondition: make the setting what the test needs (undone after the test). If the company
                # refuses (e.g. "Transaction Found"), the test is blocked by its environment, not failed.
                from framework import control_room as _cr
                from framework.test_env import EnvironmentNotReady
                lab, _, want = str(value).rpartition("=")
                from framework.test_env import ENV_NOTE_SETTINGS
                if step.get("optional_env"):
                    # Read from the case's own words ("= No for the test"): use the option the words start with.
                    try:
                        opts = _cr.read_setting(self.p, lab.strip()).get("options") or []
                        hit = max((o for o in opts if want.strip().lower().startswith(o.lower())), key=len, default=None)
                        if hit:
                            want = hit
                        elif opts:
                            self.ctx.log.append(f"      precondition left to the company baseline: {value} "
                                                f"(not one of {opts})")
                            return
                    except Exception:  # noqa: BLE001
                        pass                                   # unknown / repeated label: handled below
                try:
                    try:
                        res = _cr.set_setting(self.p, lab.strip(), want.strip())
                    except _cr.ControlRoomNotOpen as e:
                        base = lab.strip().lower()
                        if "settings match" in str(e) and base in ENV_NOTE_SETTINGS:
                            lab = lab.strip() + ENV_NOTE_SETTINGS[base]          # the Sale row of a repeated label
                            res = _cr.set_setting(self.p, lab, want.strip())
                        else:
                            raise
                except Exception as e:  # noqa: BLE001
                    if step.get("optional_env"):
                        # Read from the case's own words, not a step of the case: when it cannot be applied
                        # (unknown label, wording that is not an option), leave it to the baseline and let the
                        # case's own steps decide. It must never block a test (TC_CSAL_067).
                        self.ctx.log.append(f"      precondition left to the company baseline: {value} ({str(e)[:100]})")
                        return
                    if isinstance(e, _cr.ControlRoomNotOpen) or "vikalp nahi" in str(e) or "could not be set" in str(e):
                        raise EnvironmentNotReady(f"Precondition {value!r} could not be set: {e}") from e
                    raise
                self._remember_setting(lab, res)
                self.ctx.log.append(f"      precondition {res['label']}: "
                                    + (f"{res.get('from')} -> {res['value']}" if res["changed"] else f"already {res['value']}"))

            case "assert_setting":
                from framework import control_room as _cr
                lab, _, want = str(value).rpartition("=")
                if not lab.strip():
                    raise StepFailed(f"assert_setting wants 'Label = Value' (or 'Label #2 = Value'), got {value!r}")
                res = _cr.read_setting(self.p, lab.strip())
                if str(res["value"]).strip().lower() != want.strip().lower():
                    raise StepFailed(f"Setting {res['label']!r} is {res['value']!r}, expected {want.strip()!r}")

            case "dblclick":
                from framework import safety as _sf
                el = self.p.find(target, want="click")
                _sf.assert_safe(el, f"dblclick:{target}")
                el.dblclick()
                self.p.settle()

            case "upload":
                # target: the <input type=file>; value: a file under artifacts/verify (made by the verifier)
                from pathlib import Path as _P
                root = _P(__file__).resolve().parents[1]
                f = (root / str(value)).resolve()
                if not str(f).startswith(str((root / "artifacts" / "verify").resolve())) or not f.exists():
                    raise StepFailed(f"upload: {value!r} must be an existing file under artifacts/verify/")
                self.p.find(target).set_input_files(str(f))
                self.p.settle()

            case "download":
                # click target, wait for the file; value: a part of the expected file name. Saved under
                # artifacts/verify/downloads/; its path is {ctx.download}.
                from pathlib import Path as _P
                d = _P(__file__).resolve().parents[1] / "artifacts" / "verify" / "downloads"
                d.mkdir(parents=True, exist_ok=True)
                with self.p.page.expect_download(timeout=int(step.get("timeout_ms") or 60000)) as dl:
                    from framework import safety as _sf
                    _sf.guarded_click(self.p.find(target, want="click"), f"download:{target}")
                name = dl.value.suggested_filename
                if value and str(value).lower() not in name.lower():
                    raise StepFailed(f"downloaded {name!r}, expected a name containing {value!r}")
                out = d / f"{int(time.time())}_{name}"
                dl.value.save_as(str(out))
                self.ctx.vars["download"] = str(out)
                self.ctx.log.append(f"  downloaded {name} -> {out}")

            case "preview_text":
                # Click target (e.g. Preview), read the new tab (PDF or HTML) as text, close it, and check that every
                # part of value ("A | B") is in it. Text is kept as {ctx.preview}.
                import shutil, subprocess, tempfile
                from framework import safety as _sf
                ctx_ = self.p.page.context
                with ctx_.expect_page(timeout=int(step.get("timeout_ms") or 60000)) as pinfo:
                    _sf.guarded_click(self.p.find(target, want="click"), f"preview:{target}")
                tab = pinfo.value
                text = ""
                try:
                    tab.wait_for_load_state("domcontentloaded", timeout=30000)
                    url = tab.url
                    if url.startswith(("blob:", "data:")) or url.lower().split("?")[0].endswith(".pdf") or "pdf" in url.lower():
                        data = tab.evaluate("""async u => { const r = await fetch(u); const b = new Uint8Array(await r.arrayBuffer());
                                               let s = ''; for (const x of b) s += String.fromCharCode(x); return btoa(s); }""", url)
                        import base64
                        tool = shutil.which("pdftotext")
                        if not tool:
                            raise StepFailed("preview_text: pdftotext is not installed")
                        with tempfile.TemporaryDirectory() as td:
                            f = Path(td) / "p.pdf"
                            f.write_bytes(base64.b64decode(data))
                            text = subprocess.run([tool, "-layout", str(f), "-"], capture_output=True, text=True,
                                                  timeout=60).stdout
                    else:
                        text = tab.inner_text("body", timeout=10000)
                finally:
                    try:
                        tab.close()
                    except Exception:  # noqa: BLE001
                        pass
                self.ctx.vars["preview"] = " ".join(text.split())
                flat = self.ctx.vars["preview"].lower()
                missing = [w.strip() for w in str(value or "").split("|") if w.strip() and w.strip().lower() not in flat]
                if missing:
                    raise StepFailed(f"preview does not contain {missing}; it starts: {self.ctx.vars['preview'][:300]!r}")

            case "hover":
                self.p.find(target).hover()
                self.p.page.wait_for_timeout(500)

            case "network":
                # value "offline" / "online": cut or restore the browser's network (e.g. save during an outage)
                self.p.page.context.set_offline(str(value).strip().lower() in ("offline", "off", "false", "0"))

            case "relogin":
                # Sign out (if the steps did not already) and sign in again, then reopen the same company.
                from framework import qa_company
                from framework.auth import login
                co = qa_company.current(self.p.page) or self.ctx.vars.get("_company", "")
                self.p.page.context.clear_cookies()
                login(self.p.page, verbose=False)
                if co:
                    qa_company.switch(self.p.page, co)

            case "form_setting":
                # A setting of the open screen's own "⚙ Settings" panel (Sale Bill Setting > Basic / Advance Setting),
                # which the Control Room list does not hold: "Stock Negative allowed = No". The app saves it as soon as
                # it is chosen. Only in a QA test company. A case puts it back with an `always: true` step.
                lab, _, want = str(value).rpartition("=")
                lab, want = lab.strip(), want.strip()
                from framework import qa_company
                qa_company.require_test_company(self.p.page, f"change the screen setting '{lab}'")
                page = self.p.page
                for _ in range(3):                       # a party / item list popup covers the header icons
                    if not page.locator("ngb-modal-window").count():
                        break
                    page.keyboard.press("Escape")
                    page.wait_for_timeout(600)
                page.locator("#aControlRoomSetting").first.click()  # noqa: raw-click (opens the settings panel; QA company checked above)
                q = f'"{lab}"' if '"' not in lab else f"'{lab}'"
                sel = page.locator(f"xpath=//*[normalize-space(text())={q}]/ancestor::*[.//select][1]//select").first
                try:
                    sel.wait_for(state="visible", timeout=8000)
                except Exception:  # noqa: BLE001  (not on Basic Setting: look on Advance Setting)
                    page.get_by_text("Advance Setting", exact=True).first.click()  # noqa: raw-click (tab inside the settings panel)
                    sel.wait_for(state="visible", timeout=8000)
                shown = "x => x.options[x.selectedIndex] ? x.options[x.selectedIndex].text.trim() : ''"
                before = sel.evaluate(shown)
                if before.lower() != want.lower():
                    sel.select_option(label=want)
                    page.wait_for_timeout(2000)
                after = sel.evaluate(shown)
                page.evaluate("""() => { const b = [...document.querySelectorAll('button.itemcontrolClose')].find(e => {
                    const r = e.getBoundingClientRect(); return r.width > 0 && r.left >= 0 && r.right <= window.innerWidth; });
                    if (b) b.click(); }""")
                page.wait_for_timeout(1000)
                if after.lower() != want.lower():
                    raise StepFailed(f"screen setting '{lab}' is {after!r}, wanted {want!r}")
                self.ctx.log.append(f"      screen setting {lab}: {before} -> {after}")

            case "sign_out":
                # A login test starts here: drop this browser's session (cookies, storage) and open the login page.
                # Only this run's own browser is signed out; the next test signs in again by itself.
                page = self.p.page
                page.context.clear_cookies()
                clear = "() => { try { localStorage.clear(); sessionStorage.clear(); } catch (e) {} }"
                try:
                    page.evaluate(clear)
                except Exception:  # noqa: BLE001
                    pass
                page.goto(target or settings.LOGIN_URL, wait_until="domcontentloaded")
                try:
                    page.evaluate(clear)            # the login site's own storage ("remember me")
                except Exception:  # noqa: BLE001
                    pass
                page.wait_for_timeout(2000)

            case "reload":
                # Browser refresh (F5 inside the app is swallowed by the grid). Waits for the page to settle.
                self.p.page.reload(wait_until="domcontentloaded")
                self.p.page.wait_for_timeout(4000)
                self.p.settle()

            case "assert_same":
                # Two values the test read earlier must agree: "{ctx.gstr2_cgst} = {ctx.gstr3b_cgst}". Numbers are
                # compared as numbers (the last number of each side, "1,020.50 Dr" -> 1020.5); else as text.
                # Lets a case check that two reports agree instead of a fixed total other tests keep changing.
                left, sep, right = str(value).partition("=")
                if not sep:
                    raise StepFailed(f"assert_same needs 'A = B', got {value!r}")
                a, b = _side_number(left), _side_number(right)
                ok = (a is not None and b is not None and abs(a - b) < 0.005) if (a is not None or b is not None)                     else left.strip() == right.strip()
                if not ok:
                    raise StepFailed(f"Not the same: {left.strip()!r} vs {right.strip()!r}")
                self.ctx.log.append(f"      same: {left.strip()} = {right.strip()}")

            case "read_value":
                # Remember a field's value (or an element's text) as {ctx.<save_as>} for later steps.
                if not self.p.is_visible(target, timeout_ms=3000):
                    self._reveal_ag_column(target)         # a grid column out of view is not drawn yet
                el = self.p.find(target)
                try:
                    got = el.input_value(timeout=5000)
                except Exception:  # noqa: BLE001  (not an input)
                    got = el.inner_text(timeout=5000)
                name = step.get("save_as") or str(value or "value")
                self.ctx.vars[name] = " ".join(str(got).replace(" ", " ").split())
                self.ctx.log.append(f"  read {target} -> {name} = {self.ctx.vars[name]!r}")

            case "watch_requests":
                # Start counting the app's network requests whose URL contains `value` (e.g. "Ledger/List").
                pat = str(value or target)
                hits = self.ctx.vars.setdefault("_req_" + pat, [])
                hits.clear()
                if not self.ctx.vars.get("_reqw_" + pat):
                    self.p.page.on("request", lambda r, pat=pat, hits=hits: hits.append(r.url) if pat in r.url else None)
                    self.ctx.vars["_reqw_" + pat] = True

            case "assert_requests":
                # value: "<url part> <op> <n>", op one of == <= >= < >  (after watch_requests with the same url part)
                m = re.match(r"\s*(.+?)\s*(==|<=|>=|<|>)\s*(\d+)\s*$", str(value))
                if not m:
                    raise StepFailed(f"assert_requests wants 'url part <= N', got {value!r}")
                pat, op, n = m.group(1), m.group(2), int(m.group(3))
                if "_reqw_" + pat not in self.ctx.vars:
                    raise StepFailed(f"no watch_requests step for {pat!r} before this one")
                self.p.page.wait_for_timeout(1500)            # let in-flight requests land
                got = len(self.ctx.vars["_req_" + pat])
                ok = {"==": got == n, "<=": got <= n, ">=": got >= n, "<": got < n, ">": got > n}[op]
                if not ok:
                    raise StepFailed(f"{got} requests to {pat!r}, expected {op} {n}")

            case "use_company":
                # First step of a trade script: run inside that trade's test company (or a named one).
                from framework import qa_company
                qa_company.switch(self.p.page, str(value or target))
                self.ctx.vars["_company"] = qa_company.current(self.p.page)
                if settings.ALLOW_DESTRUCTIVE and not step.get("no_baseline"):
                    from framework import test_env
                    test_env.restore_baseline(self.p, str(value or target), self.ctx.log)

            case "click_text":
                # A visible element with exactly this text (tab, link, menu item, button label)
                exact = step.get("exact", True)
                loc = self.p.page.get_by_text(str(value), exact=bool(exact))
                vis = [loc.nth(i) for i in range(min(loc.count(), 20)) if loc.nth(i).is_visible()]
                if not vis:
                    raise StepFailed(f"Nothing visible with text {value!r}")
                from framework import safety as _sf
                _sf.guarded_click(vis[int(step.get("nth", 0))], f"text:{value}",
                                  inside_modal=bool(step.get("inside_modal")))
                self.p.settle()

            case "assert_options":
                # target: a <select> (or a field that opens a list); value: "A | B | C" must all be offered
                want = [x.strip() for x in str(value).split("|") if x.strip()]
                el = self.p.find(target)
                got = el.evaluate("e => e.tagName === 'SELECT' ? [...e.options].map(o => o.text.trim()) : null")
                if got is None:
                    from framework import safety as _sf
                    _sf.guarded_click(el, f"options:{target}")
                    self.p.page.wait_for_timeout(800)
                    got = [t.strip() for t in self.p.page.locator(
                        "[role=option], .dropdown-item, li.ui-menu-item, .mat-option, ng-dropdown-panel .ng-option"
                    ).all_inner_texts() if t.strip()]
                    self.p.page.keyboard.press("Escape")
                missing = [w for w in want if not any(w.lower() == g.lower() for g in got)]
                if missing:
                    raise StepFailed(f"Options missing {missing}. Offered: {got[:40]}")

            case "assert_value":
                el = self.p.find(target)
                got = el.evaluate("e => e.tagName === 'SELECT' ? (e.options[e.selectedIndex]||{}).text || '' : (e.value ?? e.innerText ?? '')")
                if str(got).strip().lower() != str(value).strip().lower():
                    raise StepFailed(f"{target}: value is {str(got).strip()!r}, expected {value!r}")

            case "assert_enabled":
                if not self.p.find(target).is_enabled():
                    raise StepFailed(f"Should be enabled but is disabled: {target}")

            case "assert_disabled":
                if self.p.find(target).is_enabled():
                    raise StepFailed(f"Should be disabled but is enabled: {target}")

            case "open_screen":
                from framework.screens import open_screen
                if not open_screen(self.p, target):
                    # The side menu sometimes does not unfold on the first hover (animation, a popup that just
                    # closed). One more try after moving the mouse away, like a user would (TC_GARM_056 clean-up).
                    try:
                        self.p.page.mouse.move(900, 300)
                        self.p.page.wait_for_timeout(1200)
                    except Exception:  # noqa: BLE001
                        pass
                    if not open_screen(self.p, target):
                        raise StepFailed(f"Screen '{target}' khul nahi paya")

            # ---- Transaction form ke UNCHE STAR ke kaam ----
            #
            # Grid ke cell tab tak <input> bante hi nahi jab tak focus na ho.
            # Isliye "fill sale.qty_cell 2" kabhi chalta hi nahi tha. Ye actions
            # POM ko bulate hain, jo wahi keyboard wala rasta leta hai jo asli
            # user leta hai. Tester ke liye bhi ye padhne me saaf hain.
            case "set_party":
                self._form().set_party(value)

            case "fill_header":
                # "Cash Account | patient=Ramesh | mr=Eshaanvi1"
                # SIRF wo field bharega jo is trade ke form me hain.
                parts = [x.strip() for x in str(value).split("|")]
                party = parts[0]
                extra = {}
                for kv in parts[1:]:
                    if "=" in kv:
                        k, v = [x.strip() for x in kv.split("=", 1)]
                        extra[{"patient": "patient_name",
                               "customer": "customer_name",
                               "doctor": "doctor_name"}.get(k, k)] = v
                res = self._form().fill_header(party, **extra)
                self.ctx.log.append(
                    f"      trade={res['trade']} | bhara: {', '.join(res['filled'])}"
                    f" | chhoda: {', '.join(res['skipped']) or 'kuch nahi'}")

            case "require_setting":
                # "mode_of_payment" ya "calculation_type=Inclusive"
                #
                # Ye test ka PRE-REQUISITE hai: setting theek na ho to pehle
                # theek ki jayegi, phir test aage badhega. Pehle hum aisa
                # test SKIP kar dete the -- imaandaar tha, par kaam aage
                # nahi badhta tha.
                from framework import control_room as _cr
                spec = str(value or target or "").strip()
                feat, _, want = spec.partition("=")
                res = _cr.ensure(self.p, feat.strip(), want.strip() or "Yes")
                self.ctx.log.append(
                    f"      setting {res['feature']}: {res['why']}"
                    + (f" ({res.get('from')} -> {res['value']})"
                       if res["changed"] else ""))

            case "expect_trade":
                # Ye FAIL nahi, SKIP hai.
                #
                # Pharma ka test general-trade company pe chal hi nahi sakta --
                # wahan patient/doctor/batch hote hi nahi. Use laal dikhana
                # jhooth hoga: app bilkul theek hai, test us company ke liye
                # hai hi nahi.
                prof = self._form().profile()
                if prof.trade != str(value).strip():
                    raise TradeMismatch(
                        f"Ye test '{value}' trade ke liye hai, par ye company "
                        f"'{prof.trade}' trade ki hai.\n"
                        f"  {prof.summary()}\n"
                        f"  Ye bug nahi hai -- test is company pe lagu hi nahi hota."
                    )

            case "expect_field":
                # "patient_name" hona chahiye
                if not self._form().profile().has(str(value).strip()):
                    raise StepFailed(
                        f"Form me '{value}' field nahi hai.\n"
                        f"  {self._form().profile().summary()}")

            case "expect_no_field":
                if self._form().profile().has(str(value).strip()):
                    raise StepFailed(f"Form me '{value}' field nahi hona chahiye tha")

            case "add_item":
                # "Item Name | qty | rate"  ya  "80000111 | 2"  (barcode)
                parts = [x.strip() for x in str(value).split("|")]
                if not parts or not parts[0]:
                    raise StepFailed("add_item ko chahiye: 'Item ya barcode | qty | rate'")
                qty = float(parts[1]) if len(parts) > 1 and parts[1] else 1
                rate = float(parts[2]) if len(parts) > 2 and parts[2] else None
                disc = float(parts[3]) if len(parts) > 3 and parts[3] else None
                self._sale().add_item(parts[0], qty, rate, discount=disc)

            case "add_barcode":
                # "80000111 | 2 | 100"  -- naam se zyada bharosemand
                parts = [x.strip() for x in str(value).split("|")]
                qty = float(parts[1]) if len(parts) > 1 and parts[1] else 1
                rate = float(parts[2]) if len(parts) > 2 and parts[2] else None
                self._sale().add_by_barcode(parts[0], qty, rate)

            case "retail_bill":
                # "Item | qty | rate | batch"  -- jo hissa is trade me hai
                # wahi bharega, baaki apne aap chhod dega.
                parts = [x.strip() for x in str(value).split("|")]
                res = self._retail().bill(
                    item=parts[0],
                    qty=float(parts[1]) if len(parts) > 1 and parts[1] else 1,
                    rate=float(parts[2]) if len(parts) > 2 and parts[2] else None,
                    batch=parts[3] if len(parts) > 3 and parts[3] else None,
                    patient=step.get("patient"), doctor=step.get("doctor"),
                    save=bool(step.get("save")))
                for line in res["steps"]:
                    self.ctx.log.append(f"      {line}")

            case "expect_party_state":
                # "prefilled" / "empty" / "not_asked"
                got = self._retail().party_state()
                if got["state"] != str(value).strip():
                    # Ye FAIL nahi, SKIP hai.
                    # Doosri setting par party ka poocha jana SAHI vyavhaar
                    # hai -- use laal dikhana jhooth hoga.
                    raise TradeMismatch(
                        f"Ye test party ke '{value}' hone par lagu hai, par "
                        f"abhi wo '{got['state']}' hai.\n"
                        f"  {got['why']}\n"
                        f"  Control Room: 'Ask Party in Retail Billing' = "
                        f"{got['setting']}\n"
                        f"  Ye bug NAHI hai -- test is setting par lagu hi "
                        f"nahi hota.")

            case "ensure_party":
                res = self._retail().ensure_party(value or "Cash Account")
                self.ctx.log.append(f"      {res['action']} -- {res['why']}")

            case "pick_batch":
                self._sale().pick_batch(str(value).strip())

            case "expect_column":
                cols = self._sale().grid_columns()
                if str(value).strip() not in cols:
                    raise StepFailed(
                        f"Grid me '{value}' column nahi hai. Ye hain: {cols}")

            case "set_bill_discount":
                self._form().set_bill_discount(float(value))

            case "expect_total":
                # value: "cgst=5, sgst=5" ya "invoice_value=210"
                self._check_totals(value)

            case "expect_lines":
                got = self._sale().line_count()
                if int(got) != int(value):
                    raise StepFailed(f"Grid me {value} line honi thi, {got} hain")

            case "close_form":
                self._form().close()

            case "save_form":
                self._form().save()
            case "click":
                if step.get("inside_modal"):            # a button inside the open popup: do not close it first
                    from framework import safety as _sf
                    _sf.guarded_click(self.p.find(target, want="click"), target, inside_modal=True)
                    self.p.settle()
                else:
                    self.p.click(target)
            case "fill":
                if step.get("inside_modal"):            # a field inside the open popup: do not close it first
                    from framework import safety as _sf
                    el = self.p.find(target, want="type")
                    _sf.guarded_click(el, f"fill:{target}", inside_modal=True)
                    _sf.safe_clear(el, self.p.page)
                    if value:
                        el.type(str(value), delay=15)
                    self.p.settle()
                else:
                    self.p.fill(target, value)
            case "select":
                self.p.select(target, value)
            case "press":
                if target:
                    self.p.press(target, value)
                else:                                   # Test Studio: a key with no target
                    k = str(value)
                    if re.match(r"(?i)^(alt|control|ctrl|shift|meta)\+", k):
                        self._close_side_popups()
                    if re.match(r"(?i)^(alt|control|ctrl|shift|meta)\+|^f\d{1,2}$", k):
                        # After login / a company switch the app leaves the cursor in the header search box
                        # (#controlRoomSearchField). A shortcut pressed there opens the screen but the cursor
                        # stays in the search box, so the next Enter/typing goes nowhere (TC_CSAL_070 in Studio).
                        try:
                            self.p.page.evaluate("() => { const e = document.activeElement; "
                                                 "if (e && e.id === 'controlRoomSearchField') e.blur(); }")
                        except Exception:  # noqa: BLE001
                            pass
                    if k.lower() == "enter" and self._window_already_open(step):
                        self.ctx.log.append("      the window this Enter should open is already open (the click "
                                            "opened it): Enter not pressed, it would pick the first row")
                        return
                    if k.lower() == "enter":
                        self._wait_lookup_rows()
                    self.p.page.keyboard.press(k)
                    if k.lower() == "enter":
                        self._enter_until_window(step)
            case "bulk_sale_bills":
                # Test Studio: "create 500 sale bills with 50 items each". "bills | items per bill".
                from ui_studio import bulk
                n, _, per = [x.strip() for x in str(value).partition("|")]
                bulk.run(self.p, self._sale, int(n), int(per or 5), self.ctx.log)
            case "wait_text":
                alts = self._screen_marker_alternatives(str(value))
                if alts:
                    self._wait_any_text(alts, step.get("timeout_ms"))
                else:
                    self.p.wait_for_text(value, step.get("timeout_ms"))
            case "assert_text":
                if not self.p.page_has_text(value):
                    raise StepFailed(f"Expected text not on page: {value!r}")
            case "assert_no_text":
                if self.p.page_has_text(value):
                    raise StepFailed(f"Unexpected text present: {value!r}")
            case "assert_visible":
                if not self.p.is_visible(target) and not (self._reveal_ag_column(target)
                                                          and self.p.is_visible(target)):
                    raise StepFailed(f"Not visible: {target}")
            case "assert_not_visible":
                if self.p.is_visible(target, timeout_ms=2000):
                    raise StepFailed(f"Should be hidden but visible: {target}")
            case "sleep":
                time.sleep(float(value or 1))
            case "screenshot":
                self.p.screenshot(str(value or "shot"))
                import os as _os
                if _os.environ.get("MB_NO_CAPTURE"):        # verification sessions: keep evidence with the cases
                    from pathlib import Path as _P
                    d = _P(__file__).resolve().parents[1] / "artifacts" / "verify" / "shots"
                    d.mkdir(parents=True, exist_ok=True)
                    try:
                        self.p.page.screenshot(path=str(d / f"{int(time.time())}_{str(value or 'shot')[:60]}.png"),
                                               timeout=8000)
                    except Exception:  # noqa: BLE001
                        pass
            case "note":
                pass
            case _:
                raise StepFailed(f"Unknown action: {action!r}")
