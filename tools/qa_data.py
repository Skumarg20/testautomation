"""
Check (or top up) the shared test data of the QA companies listed in config/qa_data.json.

  python -m tools.qa_data --check                     # balance of every record, change nothing
  python -m tools.qa_data --fill                      # top up what is below its minimum
  python -m tools.qa_data --fill --only "QA Garment" --names 11110001,11110003

Writes happen only in QA test companies. A run of the test suite does the same automatically for the record a
failing test needed (framework.test_data.repair); this tool is for a check before a big run.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--fill", action="store_true")
    ap.add_argument("--only")
    ap.add_argument("--names", help="comma-separated record names")
    a = ap.parse_args()
    os.environ.setdefault("HEADLESS", "true")
    from config.settings import settings
    if a.fill:
        settings.ALLOW_DESTRUCTIVE = True
        type(settings).ALLOW_DESTRUCTIVE = True
    from playwright.sync_api import sync_playwright
    from framework.auth import login
    from framework.browser import launch
    from framework import qa_company, test_data

    data = test_data.load()
    companies = [a.only] if a.only else sorted(data)
    names = set(n.strip() for n in a.names.split(",")) if a.names else None
    with sync_playwright() as pw:
        browser, ctx = launch(pw)
        bp = login(ctx.new_page())
        for comp in companies:
            try:
                qa_company.switch(bp.page, comp)
            except Exception as e:  # noqa: BLE001
                print(f"{comp}: could not open ({str(e)[:200]})", flush=True)
                continue
            for e in data.get(comp, []):
                if names and e["name"] not in names:
                    continue
                log: list[str] = []
                try:
                    if a.fill:
                        ok = test_data.top_up(bp, comp, e, log)
                        print(f"{comp} {e['name']} ({e.get('note', '')}): {'OK' if ok else 'NOT FIXED'}", flush=True)
                    else:
                        r = test_data.check(bp, comp, e, log)
                        bal = "not offered (0 or below)" if r["balance"] is None else f"{r['balance']:g}"
                        print(f"{comp} {e['name']} ({e.get('note', '')}): {bal} (min {r['min']})"
                              f"{'' if r['ok'] else '  <- LOW'}", flush=True)
                except Exception as ex:  # noqa: BLE001
                    print(f"{comp} {e['name']}: ERROR {str(ex)[:300]}", flush=True)
                for line in log:
                    if "stock:" in line or "FAIL" in line:
                        print("   " + line.strip(), flush=True)
        browser.close()


if __name__ == "__main__":
    main()
