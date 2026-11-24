"""
Import the scenario packs of the ai-projects repo (margbooks-test-automation/e2e/scenarios/*.md)
as YAML test cases, one file per module, in testcases/library/.

    python -m framework.import_scenarios C:\\path\\to\\margbooks-test-automation\\e2e\\scenarios

The packs are Markdown: mostly tables with an "ID" column, some bullet lists ("- DB-01 text").
Column names differ from pack to pack, so columns are read by name, never by position.

Every imported case is a DRAFT: it has a title, the expected result and where it came from,
but no steps. Drafts are skipped (not failed, not passed) until someone records or writes the
steps in Test Studio. Re-running the import rewrites testcases/library/ completely; IDs stay
the same as long as the packs do not change order.
"""
from __future__ import annotations

import csv
import re
import sys
from collections import defaultdict
from pathlib import Path

import yaml

from config.settings import ROOT

OUT = ROOT / "testcases" / "library"

# pack file -> (module, ID prefix). Modules follow the MargBooks side menu.
PACKS: dict[str, tuple[str, str]] = {
    "auth.md": ("auth", "AUTH"),
    "password-reset-registration.md": ("auth", "AUTH"),
    "user-role-management.md": ("users", "USER"),
    "multi-tenant.md": ("company", "COMP"),
    "subscription-status.md": ("company", "COMP"),
    "dashboard.md": ("dashboard", "DASH"),
    "masters.md": ("masters", "MSTR"),
    "item-master-crud.md": ("masters", "MSTR"),
    "ledger-master-crud.md": ("masters", "MSTR"),
    "route-station-area-masters.md": ("masters", "MSTR"),
    "unit-uqc-hsn-rate-masters.md": ("masters", "MSTR"),
    "opening-balance-entry.md": ("masters", "MSTR"),
    "sales-invoice.md": ("sales", "SALE"),
    "chemist-sale-bill.md": ("sales", "SALE"),
    "manual-sale-purchase.md": ("sales", "SALE"),       # PC- rows go to purchase, see _module_for
    "purchase.md": ("purchase", "PUR"),
    "purchase-return-debit-note.md": ("purchase", "PUR"),
    "inventory.md": ("inventory", "INV"),
    "rack-warehouse-management.md": ("inventory", "INV"),
    "barcode-generation-scanning.md": ("inventory", "INV"),
    "document-catalogue.md": ("accounting", "ACC"),
    "cash-transfer-day-closure.md": ("accounting", "ACC"),
    "outstanding-advance.md": ("accounting", "ACC"),
    "bank-entry-reconciliation.md": ("banking", "BANK"),
    "gst-report.md": ("gst", "GST"),
    "e-invoice.md": ("gst", "GST"),
    "accounting-reports.md": ("reports", "RPT"),
    "ledger-report.md": ("reports", "RPT"),
    "crm-module.md": ("crm", "CRM"),
    "support-helpdesk.md": ("support", "SUP"),
    "email-sms-whatsapp-setup.md": ("utilities", "UTIL"),
    "notifications-export.md": ("utilities", "UTIL"),
    "template-designer.md": ("utilities", "UTIL"),
    "data-sync-offline.md": ("utilities", "UTIL"),
    "online-store.md": ("online_store", "OS"),
    "manufacturing-module.md": ("manufacturing", "MFG"),
    "abha-health-flows.md": ("abha", "ABHA"),
}

# A scenario ID: 1-3 letters, a dash, an optional letter, 1-3 digits (SI-01, OA-001, RW-R01, AU-02b, LD-01..03).
# Legend and reference lines look similar but are not cases: CODE-L, KB-SW, JIRA-30329, MB-036277, GSTR-1.
_ID = r"[A-Z]{1,3}-[A-Z]?\d{1,3}[a-z]?(?:\.\.\d{1,3})?"
ID_CELL = re.compile(rf"^{_ID}$")
BULLET = re.compile(rf"^\s*[-*]\s+({_ID})\s+(.+)$")
CITATION = re.compile(r"\s*\((?:#[0-9a-f]{6,}[^)]*|[A-Za-z_]+\.csv#[^)]*)\)")
WRITES = re.compile(r"\b(save|saved|create|creates|created|add|adds|delete|deletes|modify|modifies|edit|edits|"
                    r"cancel|convert|import|post|reconcile|close the day|transfer)\b", re.I)


def _clean(text: str) -> str:
    t = CITATION.sub("", text or "")
    t = t.replace("<br>", " / ").replace("`", "")
    return re.sub(r"\s+", " ", t).strip()


def _cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def _col(head: list[str], *names: str) -> int:
    for n in names:
        for i, h in enumerate(head):
            if h.lower().startswith(n):
                return i
    return -1


def read_pack(path: Path) -> list[dict]:
    """All rows of one pack: {"src", "title", "expected", "steps", "type", "source", "extra", "group"}."""
    rows: list[dict] = []
    head: list[str] | None = None
    group = ""
    for line in path.read_text(encoding="utf-8").split("\n"):
        if line.startswith("#"):
            group = line.lstrip("#").strip()
            head = None
            continue
        if line.startswith("|"):
            cells = _cells(line)
            if cells and cells[0].lower() == "id":
                head = [c.lower() for c in cells]
                continue
            if head is None or not cells or not ID_CELL.match(cells[0]):
                continue

            def get(*names, _c=cells, _h=head):
                i = _col(_h, *names)
                return _c[i] if 0 <= i < len(_c) else ""

            title = get("title")
            scen = get("scenario", "case", "description")
            if title and scen:
                title, scen = title, scen
            else:
                title, scen = (title or scen), ""
            exp = [get("expected result"), get("expected outstanding"), get("expected advance")]
            exp_names = ["", "Outstanding: ", "Advance: "]
            expected = [n + _clean(e) for n, e in zip(exp_names, exp) if _clean(e)]
            if not expected and get("expected"):
                expected = [_clean(get("expected"))]
            rows.append({"src": cells[0], "title": _clean(title), "detail": _clean(scen),
                         "steps": _clean(get("steps", "flow")), "type": get("type").lower(),
                         "prio": get("p1").upper(), "source": _clean(get("source")),
                         "extra": {k: _clean(get(k)) for k in ("needs", "status", "active", "class", "auto", "browser")
                                   if _col(head, k) >= 0 and _clean(get(k))},
                         "expected": expected, "group": group})
            continue
        head = None
        m = BULLET.match(line)
        if m:
            rows.append({"src": m.group(1), "title": _clean(m.group(2)), "detail": "", "steps": "", "type": "",
                         "prio": "", "source": "", "extra": {}, "expected": [], "group": group})
    # a pack sometimes lists the same ID twice (summary table + detail); keep the first
    seen, out = set(), []
    for r in rows:
        if r["src"] not in seen:
            seen.add(r["src"])
            out.append(r)
    return out


def _module_for(pack: str, src_id: str) -> tuple[str, str]:
    if pack == "manual-sale-purchase.md" and src_id.startswith("PC-"):
        return "purchase", "PUR"
    return PACKS[pack]


def _type_tag(t: str) -> str:
    for k in ("positive", "negative", "boundary", "edge", "security", "consistency"):
        if k in t:
            return k
    return ""


# Which trades (business types) a scenario applies to. Evidence only, never guessed:
#   - the pack or its "Needs" column says so (chemist-sale-bill, "chemist account", "any trade");
#   - sales-invoice.md was written on the garments company; the KB shows the ABHA button only for type 5;
#   - otherwise trade:all when the module's menu was seen in the live crawl of at least 3 trades
#     (2026-11-17 crawl: Sale, Purchase, Stock Management, Accounting Trans., Banking, Report, Master, CRM,
#     Utilities & Tools, Dashboard, Staff Register all appeared in 3-4 of the 5 trades crawled).
# Modules whose menu no crawl reached (online store, digital/ABHA, manufacturing, support) stay untagged.
_TRADE_PACKS = {"chemist-sale-bill.md": "trade:chemist", "abha-health-flows.md": "trade:chemist",
                "sales-invoice.md": "trade:garment"}
_SEEN_IN_ALL_TRADES = {"sales", "purchase", "inventory", "accounting", "banking", "gst", "reports", "masters",
                       "crm", "utilities", "dashboard", "users", "company", "auth"}


def _trade_tags(r: dict, pack: str, module: str) -> list[str]:
    needs = r["extra"].get("needs", "").lower()
    if pack in _TRADE_PACKS:
        return [_TRADE_PACKS[pack]]
    if "chemist account" in needs:
        return ["trade:chemist"]
    if "any trade" in needs or module in _SEEN_IN_ALL_TRADES:
        return ["trade:all"]
    return []


def _case(r: dict, pack: str, module: str, cid: str) -> dict:
    text = " ".join(x for x in (r["title"], r["detail"], r["steps"], " ".join(r["expected"]),
                                " ".join(r["extra"].values())) if x)
    title = r["title"] if len(r["title"]) <= 140 else r["title"][:137].rsplit(" ", 1)[0] + "..."
    pre = ["DRAFT — imported scenario, no steps yet. Record or write the steps in Test Studio."]
    pre.append(f"Source: ai-projects e2e/scenarios/{pack} {r['src']}" + (f" ({r['source']})" if r["source"] else ""))
    if r["group"] and not r["group"].lower().startswith(("scenario", "cases")):
        pre.append(f"Group: {r['group']}")
    if len(r["title"]) > 140:
        pre.append(f"Scenario: {r['title']}")
    if r["detail"]:
        pre.append(f"Scenario: {r['detail']}")
    if r["steps"]:
        pre.append(f"Manual steps: {r['steps']}")
    for k, v in r["extra"].items():
        pre.append(f"{k.capitalize()}: {v}")
    tags = ["imported"]
    if _type_tag(r["type"] or r["group"].lower()):
        tags.append(_type_tag(r["type"] or r["group"].lower()))
    if "UNVERIFIED" in text or "NEEDS DECISION" in text or "QUESTION" in text:
        tags.append("unverified")
    if "NOT COVERED" in text:
        tags.append("not_covered")
    tags += _trade_tags(r, pack, module)
    prio = "p1" if r["prio"] == "P1" else ("p3" if "not_covered" in tags else "p2")
    return {"id": cid, "module": module, "title": title, "priority": prio, "tags": tags,
            "destructive": bool(WRITES.search(text)), "draft": True,
            "preconditions": pre, "expected": r["expected"], "steps": []}


def _taken_numbers() -> dict[str, int]:
    """Highest TC_<PREFIX>_<n> already used OUTSIDE the library, so imported IDs never clash."""
    top: dict[str, int] = defaultdict(int)
    for f in (ROOT / "testcases").rglob("*.yaml"):
        if OUT in f.parents:
            continue
        for raw in yaml.safe_load(f.read_text(encoding="utf-8")) or []:
            m = re.fullmatch(r"TC_([A-Z]+)_(\d+)", str(raw.get("id", "")))
            if m:
                top[m.group(1)] = max(top[m.group(1)], int(m.group(2)))
    return top


def run(src_dir: Path) -> dict:
    packs = sorted(p for p in src_dir.glob("*.md"))
    unknown = [p.name for p in packs if p.name not in PACKS]
    if unknown:
        raise SystemExit(f"No module mapping for: {', '.join(unknown)} -- add them to PACKS.")
    counter = _taken_numbers()
    by_module: dict[str, list[dict]] = defaultdict(list)
    mapping: list[tuple] = []
    for p in packs:
        for r in read_pack(p):
            module, pfx = _module_for(p.name, r["src"])
            counter[pfx] += 1
            cid = f"TC_{pfx}_{counter[pfx]:03d}"
            by_module[module].append(_case(r, p.name, module, cid))
            mapping.append((cid, module, p.name, r["src"], r["title"][:100]))
    if OUT.exists():
        for old in OUT.glob("*.yaml"):
            old.unlink()
    OUT.mkdir(parents=True, exist_ok=True)
    for module, cases in sorted(by_module.items()):
        head = (f"# {module}: {len(cases)} scenarios imported from ai-projects "
                f"(margbooks-test-automation/e2e/scenarios).\n"
                f"# DRAFTS: no steps yet, so the runner skips them. Record or write the steps in Test Studio.\n"
                f"# Generated by: python -m framework.import_scenarios -- edits here are lost on re-import.\n\n")
        body = yaml.safe_dump(cases, allow_unicode=True, sort_keys=False, width=110)
        (OUT / f"{module}.yaml").write_text(head + body, encoding="utf-8")
    with open(OUT / "_mapping.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["new_id", "module", "source_pack", "source_id", "title"])
        w.writerows(mapping)
    return {m: len(c) for m, c in sorted(by_module.items())}


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: python -m framework.import_scenarios <path to e2e/scenarios>")
    counts = run(Path(sys.argv[1]))
    for m, n in counts.items():
        print(f"  {m:<15} {n:>4}")
    print(f"  {'TOTAL':<15} {sum(counts.values()):>4}  -> {OUT}")
