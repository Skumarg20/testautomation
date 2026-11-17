"""
Bulk bills: "Create 500 sale bills with 50 items each, random party and random items".

NOT VERIFIED against a live company. It reuses the project's own pages (PartyPage, ItemPage, SaleBillPage) and
follows the rules in Settings > Bulk data rules, but two rules are best-effort because the list screens do not
expose them as a column the project has ever read:
  * "Sundry Debtors only"  -> parties whose list row mentions Sundry Debtors; if none do, it stops.
  * "in-stock items only"  -> item list order; the app's own out-of-stock warning is not read yet.
It refuses to run unless Settings says "This is a test company".
"""
from __future__ import annotations

import random

from ui_studio import state


def run(bp, sale_factory, bills: int, items: int, log: list[str]) -> None:
    from framework.step_runner import StepFailed
    from pages.item_page import ItemPage
    from pages.party_page import PartyPage
    from pages.sale_bill_page import SaleBillPage
    s = state.load_settings()
    if not s["test_company"]:
        raise StepFailed("Bulk bills need “This is a test company” ticked in Settings. Nothing was created.")
    rules = s["bulk"]
    parties = PartyPage.open(bp)
    rows = parties.all_rows()
    pool = [r[0] for r in rows if r and (not rules.get("party") or any("sundry debtors" in c.lower() for c in r))]
    if not pool:
        raise StepFailed("No Sundry Debtors party found in the Ledger list. Nothing was created.")
    names = ItemPage.open(bp).names()
    if len(names) < 1:
        raise StepFailed("No items found in the Item list. Nothing was created.")
    rnd = random.Random()
    for n in range(1, bills + 1):
        form = SaleBillPage.open(bp)
        form.set_party(rnd.choice(pool))
        for row in range(items):
            form.add_item(rnd.choice(names), qty=rnd.randint(1, 10) if rules.get("qty") else 1, row=row)
        form.save()
        if rules.get("shot"):
            bp.screenshot(f"bulk_bill_{n}")
        if n % 10 == 0 or n == bills:
            log.append(f"      bulk: {n}/{bills} bills")
