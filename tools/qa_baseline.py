"""
Save (or check) the "known good" Control Room settings of every QA test company: config/qa_baseline/*.json.
When a test switches to a QA company, settings that differ from this file are put back first
(framework.test_env.restore_baseline), so no test inherits what an earlier test left behind.

  python -m tools.qa_baseline --capture            # all QA companies (writes allowed only in QA companies)
  python -m tools.qa_baseline --capture --only "QA Chemist"
  python -m tools.qa_baseline --check              # list differences, change nothing

Overrides: values a company was verified with that a later test changed and did not put back
(found in the Studio sample run, 20-Nov-2026). They are written into the baseline AND set in the company.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

OVERRIDES = {
    # 42 QA Chemist cases expect a new bill to start on Cash Account (verified so); it was found on "Ask"
    "QA Chemist": {"Ask Party in Retail Billing #1": "Don't Ask"},
    # TC_MCAU_079 (verified in QA Mobile Trade) expects the party list on a new bill; it was found on Cash
    "QA Mobile Trade": {"Ask Party in Retail Billing #1": "Ask"},
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--capture", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--only")
    a = ap.parse_args()
    os.environ.setdefault("HEADLESS", "true")
    from config.settings import settings
    settings.ALLOW_DESTRUCTIVE = True
    type(settings).ALLOW_DESTRUCTIVE = True
    from playwright.sync_api import sync_playwright
    from framework.auth import login
    from framework.browser import launch
    from framework import qa_company, test_env, control_room as cr

    companies = [a.only] if a.only else sorted(set(qa_company.BY_TRADE.values()) | set(qa_company.GST_BY_TRADE.values()))
    with sync_playwright() as pw:
        browser, ctx = launch(pw)
        bp = login(ctx.new_page())
        for comp in companies:
            try:
                qa_company.switch(bp.page, comp)
                if a.check:
                    base = test_env.load_baseline(comp)
                    if not base:
                        print(f"{comp}: no baseline file")
                        continue
                    cr.open_control_room(bp)
                    live = {r["css"]: r.get("value", "") for r in cr._rows_live(bp)}
                    from framework import safety
                    safety.force_close_modal(bp.page)
                    diff = [f"{s['label']}: {live.get(s['css'])!r} (baseline {s['value']!r})" for s in base["settings"]
                            if s["css"] in live and str(live[s["css"]]).strip().lower() != str(s["value"]).strip().lower()]
                    print(f"{comp}: {len(diff)} difference(s)" + "".join(f"\n   {d}" for d in diff))
                    continue
                ov = OVERRIDES.get(comp, {})
                for label, val in ov.items():
                    res = cr.set_setting(bp, label, val)
                    print(f"{comp}: {res['label']} -> {res['value']}" + (" (changed)" if res["changed"] else ""))
                out = test_env.capture_baseline(bp, comp)
                print(f"{comp}: baseline saved, {len(out['settings'])} settings", flush=True)
            except Exception as e:  # noqa: BLE001
                print(f"{comp}: FAILED {str(e)[:300]}", flush=True)
        browser.close()


if __name__ == "__main__":
    main()
