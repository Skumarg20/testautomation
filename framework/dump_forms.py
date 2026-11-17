"""
POM banane ke liye zaroori forms ka poora naksha -- ek hi command me.

    python -m framework.dump_forms
"""
from playwright.sync_api import sync_playwright

from config.settings import settings
from framework import safety
from framework.browser import launch
from framework.auth import login
from framework.dump import JS, fmt, safe_shot
from framework.screens import open_screen
from framework.screens_check import ensure_neutral

FORMS = [
    "item", "party",              # list pages (Create/F2 button yahin hai)
    "item_create", "party_create",   # CREATE form -- inka naksha nahi tha
    "sale_bill", "purchase_bill", # transaction create forms -- sabse zaroori
    "sale_return", "receipt", "payment",
]


def main():
    settings.validate()
    run = settings.init_run("form dump for POM")

    with sync_playwright() as pw:
        browser, ctx = launch(pw)
        bp = login(ctx.new_page(), verbose=True)
        page = bp.page

        for key in FORMS:
            ensure_neutral(bp)
            print(f"\n>> {key}")
            try:
                ok = open_screen(bp, key, verbose=True)
            except Exception as e:  # noqa: BLE001
                print(f"   ERROR: {str(e)[:110]}")
                continue
            page.wait_for_timeout(2500)
            safe_shot(page, run / f"form_{key}.png")
            els = page.evaluate(JS)
            (run / f"form_{key}.txt").write_text(
                f"# FORM: {key}\n# URL: {page.url}\n# OPENED: {ok}\n\n" + fmt(els),
                encoding="utf-8")
            print(f"   {len(els)} elements -> form_{key}.txt")

        ensure_neutral(bp)
        browser.close()

    print(f"\n{'='*55}")
    print(f"  Files: {run}")
    print(f"  form_*.txt bhej do -- POM classes bana di jayengi.")
    print(f"{'='*55}")


if __name__ == "__main__":
    main()
