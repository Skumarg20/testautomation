"""
MargBooks ka poora UI crawl.

    python -m framework.run_crawler            naya crawl
    python -m framework.run_crawler --resume   jahan ruka tha wahan se

Ya seedha: run-margbooks-crawler.bat
"""
import sys

from playwright.sync_api import sync_playwright

from config.settings import settings
from framework import logbook
from framework.auth import login
from framework.browser import launch
from framework.crawler import OUT, Crawler


def main():
    resume = "--resume" in sys.argv
    # --enable        -> SAARI Yes/No settings (yahi aam zaroorat hai)
    # --enable-known  -> sirf 15 jaani-pehchani (chhota sweep)
    # --minutes N  -> crawl ki seema (default 90).
    # Ek crawl 28 GHANTE chal chuka hai aur sirf 3 page nikale.
    budget = 90
    for i, a in enumerate(sys.argv):
        if a == "--minutes" and i + 1 < len(sys.argv):
            try:
                budget = max(5, int(sys.argv[i + 1]))
            except ValueError:
                pass

    enable = ("known" if "--enable-known" in sys.argv
              else "all" if ("--enable" in sys.argv
                             or "--enable-all" in sys.argv) else "none")

    # READ-ONLY -- chahe UI me "Allow writes" ON ho.
    #
    # Crawler ka kaam DEKHNA hai, chhoona nahi. Ek galti se bill save ho
    # jaye ya setting badal jaye to wo kisi ki asli company me chala jayega.
    # Isliye yahan zabardasti band karte hain.
    was = settings.ALLOW_DESTRUCTIVE
    if enable == "none":
        # Sirf padhna hai -- likhna zabardasti band.
        settings.ALLOW_DESTRUCTIVE = False
        type(settings).ALLOW_DESTRUCTIVE = False
    elif not was:
        print("\n  !! Settings ON karne ke liye 'Allow writes' chahiye.")
        print("     UI ke Settings tab me on karo, ya .env me")
        print("     ALLOW_DESTRUCTIVE=true likho.\n")
        sys.exit(2)
    else:
        # --enable: Control Room ki setting badalni hai. Par click-guard aur
        # delete-request block poore crawl me ON rehte hain -- ALLOW_DESTRUCTIVE
        # False rakhte hain, aur sirf "setting badalna theek hai" ka alag flag
        # kholte hain. (Pehle yahan guard poora band ho jata tha.)
        settings.ALLOW_DESTRUCTIVE = False
        type(settings).ALLOW_DESTRUCTIVE = False
        from framework import control_room
        control_room.allow_settings_change(True)

    print("=" * 56)
    print("  MARGBOOKS UI CRAWLER")
    print("=" * 56)
    print(f"  App     : {settings.BASE_URL}")
    print(f"  Company : {settings.COMPANY}")
    print(f"  Mode    : {'RESUME' if resume else 'naya crawl'}")
    print(f"  Menu    : {'purani config list (--no-discover)' if '--no-discover' in sys.argv else 'live sidebar se (config sirf jaankari jodti hai)'}")
    print(f"  App host: {settings.BASE_URL}  (login ke baad asli host se badal sakta hai)")
    print(f"  Seema   : {budget} minute (--minutes se badlo)")
    if enable == "none":
        print(f"  Likhna  : BAND (crawler sirf padhta hai)")
        if was:
            print(f"            ('Allow writes' ON tha -- crawl ke liye band kiya)")
    else:
        what = ("sirf 15 jaani-pehchani settings" if enable == "known"
                else "HAR setting jisme 'Yes' ka vikalp hai")
        print(f"  Settings: {what} ON ki jayengi")
        print(f"            Purani haalat backup hogi --")
        print(f"            wapas karne ke liye: restore-settings.bat")
    print("=" * 56)

    settings.validate()
    settings.init_run("UI crawl")

    with sync_playwright() as pw:
        browser, ctx = launch(pw)
        try:
            print("\nLOGIN")
            bp = login(ctx.new_page(), verbose=True)

            # Login sach me hua? Maan kar nahi chalte.
            body = (bp.page.inner_text("body") or "").lower()
            if not any(w in body for w in ("dashboard", "books from", "master")):
                print("  [FAIL] Login ke baad dashboard nahi mila -- ruk rahe hain")
                logbook.write("scanner", "crawl", "fail", error="login verify fail")
                browser.close()
                sys.exit(2)
            print("  [PASS] Login ho gaya")

            summary = Crawler(bp, resume=resume, enable=enable,
                              budget_min=budget,
                              discover="--no-discover" not in sys.argv).run()
        finally:
            browser.close()

    print("\n" + "=" * 56)
    print("  CRAWL KHATAM")
    print("=" * 56)
    print(f"  Menu     : {summary['menusPassed']} pass, "
          f"{summary['menusFailed']} fail, {summary['menusSkipped']} skip")
    print(f"  Page     : {summary['pagesPassed']} pass, "
          f"{summary['pagesFailed']} fail, "
          f"{summary.get('pagesBlocked', 0)} blocked")
    print(f"  Create   : {summary.get('createFormsPassed', 0)} form mile, "
          f"{summary.get('createFormsBlocked', 0)} nahi khule")
    if summary.get("newFields"):
        print(f"             {summary['newFields']} field sirf create form me "
              f"mile (list me nahi the)")
    if summary.get("discovered"):
        print(f"  Sidebar  : {summary.get('pagesFromSidebar', 0)} page mile "
              f"(config me {summary.get('pagesInConfig', 0)} the), "
              f"{len(summary.get('hiddenInSidebar') or [])} chhupe hue")
    print(f"  Element  : {summary['elements']}")
    print(f"  Settings : {summary['controlRoomSettings']} "
          f"({summary['controlRoomDropdowns']} dropdown)")
    if summary.get("settingsChanged"):
        print(f"  Settings : {summary['settingsChanged']} badli gayin "
              f"(restore-settings.bat se wapas)")
    print(f"  Samay    : {summary['seconds']}s")
    print(f"  Haal     : {summary['status']}")
    print(f"\n  {OUT / 'metadata.json'}")
    print(f"  {OUT / 'crawl-summary.json'}")
    print("=" * 56)

    sys.exit(0 if summary["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
