"""
Health check -- browser kholne se pehle sab theek hai ya nahi, ye batata hai.

    python -m framework.doctor      (ya doctor.bat double-click)
"""
from __future__ import annotations

import sys
from pathlib import Path

OK, BAD, WARN = "[ OK ]", "[FAIL]", "[WARN]"
problems: list[str] = []


def check(label, cond, fix=""):
    print(f"{OK if cond else BAD}  {label}")
    if not cond and fix:
        problems.append(f"{label}\n       -> {fix}")
    return cond


def main():
    from config.settings import settings as _st
    print(f"\n=== MargBooks QA Agent -- Health Check ===")
    print(f"    build {_st.BUILD}\n")

    print("-- Python & libraries --")
    check(f"Python {sys.version.split()[0]}", sys.version_info >= (3, 10),
          "Python 3.10+ chahiye")
    for mod, name in [("playwright", "playwright"), ("pytest", "pytest"),
                      ("yaml", "pyyaml"), ("dotenv", "python-dotenv"),
                      ("faker", "faker")]:
        try:
            __import__(mod)
            ok = True
        except ImportError:
            ok = False
        check(f"library: {name}", ok, f"pip install {name}")

    print("\n-- Folder structure --")
    root = Path(__file__).resolve().parent.parent
    FOLDERS = ["framework", "pages", "ui", "config", "locators", "testcases", "tests"]
    for d in FOLDERS:
        check(f"{d}/ folder", (root / d).is_dir(),
              f"'{d}' folder missing -- zip theek se unzip nahi hua")
    # khule pade hue .py -- galat copy ki nishani
    loose = [f.name for f in root.glob("*.py") if f.name != "conftest.py"]
    if loose:
        print(f"{WARN}  Root me {len(loose)} khuli .py file mili: {loose[:6]}")
        problems.append(
            f"Root me {len(loose)} .py files khuli padi hain "
            f"(sirf conftest.py hona chahiye)\n"
            f"       Ye purani copies hain -- zip unzip karte waqt files\n"
            f"       galat jagah gir gayin. Python inhe padhta HI NAHI,\n"
            f"       par ye confusion banati hain.\n"
            f"       -> in files ko delete kar do:\n"
            f"          {', '.join(loose[:10])}")
    else:
        print(f"{OK}  Root saaf hai (sirf conftest.py)")

    print("\n-- Project files (naya version hai ya purana) --")
    root = Path(__file__).resolve().parent.parent
    files = {
        "framework/auth.py": "organisations mile",
        "framework/nav.py": "click_submenu",
        "framework/dump.py": "MARKER",
        "framework/doctor.py": "Health Check",
        "locators/margbooks.yaml": "searchItems",
        # 06_search.yaml ab _examples/ me hai (library khali kar di gayi).
        # Login ke case hi bundled hain, isliye unhi se version jaanchte hain.
        "testcases/01_auth.yaml": "unregistered_user",
        "framework/screens.py": "sale_bill",
        "framework/safety.py": "MB-QA-GUARD",
        "pages/transaction_form.py": "_find_suffix",
        "pages/sale_bill_page.py": "add_by_barcode",
        "pages/ag_grid.py": "row-index",
        "pages/form_profile.py": "wholesale",
        "pages/lookup.py": "SearchBox",
        "framework/base_page.py": "describe_fields",
        "locators/margbooks.yaml": "txtlegername",
        "framework/catalogue.py": "SCAN_JS",
        "framework/page_ready.py": "spinner_visible",
        "framework/control_room.py": "mode_of_payment",
        "framework/heal.py": "SLIM_DOM_JS",
        "pages/retail_billing.py": "party_state",
        "framework/code_scanner.py": "SKIP_DIRS",
        "ui/codegen_import.py": "LOCATOR_CALL",
        "framework/mapping.py": "confidence",
        "framework/logbook.py": "execution_history",
        "config/prerequisites.json": "ask_item_discount",
        "framework/crawler.py": "SKIPPED_BY_CONFIG",
        "config/menu_sequence.json": "menu_sequence",
        "framework/ai.py": "GEMINI_URL",
        "framework/menu_tree.py": "Inventory Master",
        "ui/app.html": "tape-wrap",
        "config/settings.py": "BROWSER_MAXIMIZE",
        "framework/browser.py": "detect_screen",
        "framework/netguard.py": "netguard",
        "framework/browser.py": "fit_window",
        "framework/event_recorder.py": "isTrusted",
        "pages/grid.py": "scroll_all",
    }
    for rel, needle in files.items():
        f = root / rel
        ok = f.exists() and needle in f.read_text(encoding="utf-8", errors="ignore")
        check(f"{rel} (latest)", ok,
              "Purani file hai -- naye zip se replace karo")

    print("\n-- Config --")
    # DHYAAN: is function me neeche 'from config.settings import settings'
    # likha hai. Python ka niyam -- naam kahin bhi assign ho to wo POORE
    # function me local ban jata hai. Isliye yahan bare 'settings' likhne se
    # UnboundLocalError aata tha. Alag naam se import karte hain.
    from config.settings import settings as _cfg
    _env = getattr(_cfg, "ACTIVE_ENV", None)
    if _env:
        print(f"{OK}  Environment: {_env}  (UI ke Settings tab se)")
    else:
        print(f"{OK}  Environment: .env se (UI me koi environment nahi chuna)")
    env = root / ".env"
    if not check(".env maujood hai", env.exists(), "copy .env.example .env"):
        _finish()
        return
    from config.settings import settings
    check(f"LOGIN_URL = {settings.LOGIN_URL}",
          settings.LOGIN_URL.startswith("https://") and "." in settings.LOGIN_URL,
          "pura URL daalo, jaise https://accounts.margbooks.com")
    check(f"APP_URL   = {settings.BASE_URL}",
          settings.BASE_URL.startswith("https://") and "books" in settings.BASE_URL,
          "login ke baad address bar wala domain, jaise https://books5.margbooks.com")
    check("MARGBOOKS_USER", bool(settings.USER), ".env me daalo")
    check("PASS ya PIN", bool(settings.PASSWORD or settings.PIN), ".env me daalo")
    check("MARGBOOKS_COMPANY", bool(settings.COMPANY),
          "Organisation List me se EXACT naam daalo")
    print(f"{WARN if settings.ALLOW_DESTRUCTIVE else OK}  "
          f"ALLOW_DESTRUCTIVE = {settings.ALLOW_DESTRUCTIVE}"
          f"{'   <-- data likhne wale tests CHALENGE' if settings.ALLOW_DESTRUCTIVE else ''}")
    import os as _os
    _raw = _os.getenv("BROWSER_MAXIMIZE")
    if settings.BROWSER_MAXIMIZE:
        try:
            from framework.browser import detect_screen
            _sw, _sh = detect_screen()
            print(f"{OK}  Window = maximized -> {_sw}x{_sh}")
        except Exception:  # noqa: BLE001
            print(f"{OK}  Window = maximized")
    else:
        print(f"{WARN}  Window = {settings.VIEWPORT_W}x{settings.VIEWPORT_H} FIXED"
              f"  (.env me BROWSER_MAXIMIZE={_raw!r})")
        problems.append("Window fixed hai, screen se bada ho sakta hai\n"
                        "       -> .env me likho: BROWSER_MAXIMIZE=true")
    print(f"{OK}  HEADLESS = {settings.HEADLESS}"
          f"{'   (browser dikhega nahi)' if settings.HEADLESS else '   (browser dikhega)'}")
    print(f"{OK}  AI key = {'set hai' if settings.ANTHROPIC_API_KEY else 'nahi (AI features band)'}")

    print("\n-- Test cases --")
    try:
        from framework.case_loader import load_all
        from framework.locator_store import store
        cases = load_all()
        known = set(store.all_keys())
        missing = {t for c in cases for s in c.steps
                   if (t := s.get("target")) and not t.startswith("/")
                   and "." in t and t not in known}
        check(f"{len(cases)} test cases load hue", bool(cases))
        check(f"{len(known)} locators", len(known) > 50)
        check("har case ka locator maujood", not missing,
              f"missing: {sorted(missing)[:5]}")
    except Exception as e:  # noqa: BLE001
        check("test cases parse", False, str(e))

    print("\n-- Suraksha --")
    from framework import safety
    if settings.ALLOW_DESTRUCTIVE:
        print(f"{WARN}  Delete-guard OFF hai (ALLOW_DESTRUCTIVE=true)")
        print(f"       Sirf demo account pe aisa rakho.")
    else:
        print(f"{OK}  Delete-guard ON -- har page pe delete/remove buttons blocked")
    print(f"{OK}  'Not authorized' wale screens FAIL nahi, SKIP honge")
    if settings.ALLOW_DESTRUCTIVE:
        print(f"{BAD}  NETGUARD OFF -- delete requests server tak jayengi!")
    else:
        print(f"{OK}  Netguard ON -- delete/remove HTTP request block hongi")
    print(f"{OK}  Event recorder ON -- har click/key record hoga")

    print("\n-- Agent ka gyaan --")
    from framework import catalogue as _cat
    st = _cat.stats()
    if st["elements"]:
        print(f"{OK}  Catalogue: {st['elements']} field, {st['screens']} screen")
    else:
        print(f"{WARN}  Catalogue khali hai -- pehla test chalte hi bharna shuru")
    from framework import control_room as _cr
    if _cr.load().get("read_at"):
        print(f"{OK}  {_cr.summary()}")
    else:
        print(f"{WARN}  Control Room abhi padha nahi gaya")
        print(f"       -> control-room.bat chalao (ya koi bhi run --"
              f" pehli baar apne aap padh lega)")

    from framework import code_scanner as _cs
    _sc = _cs.stats()
    if _sc.get("scanned_at"):
        print(f"{OK}  Source scan: {_sc['elements']} field, "
              f"{_sc['routes']} route ({_sc['scanned_at']})")
    else:
        print(f"{WARN}  Source scan nahi hua")
        print(f"       -> scan-code.bat (MargBooks ke frontend folder ka path)")

    from framework import ai as _ai
    av = _ai.available()
    if av["active"]:
        print(f"{OK}  AI: {av['active']} (saadhi bhasha -> steps)")
    else:
        print(f"{WARN}  Koi AI key nahi. Niyam-parser phir bhi chalega.")
        print(f"       -> Gemini free tier: aistudio.google.com/apikey")

    print("\n-- Browser --")
    try:
        from framework.browser import detect_screen
        sw, sh = detect_screen()
        print(f"{OK}  Screen (OS se): {sw}x{sh}")
    except Exception as e:  # noqa: BLE001
        print(f"{WARN}  Screen naap nahi paye: {str(e)[:60]}")
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            b = pw.chromium.launch(headless=True)
            b.close()
        check("Chromium chal raha hai", True)
    except Exception as e:  # noqa: BLE001
        check("Chromium", False, f"python -m playwright install chromium  ({e})")

    _finish()


def _finish():
    print()
    if problems:
        print("=" * 55)
        print(f"  {len(problems)} PROBLEM MILE -- ye theek karo:\n")
        for i, p in enumerate(problems, 1):
            print(f"  {i}. {p}")
        print("=" * 55)
    else:
        print("=" * 55)
        print("  SAB THEEK HAI. Ab login.bat chalao.")
        print("=" * 55)


if __name__ == "__main__":
    main()
