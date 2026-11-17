"""
Failure triage agent.

artifacts/results.json padhta hai aur har failure ko classify karta hai:
  REAL_BUG | LOCATOR_DRIFT | TEST_DATA | ENVIRONMENT | FLAKY
Taki QA team 40 failures me se sirf real 3 pe time lagaye.

    python -m agent.triage
    python -m agent.triage --json artifacts/results.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from rich import print as rprint
from rich.table import Table
from rich.console import Console

from config.settings import settings
from agent.client import ask_json

SYSTEM = """You triage automated UI test failures for MargBooks (Marg ERP's cloud
accounting product). For each failure, decide the single most likely cause:

- REAL_BUG        : the app behaved incorrectly (wrong total, missing validation,
                    wrong GST split, data not saved)
- LOCATOR_DRIFT   : element not found / selector resolution error -> UI changed
- TEST_DATA       : precondition data missing or stale (item/party absent, stock 0,
                    prior case in the chain failed)
- ENVIRONMENT     : timeout, network, 5xx, login/session, slow demo server
- FLAKY           : race/timing, passes on retry, no consistent signal

Output JSON:
{"triage":[{"case_id":"...","category":"...","confidence":0.0-1.0,
            "reason":"one sentence","action":"concrete next step for the QA engineer",
            "bug_title":"only if REAL_BUG, otherwise null"}],
 "summary":"2-3 sentences on the overall run health"}"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=str(settings.ARTIFACTS / "results.json"))
    args = ap.parse_args()

    path = Path(args.json)
    if not path.exists():
        rprint("[red]results.json nahi mila -- pehle pytest chalao.[/]")
        return

    results = json.loads(path.read_text())
    failures = [r for r in results if r["outcome"] == "failed"]
    passed = len(results) - len(failures)
    if not failures:
        rprint(f"[green]Saare {passed} tests pass. Triage ki zaroorat nahi.[/]")
        return

    out = ask_json(SYSTEM, f"Run: {passed} passed, {len(failures)} failed.\n\n"
                           f"Failures:\n{json.dumps(failures, indent=1)[:60000]}",
                   max_tokens=6000)

    t = Table(title=f"Triage -- {len(failures)} failures")
    for col in ("Case", "Category", "Conf", "Reason", "Action"):
        t.add_column(col, overflow="fold")
    colors = {"REAL_BUG": "red", "LOCATOR_DRIFT": "yellow",
              "TEST_DATA": "cyan", "ENVIRONMENT": "magenta", "FLAKY": "white"}
    for r in out["triage"]:
        c = colors.get(r["category"], "white")
        t.add_row(r.get("case_id") or "?", f"[{c}]{r['category']}[/]",
                  f"{r.get('confidence', 0):.0%}", r["reason"], r["action"])
    Console().print(t)
    rprint(f"\n[bold]Summary:[/] {out['summary']}")

    bugs = [r for r in out["triage"] if r["category"] == "REAL_BUG"]
    if bugs:
        rprint("\n[bold red]Raise these as bugs:[/]")
        for b in bugs:
            rprint(f"  - {b['bug_title']}  (from {b.get('case_id')})")

    (settings.ARTIFACTS / "triage.json").write_text(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
