"""
Shared test data of the QA companies: notice when a test's data is used up and put it back.

The QA companies are shared by every test. A test that sells a variant leaves less stock for the next one;
after enough runs a test that only *reads* that variant finds nothing (TC_GARM_072, TC_GARM_056: barcode 11110001
went to -8). That is the environment, not the app.

config/qa_data.json lists, per QA company, the records tests rely on and how much stock each should have.
When a step fails because one of them is missing (StepRunner raises EnvironmentNotReady with `.missing`), the
runner calls repair(): stock is topped up to the target with a Manual Sale Return (the only way to add stock to an
existing variant barcode: a purchase refuses it with "Duplicate Barcode Not Allowed"), and the test is run again
from the start, once. Data with no recipe stays "Blocked - environment" with the reason.

    python -m tools.qa_data --check            # balance of every listed record, change nothing
    python -m tools.qa_data --fill             # top up what is below its minimum (QA companies only)

Writes happen only in QA test companies (framework.qa_company guard) and only when writes are allowed.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parents[1] / "config" / "qa_data.json"


def load(company: str | None = None) -> dict:
    try:
        data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except FileNotFoundError:
        data = {}
    data = {k: v for k, v in data.items() if not k.startswith("_")}
    return data.get(company, []) if company else data


# Trades whose items carry batches: a return or purchase would add a NEW batch and change which batch the
# tests get first (FIFO / expiry), so their stock is never topped up automatically.
BATCH_TRADES = ("chemist", "pharma")


def entry_for(company: str, name: str) -> dict | None:
    name = str(name).strip()
    for e in load(company):
        if name in (str(e.get("name")), str(e.get("barcode") or "")):
            return e
    # Any other shared QA_ item of a non-batch trade: below 10 in stock it is topped up to 20. Items whose
    # name says the test needs them empty (QA_Item_NoStock, QA_Item_MinLevel) are never filled.
    if (name.startswith("QA_Item_") and not any(t in company.lower() for t in BATCH_TRADES)
            and not re.search(r"nostock|minlevel|negative|hidden", name, re.I)):
        return {"name": name, "kind": "item", "item": name, "min": 10, "target": 20}
    return None


# ---------------------------------------------------------------- UI helpers

def _runner(bp, log):
    from framework.step_runner import RunContext, StepRunner
    r = StepRunner(bp, RunContext())
    r.auto_undo = False
    r._repairing = True              # never repair-and-retry inside a repair
    r.ctx.log = log if log is not None else r.ctx.log
    return r


def _leave(bp, log):
    """Back to the dashboard from whatever the failed test left open (unsaved forms are dropped)."""
    page = bp.page
    from framework import safety
    for _ in range(3):
        try:
            page.keyboard.press("Escape")
            page.wait_for_timeout(500)
        except Exception:  # noqa: BLE001
            pass
    try:
        page.keyboard.press("Alt+h")
        page.wait_for_timeout(1500)
        yes = page.locator("#btnYes")
        if yes.count() and yes.first.is_visible():
            safety.guarded_click(yes.first, "leave.yes", inside_modal=True)
            page.wait_for_timeout(1500)
    except Exception:  # noqa: BLE001
        pass
    try:
        safety.force_close_modal(page)
    except Exception:  # noqa: BLE001
        pass


# first entry cell of the bill grid: Barcode where the trade has one, else Product
_FIRST_CELL = ('xpath=(//div[@row-index="0"]//div[@col-id="tmp_barcode"] | '
               '//div[@row-index="0"]//div[@col-id="itemLinkID"])[1]')

_ROW = ('xpath=//ngb-modal-window//div[@role="row"][.//div[@col-id="balanceQty"]]'
        '[.//div[@col-id="BarCode" and normalize-space()="{bc}"]]//div[@col-id="balanceQty"]')


def _num(txt) -> float | None:
    m = re.search(r"-?\s*\d[\d,]*(\.\d+)?", str(txt or ""))
    return float(m.group(0).replace(" ", "").replace(",", "")) if m else None


def variant_balance(bp, item: str, barcode: str, log=None) -> float | None:
    """Balance of one variant barcode as the sale bill's variant list shows it (None: not offered at all,
    i.e. 0 or below)."""
    _leave(bp, log)
    r = _runner(bp, log)
    r.run([
        {"action": "open_screen", "target": "sale_bill"},
        {"action": "wait_text", "value": "Invoice Value"},
        {"action": "sleep", "value": 3},
        {"action": "click", "target": _FIRST_CELL},
        {"action": "press", "value": "Enter"},
        {"action": "wait_text", "value": "Total no of items"},
        {"action": "sleep", "value": 1.5},
        {"action": "fill", "target": "input#searchItems", "value": item, "inside_modal": True},
        {"action": "sleep", "value": 2},
        {"action": "press", "value": "Enter"},
        {"action": "wait_text", "value": "Show All Parameter"},
        {"action": "sleep", "value": 2},
    ])
    page = bp.page
    loc = page.locator(_ROW.format(bc=barcode))
    bal = None
    try:
        if loc.count():
            bal = _num(loc.first.inner_text(timeout=3000))
    except Exception:  # noqa: BLE001
        bal = None
    _leave(bp, log)
    return bal


def item_stock(bp, item: str, log=None) -> float | None:
    """Stock of an item in the Item List (Main Store). None: no item with exactly this name."""
    from pages.item_page import ItemPage
    _leave(bp, log)
    ip = ItemPage.open(bp)
    ip.search(item)
    bp.page.wait_for_timeout(2000)
    rows = ip.rows()
    _leave(bp, log)
    for r in rows:
        if r and r[0].strip() == item:
            # Description | Packing | Company | Stock | Unit | Sale Rate
            nums = [x for x in r[1:] if re.fullmatch(r"-?[\d,]+\.\d+", x.strip())]
            return _num(nums[0]) if nums else None
    return None


def _focus_id(page) -> str:
    try:
        return page.evaluate("() => (document.activeElement && document.activeElement.id) || ''")
    except Exception:  # noqa: BLE001
        return ""


def _type_qty(page, q: str) -> None:
    page.keyboard.press("Control+a")
    page.keyboard.type(q)
    page.keyboard.press("Enter")
    page.wait_for_timeout(1200)


def return_stock(bp, qty: float, setting: str = "341", barcode: str | None = None, item: str | None = None,
                 log=None) -> None:
    """Add `qty` to a variant barcode or a plain item with a Manual Sale Return on Cash Account (no bill
    reference). Works on both grid layouts: Barcode column first (garment...) or Product first (billing...)."""
    from framework import control_room as cr, qa_company
    from pages.transaction_form import TransactionForm
    page = bp.page
    qa_company.require_test_company(page, "add stock")
    _leave(bp, log)
    before = cr.set_setting(bp, setting, "Yes")             # Manual Return Allow In Sale
    q = str(int(qty)) if float(qty).is_integer() else str(qty)
    try:
        _runner(bp, log).run([
            {"action": "open_screen", "target": "sale_return"},
            {"action": "wait_text", "value": "Returns of Bills"},
            {"action": "sleep", "value": 2},
            {"action": "select", "target": "#returnOfBill", "value": "Manual"},
            {"action": "sleep", "value": 1},
            {"action": "click_text", "value": "Ok", "inside_modal": True},
            {"action": "sleep", "value": 2},
            {"action": "click", "target": _FIRST_CELL},
            {"action": "sleep", "value": 1},
        ])
        on_barcode = _focus_id(page).startswith("txt-tmp_barcode")
        if barcode and on_barcode:
            page.keyboard.type(str(barcode), delay=20)
            page.keyboard.press("Enter")
            page.wait_for_timeout(3000)
        else:
            if on_barcode:                                   # empty Barcode cell + Enter opens the item list
                page.keyboard.press("Enter")
                page.wait_for_timeout(2500)
                page.locator("input#searchItems").first.fill(item or str(barcode))
            else:                                            # typing in Product opens the list with the text
                page.keyboard.type(item or str(barcode), delay=30)
            page.wait_for_timeout(2500)
            page.keyboard.press("Enter")
            page.wait_for_timeout(2500)
        # batch items (chemist, pharma): a Select Batch window opens: take the first batch (as a user does)
        for _ in range(2):
            if page.get_by_text("Select Batch", exact=False).count() and                     page.get_by_text("Select Batch", exact=False).first.is_visible():
                page.keyboard.press("Enter")
                page.wait_for_timeout(2000)
        line = page.locator('xpath=//div[@row-index="0"]//div[@col-id="itemLinkID"]').first
        if not (line.count() and (line.inner_text() or "").strip()):
            raise RuntimeError(f"the return has no line for {barcode or item}")
        fid = _focus_id(page)
        if fid.startswith("txt-quantity"):                   # plain item: cursor is in Qty
            _type_qty(page, q)
        else:                                                # variant: the line came in with qty 1
            page.locator('xpath=//div[@row-index="0"]//div[@col-id="quantity"]').first.dblclick()
            page.wait_for_timeout(800)
            if _focus_id(page).startswith("txt-quantity"):
                page.keyboard.press("Enter")                 # a variant item opens its window on Enter
                page.wait_for_timeout(1500)
            cell = page.locator('xpath=//ngb-modal-window//div[@row-index="0"]//div[@col-id="qty"]')
            if cell.count() and cell.first.is_visible():
                cell.first.dblclick()
                page.wait_for_timeout(800)
                _type_qty(page, q)
                page.keyboard.press("F10")                   # commit the variant window
                page.wait_for_timeout(2000)
            else:
                _type_qty(page, q)
        got = page.locator('xpath=//div[@row-index="0"]//div[@col-id="quantity"]').first.inner_text()
        if _num(got) != float(qty):
            raise RuntimeError(f"return qty shows {got!r}, wanted {q}")
        TransactionForm(bp).save()
        if log is not None:
            log.append(f"      stock: Manual Sale Return {barcode or item} x {q} saved")
    finally:
        _leave(bp, log)
        if before.get("changed"):
            cr.set_setting(bp, setting, str(before.get("from")))


def return_variant(bp, barcode: str, qty: float, setting: str = "341", log=None) -> None:
    return_stock(bp, qty, setting, barcode=barcode, log=log)


# ---------------------------------------------------------------- check / repair

def check(bp, company: str, e: dict, log=None) -> dict:
    """{'name','balance','min','ok'} for one entry."""
    if e.get("kind") in ("variant", "item"):
        bal = _balance(bp, e, log)
        return {"name": e["name"], "balance": bal, "min": e.get("min", 1),
                "ok": bal is not None and bal >= float(e.get("min", 1))}
    return {"name": e["name"], "balance": None, "min": e.get("min"), "ok": None}


def _balance(bp, e: dict, log=None) -> float | None:
    if e.get("kind") == "variant":
        return variant_balance(bp, e["item"], e["barcode"], log)
    return item_stock(bp, e["item"], log)


def top_up(bp, company: str, e: dict, log=None) -> bool:
    """Bring one entry up to its target. True when it is at or above its minimum afterwards."""
    if e.get("kind") not in ("variant", "item"):
        return False
    if e.get("kind") == "item":
        bal = item_stock(bp, e["item"], log)
        if bal is None:
            if log is not None:
                log.append(f"      {e['item']} is not in the item list: it must be created (no recipe)")
            return False
        if bal >= float(e.get("min", 1)):
            return True
        add = float(e.get("target", e.get("min", 1))) - bal
        if log is not None:
            log.append(f"      stock: {e['item']} balance {bal:g} -> adding {add:g}")
        return_stock(bp, add, e.get("return_setting", "341"), item=e["item"], log=log)
        bal = item_stock(bp, e["item"], log)
        return bal is not None and bal >= float(e.get("min", 1))
    target = float(e.get("target", e.get("min", 1)))
    for _ in range(3):
        bal = variant_balance(bp, e["item"], e["barcode"], log)
        if bal is not None and bal >= float(e.get("min", 1)):
            if log is not None:
                log.append(f"      stock: {e['name']} balance {bal:g} (ok)")
            return True
        # Not offered = 0 or below; how far below is not shown, so add the target and look again.
        add = target - bal if bal is not None else target
        if log is not None:
            log.append(f"      stock: {e['name']} balance {('%g' % bal) if bal is not None else '0 or below'}"
                       f" -> adding {add:g}")
        return_stock(bp, add, e.get("return_setting", "341"), barcode=e["barcode"], log=log)
    return False


def repair(bp, names, log=None) -> bool:
    """Put back the named records in the open QA company. True only when every one of them has a recipe and
    is back; then the caller runs the test again."""
    from config.settings import settings
    from framework import qa_company
    if not settings.ALLOW_DESTRUCTIVE:
        return False
    company = qa_company.current(bp.page)
    if not qa_company.is_test_company(company):
        return False
    entries = [entry_for(company, n) for n in names]
    if not entries or any(e is None for e in entries):
        if log is not None:
            log.append(f"      no recipe in config/qa_data.json for {', '.join(n for n, e in zip(names, entries) if e is None)}"
                       f" in {company}")
        return False
    ok = True
    for e in entries:
        try:
            ok = top_up(bp, company, e, log) and ok
        except Exception as ex:  # noqa: BLE001
            if log is not None:
                log.append(f"      could not put back {e['name']}: {str(ex)[:200]}")
            ok = False
    return ok
