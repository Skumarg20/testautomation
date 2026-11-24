"""
Rewrite the GST report cases that checked a fixed running total (approved by the user, 23-Nov-2026).

They asserted e.g. "CGST Input balance 700.00 Dr" or "3B ITC CGST 980.00". Other tests keep posting purchases
in the same QA company, so those totals grow and the case failed although the app was right.

New form, same intent:
  * the report month is the month the case was verified in (a closed period: its figures stop changing);
  * figures are READ (read_value) instead of compared with a fixed number;
  * the case then checks what must always hold: GSTR-2 tax = GSTR-3B eligible ITC for that month,
    CGST = SGST (local purchases), Net ITC = eligible ITC, ledger CGST Input = SGST Input;
  * "report is not blank" cases check that the amount is not 0.00.

    python -m tools.rewrite_running_totals            # show what would change
    python -m tools.rewrite_running_totals --apply    # write the case files (yaml round-trips unchanged)
"""
from __future__ import annotations

import argparse
import calendar
import copy
import datetime as dt
import glob
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
RECONCILE = {"TC_GST_036", "TC_PUR_084", "TC_CACC_078", "TC_CACC_206"}
NOT_BLANK = {"TC_CACC_076", "TC_CACC_080"}
GSTR2_FROM = "TC_PUR_084"          # its GSTR-2 block is copied into cases of the same company that lack one

AMOUNT_PRED = re.compile(r'\[normalize-space\((?:translate\([^)]*\))?\)="[^"]*"\]|\[normalize-space\(\)="[^"]*"\]')
LEDGER = re.compile(r'col-id="LedgerName"\]\[normalize-space\(\)="(CGST|SGST|IGST)\s+Input"\]')
G2COL = re.compile(r'col-id="(TotalTax(?:CentralTax|StateUtTax|IntegratedTax)|NoofInvoices)"')
B3ROW = re.compile(r'contains\(@title,"(All other ITC|Net ITC available|Outward taxable supplies[^"]*)"\)')
B3COL = re.compile(r'col-id="(CentralTax|StateUtTax|IntegratedTax|CentralTaxAmt)"')
SHORT = {"TotalTaxCentralTax": "cgst", "TotalTaxStateUtTax": "sgst", "TotalTaxIntegratedTax": "igst",
         "NoofInvoices": "count", "CentralTax": "cgst", "StateUtTax": "sgst", "IntegratedTax": "igst",
         "CentralTaxAmt": "out_cgst"}


def _month(case: dict) -> tuple[str, str, str]:
    d = dt.date.fromisoformat(str((case.get("verification") or {}).get("date") or "2026-11-18")[:10])
    last = calendar.monthrange(d.year, d.month)[1]
    return d.strftime("%b"), d.replace(day=1).strftime("%d-%m-%Y"), d.replace(day=last).strftime("%d-%m-%Y")


def _name(target: str) -> str | None:
    if m := LEDGER.search(target):
        return f"led_{m.group(1).lower()}"
    if "Particulars" in target and (m := G2COL.search(target)):
        return f"g2_{SHORT[m.group(1)]}"
    if (r := B3ROW.search(target)) and (m := B3COL.search(target)):
        row = {"All other ITC": "b3", "Net ITC available": "b3net"}.get(r.group(1), "b3out")
        return f"{row}_{SHORT[m.group(1)]}"
    return None


def rewrite(case: dict, gstr2_block: list[dict] | None) -> dict:
    c = copy.deepcopy(case)
    mon, first, last = _month(c)
    out, read = [], []
    has_g2 = any(s.get("action") == "click_text" and s.get("value") == "GSTR-2" for s in c["steps"])
    for s in c["steps"]:
        s = dict(s)
        t = str(s.get("target") or "")
        if s.get("action") == "select" and s.get("target") == "#filterType":
            s["value"] = mon
            s["note"] = f"Month {mon} (the verified month: a closed period, its figures no longer change)"
        if s.get("action") == "fill" and s.get("target") in ("input#fromDateFilter", "input#toDateFilter"):
            s["value"] = first if "from" in s["target"] else last
            s["fixed_date"] = True
            s["note"] = f"Period: the whole verified month {first}..{last}"
        if s.get("action") == "click" and s.get("note") == "Period = today":
            s["note"] = "Period = the verified month"
        if s.get("action") == "assert_visible" and AMOUNT_PRED.search(t) and (nm := _name(t)):
            if c["id"] in NOT_BLANK:
                s["target"] = AMOUNT_PRED.sub('[normalize-space()!="" and normalize-space()!="0.00"]', t, count=1)
                s["note"] = f"{s.get('note', '')} -> amount shown and not 0.00 (the total itself grows as tests run)".strip()
            else:
                s = {"action": "read_value", "target": AMOUNT_PRED.sub("", t, count=1), "save_as": nm,
                     "note": f"Read {nm} (was: {s.get('note', '')})"}
                read.append(nm)
        if s.get("action") == "screenshot" and c["id"] in RECONCILE and not has_g2 and gstr2_block:
            for g in gstr2_block:
                g = dict(g)
                if g.get("action") == "read_value":
                    read.append(g["save_as"])
                out.append(g)
            has_g2 = True
        out.append(s)
    if c["id"] in RECONCILE:                     # the checks go right after the last figure is read
        last = max(k for k, s in enumerate(out) if s.get("action") == "read_value")
        out[last + 1:last + 1] = _checks(read)
    c["steps"] = out
    c.setdefault("preconditions", []).append(
        "Rewritten 2026-11-23: fixed running totals replaced by read values + checks that always hold "
        "(GSTR-2 = GSTR-3B for the verified month, CGST = SGST); other tests keep adding purchases.")
    return c


def _checks(read: list[str]) -> list[dict]:
    have = set(read)
    pairs = [("g2_cgst", "b3_cgst", "GSTR-2 CGST = GSTR-3B eligible ITC CGST"),
             ("g2_igst", "b3_igst", "GSTR-2 IGST = GSTR-3B eligible ITC IGST"),
             ("b3_cgst", "b3_sgst", "3B eligible ITC: CGST = SGST"),
             ("b3net_cgst", "b3_cgst", "3B Net ITC CGST = eligible ITC CGST (no reversal)"),
             ("led_cgst", "led_sgst", "Ledger CGST Input = SGST Input")]
    return [{"action": "assert_same", "value": f"{{ctx.{a}}} = {{ctx.{b}}}", "note": n}
            for a, b, n in pairs if a in have and b in have]


def _gstr2_block(case: dict) -> list[dict]:
    """GSTR-2 steps (open .. reads) of the donor case, already rewritten."""
    st = rewrite(case, None)["steps"]
    g = next(k for k, s in enumerate(st) if s.get("action") == "click_text" and s.get("value") == "GSTR-2")
    i = max(k for k in range(g) if st[k].get("action") == "press" and st[k].get("value") == "Alt+I")
    j = max(k for k, s in enumerate(st) if s.get("action") == "read_value" and s["save_as"].startswith("g2_"))
    return st[i:j + 1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    files = {}
    donor = None
    for f in glob.glob(str(ROOT / "testcases" / "**" / "*.yaml"), recursive=True):
        data = yaml.safe_load(open(f, encoding="utf-8")) or []
        for c in data:
            if c.get("id") == GSTR2_FROM:
                donor = c
        if any(c.get("id") in RECONCILE | NOT_BLANK for c in data):
            files[f] = data
    block = _gstr2_block(donor)
    for f, data in files.items():
        for k, c in enumerate(data):
            if c.get("id") not in RECONCILE | NOT_BLANK:
                continue
            same_co = c["steps"][0].get("value") == donor["steps"][0].get("value")
            new = rewrite(c, block if same_co else None)
            print(f"\n== {c['id']} ({Path(f).name})")
            for s in new["steps"]:
                if s.get("action") in ("read_value", "assert_same") or "not 0.00" in str(s.get("note")) \
                        or s.get("fixed_date") or s.get("target") == "#filterType":
                    print("   ", s.get("action"), s.get("save_as") or s.get("value") or "", "|", str(s.get("note"))[:80])
            data[k] = new
        if a.apply:
            Path(f).write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=110), encoding="utf-8")
    print("\nwritten" if a.apply else "\n(dry run: add --apply to write)")


if __name__ == "__main__":
    sys.exit(main())
