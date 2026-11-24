"""
Rewrite cases that checked a FIXED stock figure ("Stock before: 123.00", then "Stock after: 119.00").

Other tests sell and buy the same QA items, so the absolute stock drifts and the case failed although the app was
right (TC_CPUR_154 expected 123, TC_SALE_048 491, TC_SALE_067 100). What the case really checks is the CHANGE:
the bill took 4, so after = before - 4. Same intent, new form:

  * the first stock check of an item/column becomes   read_value  -> {ctx.stock_<k>_0}
  * every later check of the SAME cell (same locator, other number) becomes
        read_value -> {ctx.stock_<k>_<i>}   +   assert_same "{ctx.stock_<k>_0} - 4 = {ctx.stock_<k>_<i>}"
    (the difference the case author wrote: 123 -> 119 is "- 4"; 100 -> 99 -> 100 is "- 1" then "+ 0").
  * comparisons (< 100, > 0) and one-off figures that are not stock are left alone.

    python -m tools.rewrite_fixed_stock            # show what would change
    python -m tools.rewrite_fixed_stock --apply    # write the case files
    python -m tools.rewrite_fixed_stock --ids TC_SALE_048,TC_CPUR_154 [--apply]
"""
from __future__ import annotations

import argparse
import copy
import glob
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
STOCK_COLS = ("Opening", "OpeningQty", "balanceQty")
NUM = r"-?\d[\d,]*(?:\.\d+)?"
# [normalize-space()="491.00"]  |  [normalize-space(translate(.," "," "))="491.00"]  |  and number(normalize-space())=100
EQ_PRED = re.compile(r'\[normalize-space\((?:translate\([^)]*\))?\)="(' + NUM + r')"\]')
NUM_AND = re.compile(r'\s+and\s+number\(normalize-space\(\)\)\s*=\s*(' + NUM + r')(?=\])')
NUM_PRED = re.compile(r'\[number\(normalize-space\(\)\)\s*=\s*(' + NUM + r')\]')
GENERIC_COL = re.compile(r'//div\[@col-id\]\[normalize-space\(\)="(' + NUM + r')"\]')
# [@col-id="Opening" and contains(.,"99.00")]  |  [@col-id="Opening" and normalize-space()="77.00"]
AND_TEXT = re.compile(r'(?<="Opening")\s+and\s+(?:contains\(\.,\s*|normalize-space\(\)\s*=\s*)"(' + NUM + r')"\)?(?=\])')
# a row's  //div[contains(.,"47.00")]  with a "stock" note: the List's stock column is "Opening"
ANY_DIV = re.compile(r'//div\[contains\(\.,\s*"(' + NUM + r')"\)\]$')


def _num(s: str) -> float:
    return float(s.replace(",", ""))


def _stock_figure(step: dict) -> tuple[str, float] | None:
    """(locator without the number, the number) when the step asserts a fixed stock figure."""
    if step.get("action") != "assert_visible":
        return None
    t = str(step.get("target") or "")
    note = str(step.get("note") or "")
    if "ngb-modal-window" in t and (m := GENERIC_COL.search(t)) and re.search(r"stock", note, re.I):
        # Select Item list: its stock column is "Opening" (seen in the app's grid, TC_SALE_048 trace)
        return t[:m.start()] + '//div[@col-id="Opening"]' + t[m.end():], _num(m.group(1))
    if re.search(r"stock", note, re.I) and (m := ANY_DIV.search(t)):
        return t[:m.start()] + '//div[@col-id="Opening"]', _num(m.group(1))
    if not any(f'col-id="{c}"' in t for c in STOCK_COLS):
        return None
    for rx in (NUM_AND, AND_TEXT, NUM_PRED, EQ_PRED):
        m = rx.search(t)
        if m:
            return t[:m.start()] + t[m.end():], _num(m.group(1))
    return None


def _fmt(d: float) -> str:
    d = round(d, 3)
    s = f"{abs(d):g}"
    return f"- {s}" if d < 0 else f"+ {s}"


def rewrite(case: dict) -> tuple[dict, int]:
    c = copy.deepcopy(case)
    groups: dict[str, tuple[int, float]] = {}      # locator -> (group no, first figure)
    out, changed = [], 0
    seen: dict[str, int] = {}
    for s in c["steps"]:
        if hit := _stock_figure(s):
            seen[hit[0]] = seen.get(hit[0], 0) + 1
    for s in c["steps"]:
        hit = _stock_figure(s)
        if not hit or seen[hit[0]] < 2:      # a lone figure ("stock 0.00") is the point of the case: keep it
            out.append(s)
            continue
        loc, n = hit
        note = str(s.get("note") or "")
        if loc not in groups:
            groups[loc] = (len(groups), n)
            k = groups[loc][0]
            out.append({"action": "read_value", "target": loc, "save_as": f"stock_{k}_0",
                        "note": f"Read the stock now (was: {note or f'stock {n:g}'}; the figure drifts as other tests run)"})
        else:
            k, first = groups[loc]
            i = sum(1 for x in out if str(x.get("save_as", "")).startswith(f"stock_{k}_"))
            name = f"stock_{k}_{i}"
            out.append({"action": "read_value", "target": loc, "save_as": name, "note": f"Read the stock again ({note})"})
            out.append({"action": "assert_same", "value": f"{{ctx.stock_{k}_0}} {_fmt(n - first)} = {{ctx.{name}}}",
                        "note": f"Stock moved by {n - first:+g} as the case expects (was: {note})"})
        changed += 1
    if changed:
        c["steps"] = out
        c.setdefault("preconditions", []).append(
            "Rewritten 2026-11-23: fixed stock figures replaced by read value + the expected change "
            "(other tests keep selling/buying the same QA items).")
    return c, changed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--ids", default="")
    a = ap.parse_args()
    only = {x.strip() for x in a.ids.split(",") if x.strip()}
    total = 0
    for f in sorted(glob.glob(str(ROOT / "testcases" / "**" / "*.yaml"), recursive=True)):
        try:
            data = yaml.safe_load(open(f, encoding="utf-8")) or []
        except Exception:  # noqa: BLE001
            continue
        if not isinstance(data, list):
            continue
        dirty = False
        for k, c in enumerate(data):
            if not isinstance(c, dict) or "steps" not in c or (only and c.get("id") not in only):
                continue
            new, n = rewrite(c)
            if not n:
                continue
            total += 1
            print(f"\n== {c['id']} ({Path(f).name}): {n} stock check(s)")
            for s in new["steps"]:
                if s.get("action") == "assert_same" or str(s.get("save_as", "")).startswith("stock_"):
                    print("   ", s["action"], s.get("save_as") or s.get("value"), "|", str(s.get("note"))[:90])
            data[k] = new
            dirty = True
        if dirty and a.apply:
            Path(f).write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=110), encoding="utf-8")
    print(f"\n{total} case(s)", "written" if a.apply else "(dry run: add --apply to write)")


if __name__ == "__main__":
    sys.exit(main())
