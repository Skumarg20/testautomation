"""
Locator discovery agent.

Live MargBooks page kholta hai, DOM condense karta hai, aur Claude se poochta hai
ki humare logical keys ke liye best Playwright selectors kya hain.
Phir locators/margbooks.yaml update kar deta hai.

    python -m agent.discover --page login
    python -m agent.discover --page sale --url /sale/invoice
    python -m agent.discover --all
"""
from __future__ import annotations

import argparse
from playwright.sync_api import sync_playwright
from rich import print as rprint

from config.settings import settings
from framework.browser import launch
from agent.client import ask_json, condense_dom
from framework.base_page import BasePage
from framework.locator_store import store
from framework.auth import login

SYSTEM = """You are a senior SDET mapping a web app's DOM to stable Playwright selectors.

Rules for the selectors you produce:
- Prefer, in order: data-testid > accessible role+name > label > placeholder > stable
  name/id attribute > CSS class. Never use auto-generated/hashed classes
  (e.g. .css-1x2y3z, .ng-tns-c12) or nth-child chains.
- Use these prefixes: testid=ID | role=ROLE:Name | label=Text | placeholder=Text |
  exact_text=Text | xpath=... | plain CSS.
- Give 2-3 ranked candidates per key so the suite can self-heal.
- If a requested key genuinely has no matching element on this page, omit it.
  Do NOT invent selectors.

Output JSON: {"page_key": {"element_key": ["sel1","sel2"], ...},
              "unmapped": ["keys you could not find"],
              "extra": {"element_key": ["sel"]}}
"extra" = useful elements present on the page that weren't in the requested list."""

PAGE_URLS = {
    "login": "LOGIN",                       # special: accounts.margbooks.com
    "nav": "/dashboard",
    "item": "/item-master/list",
    "party": "/partymaster/list",
    "sale": "/transaction",
    "report": "/dashboard",                 # GSTR ka real URL abhi confirm karna hai
}


def discover(page_key: str, url: str | None = None, ctx=None):
    wanted = [k.split(".", 1)[1] for k in store.all_keys() if k.startswith(page_key + ".")]
    bp = BasePage(ctx.new_page())
    try:
        target = url or PAGE_URLS.get(page_key, "/")
        bp.goto(settings.LOGIN_URL if target == "LOGIN" else target)
        bp.page.wait_for_load_state("networkidle")
        dom = condense_dom(bp.page)
        result = ask_json(
            SYSTEM,
            f"Page key: {page_key}\n"
            f"Element keys I need selectors for: {wanted}\n\n"
            f"Condensed DOM:\n{dom}",
            max_tokens=4000,
        )
        mapped = result.get(page_key) or result.get("page_key") or {}
        for el, sels in mapped.items():
            store.add(f"{page_key}.{el}", sels)
            rprint(f"  [green]mapped[/] {page_key}.{el} -> {sels[0]}")
        for el, sels in (result.get("extra") or {}).items():
            store.add(f"{page_key}.{el}", sels)
            rprint(f"  [cyan]extra [/] {page_key}.{el} -> {sels[0]}")
        for k in result.get("unmapped", []):
            rprint(f"  [yellow]MISS  [/] {page_key}.{k} -- page pe nahi mila")
        store.save()
    finally:
        bp.page.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--page")
    ap.add_argument("--url")
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args()

    settings.validate()
    with sync_playwright() as pw:
        browser, ctx = launch(pw)

        # login once (multi-step / PIN / saved session sab handle hota hai)
        _bp = login(ctx.new_page())
        _bp.page.close()

        targets = list(PAGE_URLS) if args.all else [args.page]
        for t in targets:
            rprint(f"\n[bold]Discovering {t}...[/]")
            try:
                discover(t, args.url, ctx)
            except Exception as e:  # noqa: BLE001
                rprint(f"  [red]error[/] {e}")

        browser.close()


if __name__ == "__main__":
    main()
