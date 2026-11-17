"""
Test case generation agent.

Ek MargBooks screen kholta hai, dekhta hai kaun se fields/buttons hain, aur
naye YAML test cases likh deta hai -- existing cases ko dekh kar duplicate
avoid karta hai.

    python -m agent.generate --page sale --url /sale/invoice --count 8
    python -m agent.generate --page party --focus "GSTIN validation edge cases"
"""
from __future__ import annotations

import argparse
import yaml
from playwright.sync_api import sync_playwright
from rich import print as rprint

from config.settings import settings
from framework.browser import launch
from agent.client import ask_json, condense_dom
from agent.discover import PAGE_URLS
from framework.base_page import BasePage
from framework.auth import login
from framework.case_loader import load_all
from framework.locator_store import store

SYSTEM = """You are a senior QA engineer writing test cases for MargBooks, an Indian
cloud accounting / billing / inventory product (Marg ERP). Users are mostly pharma
distributors, retailers and small businesses, so GST correctness, batch-expiry
handling and invoice arithmetic matter more than cosmetic UI issues.

Write test cases in this exact YAML-as-JSON schema:
{"cases":[{
  "id": "TC_<MODULE>_<NNN>",
  "module": "sales|purchase|masters|inventory|gst|auth|reports",
  "title": "one line, states the expected behaviour not just the action",
  "priority": "p1|p2|p3",
  "tags": ["smoke","negative","calculation","gst",...],
  "destructive": true/false,     // true if it creates/edits/deletes data
  "preconditions": ["..."],
  "expected": ["concrete, checkable outcomes"],
  "steps": [{"action":"...","target":"page.element","value":"...","save_as":"var"}]
}]}

Allowed actions ONLY: goto, click, fill, select, press, wait_text, assert_text,
assert_no_text, assert_visible, assert_not_visible, sleep, screenshot, note.
Every "target" MUST be a key from the provided locator key list. If you need an
element that isn't in that list, use a "note" step describing it instead of
inventing a key.
Value placeholders available: {{item_name}} {{party_name}} {{batch_no}} {{hsn}}
{{gstin}} {{invalid_gstin}} {{mobile}} {{qty}} {{rate}} {{gst_rate}}

Prioritise: boundary values, GST intra vs inter state, rounding, discount order of
operations, negative stock, expired batch, duplicate records, permission checks,
and empty/invalid input. Avoid restating cases that already exist."""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--page", required=True)
    ap.add_argument("--url")
    ap.add_argument("--count", type=int, default=6)
    ap.add_argument("--focus", default="")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    settings.validate()
    existing = [{"id": c.id, "title": c.title} for c in load_all()]
    keys = store.all_keys()

    with sync_playwright() as pw:
        browser, ctx = launch(pw)
        bp = login(ctx.new_page())
        bp.goto(args.url or PAGE_URLS.get(args.page, "/"))
        bp.page.wait_for_load_state("networkidle")
        dom = condense_dom(bp.page)
        browser.close()

    result = ask_json(
        SYSTEM,
        f"Generate {args.count} NEW test cases for the '{args.page}' area."
        + (f"\nFocus specifically on: {args.focus}" if args.focus else "")
        + f"\n\nAvailable locator keys:\n{keys}"
        + f"\n\nExisting cases (do not duplicate):\n{existing}"
        + f"\n\nWhat's actually on the page right now:\n{dom}",
        max_tokens=8000,
    )

    cases = result.get("cases", [])
    out = settings.TESTCASES / (args.out or f"9_generated_{args.page}.yaml")
    prev = yaml.safe_load(out.read_text()) if out.exists() else []
    out.write_text(yaml.safe_dump((prev or []) + cases, sort_keys=False, allow_unicode=True))
    rprint(f"[green]{len(cases)} cases written -> {out}[/]")
    for c in cases:
        rprint(f"  {c['id']} [{c['priority']}] {c['title']}")
    rprint("\n[yellow]Review karo phir commit karo -- AI-generated cases human review maangte hain.[/]")


if __name__ == "__main__":
    main()
