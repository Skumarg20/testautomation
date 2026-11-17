"""
Page dumper -- AI ke BINA, bilkul free.

Ab ye page ko "asli me load hua ya nahi" verify karta hai. Har screen ke liye
ek pehchaan (marker) hai; wo na mile to file likhne ke bajaye WARNING deta hai,
taki khaali grey page ka bekaar dump na bane.

    python -m framework.dump --all
    python -m framework.dump --page sale
"""
from __future__ import annotations

import argparse
from playwright.sync_api import sync_playwright

from config.settings import settings


def safe_shot(page, path):
    """Screenshot -- fail ho to chup-chaap chhod do, run mat girao."""
    for kw in ({"full_page": True, "timeout": 8000}, {"timeout": 5000}):
        try:
            page.screenshot(path=str(path), **kw)
            return True
        except Exception:  # noqa: BLE001
            continue
    return False
from framework import safety
from framework.browser import launch
from framework.auth import login, app_ready

# page -> (url path, marker text jo page load hone pe dikhna chahiye)
PAGES = {
    "login":     ("LOGIN", "Sign In"),
    "dashboard": ("/dashboard", "Dashboard"),
    "item":      ("/item-master/list", "Item List"),
    "party":     ("/partymaster/list", "Ledger Master"),
    "sale":      ("/transaction", "Party Name"),
    # neeche wale screens URL se nahi khulte -- --screen se dump karo
}

JS = """
() => {
  const out = [];
  const q = 'input,select,textarea,button,a,[role="button"],[data-testid],label,th,td,h1,h2,h3';
  document.querySelectorAll(q).forEach(e => {
    const r = e.getBoundingClientRect();
    if (r.width === 0 && r.height === 0) return;
    const cls = (typeof e.className === 'string')
        ? e.className.trim().split(/\\s+/).slice(0,3).join(' ') : '';
    out.push({
      tag: e.tagName.toLowerCase(),
      type: e.getAttribute('type') || '',
      id: e.id || '',
      name: e.getAttribute('name') || '',
      testid: e.getAttribute('data-testid') || '',
      ph: e.getAttribute('placeholder') || '',
      aria: e.getAttribute('aria-label') || '',
      role: e.getAttribute('role') || '',
      href: e.getAttribute('href') || '',
      cls: cls,
      text: (e.innerText || e.value || '').trim().replace(/\\s+/g,' ').slice(0,45),
    });
  });
  return out.slice(0, 600);
}
"""


def fmt(els) -> str:
    lines, seen = [], set()
    for e in els:
        parts = [f"<{e['tag']}{'/' + e['type'] if e['type'] else ''}>"]
        for k, lbl in (("id", "id"), ("name", "name"), ("testid", "testid"),
                       ("ph", "placeholder"), ("aria", "aria"), ("role", "role"), ("href", "href"),
                       ("cls", "class"), ("text", "TEXT")):
            if e[k]:
                parts.append(f"{lbl}={e[k]}")
        line = " | ".join(parts)
        if line not in seen:
            seen.add(line)
            lines.append(line)
    return "\n".join(lines)


def dump_page(page, key, path, marker) -> bool:
    url = settings.LOGIN_URL if path == "LOGIN" else f"{settings.BASE_URL}{path}"
    print(f"\n>> {key}  ({url})")
    page.goto(url, wait_until="domcontentloaded")
    page.wait_for_timeout(2000)

    # SPA ko render hone do
    ok = False
    for _ in range(6):
        try:
            page.get_by_text(marker, exact=False).first.wait_for(state="visible", timeout=2500)
            ok = True
            break
        except Exception:  # noqa: BLE001
            page.wait_for_timeout(1500)

    settings.ARTIFACTS.mkdir(parents=True, exist_ok=True)
    safe_shot(page, settings.ARTIFACTS / f"dump_{key}.png")

    if not ok:
        print(f"   !! WARNING: '{marker}' nahi mila -- page theek se load nahi hua.")
        print(f"      Landed on: {page.url}")
        print(f"      dump_{key}.png dekh lo.")

    els = page.evaluate(JS)
    header = (f"# PAGE  : {key}\n# URL   : {page.url}\n# TITLE : {page.title()}\n"
              f"# MARKER: {'FOUND' if ok else 'NOT FOUND -- page shayad khali hai'}\n\n")
    out = settings.ARTIFACTS / f"dump_{key}.txt"
    out.write_text(header + fmt(els) + "\n", encoding="utf-8")
    print(f"   {len(els)} elements -> {out.name}")
    return ok


MENUS = ["master", "sale", "purchase", "accounting", "stock", "banking", "crm"]


def dump_menus(page):
    """Har top menu ko khol ke uske submenu links (text + href) nikaalo.
    Isse pata chalta hai ki Sale Bill jaise screens ka asli raasta kya hai."""
    from framework.base_page import BasePage
    from framework.nav import open_menu, submenu_links

    bp = BasePage(page)
    bp.goto("/dashboard")
    page.wait_for_timeout(2500)

    out = ["# LEFT MENU -> SUBMENU MAP\n"]
    for m in MENUS:
        try:
            open_menu(bp, m)
            links = submenu_links(bp)
            out.append(f"\n## {m.upper()}")
            seen = set()
            for text, href in links:
                k = (text, href)
                if k in seen:
                    continue
                seen.add(k)
                out.append(f"  {text!r:45}  href={href}")
            print(f"  {m}: {len(seen)} submenu items")
            open_menu(bp, m)  # band kar do
        except Exception as e:  # noqa: BLE001
            out.append(f"\n## {m.upper()}  -- ERROR: {e}")
            print(f"  {m}: ERROR {e}")

    settings.ARTIFACTS.mkdir(parents=True, exist_ok=True)
    f = settings.ARTIFACTS / "dump_menus.txt"
    f.write_text("\n".join(out), encoding="utf-8")
    safe_shot(page, settings.ARTIFACTS / "dump_menus.png")
    print(f"\n-> {f}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--page")
    ap.add_argument("--menus", action="store_true", help="left menu ka submenu map nikaalo")
    ap.add_argument("--screen", help="screens.py wale kisi bhi screen ko dump karo, jaise sale_bill")
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args()

    settings.validate()
    settings.init_run("page dump")
    keys = list(PAGES) if args.all or not args.page else [args.page]

    with sync_playwright() as pw:
        browser, ctx = launch(pw)
        page = ctx.new_page()

        if args.screen:
            from framework.base_page import BasePage
            from framework.screens import open_screen
            print("Logging in...")
            bp = login(page, verbose=True)
            print(f"\nOpening screen: {args.screen}")
            ok = open_screen(bp, args.screen, verbose=True)
            print(f"   {'khul gaya' if ok else 'NAHI khula'} -- URL: {page.url}")
            page.wait_for_timeout(2500)
            settings.ARTIFACTS.mkdir(parents=True, exist_ok=True)
            safe_shot(page, settings.ARTIFACTS / f"dump_{args.screen}.png")
            els = page.evaluate(JS)
            out = settings.ARTIFACTS / f"dump_{args.screen}.txt"
            out.write_text(f"# SCREEN: {args.screen}\n# URL: {page.url}\n"
                           f"# OPENED: {ok}\n\n" + fmt(els), encoding="utf-8")
            print(f"   {len(els)} elements -> {out}")
            browser.close()
            return

        if args.menus:
            print("Logging in...")
            login(page, verbose=True)
            print("\nDumping menus...")
            dump_menus(page)
            browser.close()
            return

        if keys != ["login"]:
            print("Logging in (company select included)...")
            login(page, verbose=True)
            if not app_ready(page):
                print("!! App ready nahi hua -- aage jaane ka fayda nahi.")
                browser.close()
                return

        results = {}
        for k in keys:
            path, marker = PAGES[k]
            try:
                results[k] = dump_page(page, k, path, marker)
            except Exception as e:  # noqa: BLE001
                print(f"   ERROR: {e}")
                results[k] = False

        browser.close()

    print("\n--- Summary ---")
    for k, v in results.items():
        print(f"  {'OK  ' if v else 'FAIL'}  {k}")
    print(f"\nFiles: {settings.ARTIFACTS}")
    print("dump_*.txt bhej do -- locator map bana diya jayega.")


if __name__ == "__main__":
    main()
