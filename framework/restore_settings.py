"""
Crawl ke liye badli hui Control Room settings wapas karo.

    python -m framework.restore_settings    (ya restore-settings.bat)

Crawl ke liye badli hui settings company me hamesha ke liye nahi rehni
chahiye -- warna kal koi asli kaam karega aur socha kuch aur hoga.
"""
import json

from playwright.sync_api import sync_playwright

from config.settings import settings
from framework import control_room as cr
from framework.auth import login
from framework.browser import launch


def main():
    print("\n=== SETTINGS WAPAS ===\n")

    if not cr.BACKUP.exists():
        print("  Koi backup nahi mila.")
        print("  Matlab crawler ne kabhi settings badli hi nahi.\n")
        return

    saved = json.loads(cr.BACKUP.read_text(encoding="utf-8"))
    rows = saved.get("settings", [])
    print(f"  Backup: {saved.get('saved_at')}")
    print(f"  {len(rows)} setting wapas karni hain:\n")
    for r in rows[:12]:
        print(f"    {r['label'][:46]:<46} -> {r['was']}")
    if len(rows) > 12:
        print(f"    ... aur {len(rows) - 12}")

    if not settings.ALLOW_DESTRUCTIVE:
        print("\n  !! 'Allow writes' band hai -- settings badli nahi ja sakti.")
        print("     UI ke Settings tab me on karo, phir dobara chalao.\n")
        return

    # Ijazat mil gayi (Allow writes ON). Ab bhi click-guard aur delete-block ON
    # rakhte hain -- sirf "Control Room ki setting badalna theek hai" kholte hain.
    settings.ALLOW_DESTRUCTIVE = False
    type(settings).ALLOW_DESTRUCTIVE = False
    cr.allow_settings_change(True)

    settings.validate()
    settings.init_run("settings restore")

    with sync_playwright() as pw:
        browser, ctx = launch(pw)
        try:
            print("\n  Login...")
            bp = login(ctx.new_page(), verbose=False)
            res = cr.restore(bp, verbose=True)
        finally:
            browser.close()

    print(f"\n  {res.get('restored', 0)} wapas ho gayin, "
          f"{res.get('failed', 0)} nahi ho payin")
    for p in (res.get("problems") or [])[:6]:
        print(f"    !! {p['label'][:44]}: {p.get('why', '')[:50]}")
    print()


if __name__ == "__main__":
    main()
