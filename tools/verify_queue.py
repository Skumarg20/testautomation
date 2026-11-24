"""
Split every test case into batches per QA test company, for verification in the live app.

    python -m tools.verify_queue [--batch 20]

Each case goes to a test company of a trade it is tagged for (trade:all -> any trade); among the eligible
companies the least loaded one wins, so the 8 sessions get equal work. Output:
  artifacts/verify/batches/<company_slug>/NNN.json   {"company", "cases": [{"id", "file"}]}
Re-running keeps finished cases out (a case is finished when artifacts/verify/cases/<id>.yaml exists).
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path

import yaml

from framework.qa_company import BY_TRADE, GST_BY_TRADE

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "verify"
SOURCES = [ROOT / "testcases" / "trades", ROOT / "testcases" / "library"]
# Cases about tax go to the GST-registered twin companies (the QA companies are GST Unregistered: tax is 0).
GST_RE = re.compile(r"\b(gst|cgst|sgst|igst|cess|tax|hsn|gstr|e-?invoice|e-?way|itc|reverse charge|rcm)\b", re.I)
ORDER = ["sales", "purchase", "inventory", "accounting", "gst", "masters", "reports", "banking", "company",
         "users", "utilities", "dashboard", "crm", "online_store", "auth"]


def slug(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", s).strip("_")


def load() -> list[dict]:
    out = []
    for folder in SOURCES:
        for f in sorted(folder.glob("*.yaml")):
            data = yaml.load(f.read_text(encoding="utf-8"), Loader=yaml.CSafeLoader) or []
            for c in data:
                if isinstance(c, dict) and c.get("id"):
                    trades = [t.split(":", 1)[1] for t in c.get("tags") or [] if str(t).startswith("trade:")]
                    text = " ".join(str(c.get(k, "")) for k in ("title", "expected", "module"))
                    out.append({"id": c["id"], "file": str(f.relative_to(ROOT)).replace("\\", "/"),
                                "module": c.get("module") or "", "trades": trades,
                                "gst": c.get("module") == "gst" or bool(GST_RE.search(text))})
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch", type=int, default=20)
    a = ap.parse_args()
    done = {p.stem for p in (OUT / "cases").glob("*.yaml")}
    cases = [c for c in load() if c["id"] not in done]
    rank = {m: i for i, m in enumerate(ORDER)}
    cases.sort(key=lambda c: (rank.get(c["module"], len(ORDER)), c["file"], c["id"]))
    allco = list(BY_TRADE.values()) + list(GST_BY_TRADE.values())
    load_ = {co: 0 for co in allco}
    per: dict[str, list] = {co: [] for co in allco}
    for c in cases:
        m = GST_BY_TRADE if c["gst"] else BY_TRADE
        elig = [m[t] for t in c["trades"] if t in m] or list(m.values())   # all / untagged
        co = min(elig, key=lambda x: load_[x])
        load_[co] += 1
        per[co].append({"id": c["id"], "file": c["file"], "module": c["module"]})
    shutil.rmtree(OUT / "batches", ignore_errors=True)
    for co, lst in per.items():
        d = OUT / "batches" / slug(co)
        d.mkdir(parents=True, exist_ok=True)
        for i in range(0, len(lst), a.batch):
            (d / f"{i // a.batch + 1:03d}.json").write_text(
                json.dumps({"company": co, "cases": lst[i:i + a.batch]}, indent=1), encoding="utf-8")
    print(f"{len(cases)} cases to verify ({len(done)} already done)")
    for co, n in load_.items():
        print(f"  {co:24s} {n:4d} cases, {-(-n // a.batch)} batches")


if __name__ == "__main__":
    main()
