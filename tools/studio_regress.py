"""
Run every script-ready verified case through the Test Studio executor, the same way the Run screen does
(screenshot after every step), and record the outcome next to the verification result.

A case that passed in the live-app verification but fails here points at Test Studio, not at the case.

  python -m tools.studio_regress --plan                 # list the workers
  python -m tools.studio_regress --worker 0             # run worker 0 (resumable: finished cases are skipped)
  python -m tools.studio_regress --report               # summary of artifacts/studio_regress/results.jsonl

Writes are allowed only inside the QA test companies (the qa_company guard still applies to every step).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUT = ROOT / "artifacts" / "studio_regress"
RESULTS = OUT / "results.jsonl"


def ready_cases() -> list[dict]:
    from ui_studio import tests
    return [t for t in tests.list_tests() if (t.get("ver") or {}).get("ready")]


def plan() -> list[list[str]]:
    """One worker per trade: the plain QA company and its GST twin run one after the other (never two runs
    in the same company at once, because cases change that company's settings)."""
    by_trade: dict[str, list[dict]] = defaultdict(list)
    for t in ready_cases():
        trade = t["ver"]["company"].replace("QA GST ", "").replace("QA ", "")
        by_trade[trade].append(t)
    workers = []
    for trade in sorted(by_trade):
        cs = sorted(by_trade[trade], key=lambda t: (t["ver"]["company"], t["id"]))
        workers.append([t["id"] for t in cs])
    return workers


def done_ids() -> set[str]:
    if not RESULTS.exists():
        return set()
    out = set()
    for line in RESULTS.read_text(encoding="utf-8").splitlines():
        try:
            out.add(json.loads(line)["id"])
        except Exception:  # noqa: BLE001
            pass
    return out


def run_worker(n: int, only: list[str] | None = None, limit: int = 0) -> None:
    os.environ.setdefault("HEADLESS", "true")
    from config.settings import settings
    settings.ALLOW_DESTRUCTIVE = True
    type(settings).ALLOW_DESTRUCTIVE = True
    from ui import envs
    orig = envs.apply_active

    def _apply():
        e = orig() or {}
        settings.ALLOW_DESTRUCTIVE = True
        type(settings).ALLOW_DESTRUCTIVE = True
        return e
    envs.apply_active = _apply
    from ui_studio import tests, executor

    ids = only or plan()[n]
    if limit and not only:                     # a sample spread over the whole list (all screens/modules)
        ids = ids[::max(1, len(ids) // limit)][:limit]
    skip = done_ids() if not only else set()
    OUT.mkdir(parents=True, exist_ok=True)
    for cid in ids:
        if cid in skip:
            continue
        case = tests.load_cases([cid])
        meta = case[0]
        statuses: dict[int, str] = {}
        t0 = time.time()
        try:
            r = executor._play(case, {"dir": str(OUT / "runs" / cid), "label": cid, "video": False, "shots": True,
                                      "trace": True, "stop_first": False},
                               lambda ci, si, st, sc, sh: statuses.__setitem__(si, st), lambda m: None)[0]
        except Exception as e:  # noqa: BLE001
            r = {"outcome": "failed", "error": f"runner crashed: {e}", "failed_step": -1}
        fs = r.get("failed_step", -1)
        rec = {"id": cid, "worker": n, "outcome": r.get("outcome"), "error": (r.get("error") or "")[:1500],
               "failed_step": fs, "step": (meta["steps"][fs] if isinstance(fs, int) and 0 <= fs < len(meta["steps"]) else None),
               "seconds": round(time.time() - t0, 1), "at": time.strftime("%Y-%m-%d %H:%M:%S"),
               "dir": str(OUT / "runs" / cid)}
        with RESULTS.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, default=str) + "\n")
        print(f"[w{n}] {cid}: {rec['outcome']} ({rec['seconds']} s) {rec['error'][:160]}", flush=True)


def report() -> None:
    rows = {}
    for line in RESULTS.read_text(encoding="utf-8").splitlines() if RESULTS.exists() else []:
        r = json.loads(line)
        rows[r["id"]] = r                       # the latest run of a case counts
    c = Counter(r["outcome"] for r in rows.values())
    total = len(ready_cases())
    print(f"{len(rows)} of {total} run: {dict(c)}")
    for r in rows.values():
        if r["outcome"] != "passed":
            print(f"  {r['id']}: {r['outcome']} @ {r['failed_step']}: {r['error'][:200]!r}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--worker", type=int)
    ap.add_argument("--ids", help="comma separated case ids to (re)run")
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--limit", type=int, default=0, help="run only N cases per worker, spread over its list")
    a = ap.parse_args()
    if a.plan:
        for i, w in enumerate(plan()):
            print(i, len(w), w[:3])
    elif a.report:
        report()
    elif a.ids:
        run_worker(a.worker or 0, a.ids.split(","))
    elif a.worker is not None:
        run_worker(a.worker, limit=a.limit)
