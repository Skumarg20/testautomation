"""
Har screen khulti hai ya nahi -- ek-ek karke check.

Ismein do samajhdari hai:
  1. Screens MENU ke hisaab se group hain. Sale ke 13 screens ek saath check
     honge, phir Purchase ke 12. Sidebar hamesha saamne hai, isliye beech me
     dashboard jaane ki zaroorat nahi -- isse aadha se zyada waqt bachta hai.
  2. Agle screen pe jaane se pehle khula form BAND kiya jata hai (Esc / Close),
     navigate karke nahi. Isse "page chhod rahe ho?" wala popup bhi nahi aata.

    python -m framework.screens_check
    python -m framework.screens_check --menu sale
    python -m framework.screens_check --only sale_bill,purchase_bill
"""
from __future__ import annotations

import argparse
import time
from collections import defaultdict

from playwright.sync_api import sync_playwright

from config.settings import settings
from framework import safety, netguard, event_recorder
from framework.browser import launch, describe_window
from framework.auth import login
from framework.safety import ModuleNotEnabled
from framework.screens import SCREENS, open_screen


def form_is_open(bp) -> bool:
    """Koi transaction form khula hai? (tab, Save button, ya Party Name field)"""
    try:
        return bool(bp.page.evaluate(r"""
          () => {
            const t = (document.body.innerText || '');
            const hasSave = [...document.querySelectorAll('button')]
              .some(b => /^(f10\s*\/?\s*end\s*)?save/i.test((b.innerText||'').trim()));
            const hasTab = !!document.querySelector('.nav-tabs .close, [class*="tab"] .close');
            return hasSave || hasTab || /Party Name/i.test(t);
          }
        """))
    except Exception:  # noqa: BLE001
        return False


def ensure_neutral(bp, verbose: bool = False) -> bool:
    """
    Agle screen se pehle app ko saaf haalat me lao -- aur CONFIRM karo.

    Pehle sirf band karne ki koshish hoti thi, check nahi hota tha. Isliye ek
    chhodkar ek screen fail ho rahi thi: khula form agli screen ko rok deta tha.
    """
    for attempt in range(3):
        # popup khula ho to pehle usse nipto
        if safety.read_modal(bp.page):
            if not safety.dismiss_modal(bp.page, verbose=verbose):
                safety.force_close_modal(bp.page, verbose=verbose)
            bp.page.wait_for_timeout(700)
        if not form_is_open(bp):
            return True
        close_open_form(bp)
        bp.page.wait_for_timeout(800)
        if safety.read_modal(bp.page):                   # Esc ke baad popup aata hai
            if not safety.dismiss_modal(bp.page, verbose=verbose):
                safety.force_close_modal(bp.page, verbose=verbose)
        bp.page.wait_for_timeout(600)

    # aakhri raasta -- dashboard pe jao
    if verbose:
        print("        form band nahi hua, dashboard se reset kar rahe hain")
    try:
        safety.force_close_modal(bp.page)
        bp.goto("/dashboard", check_auth=False)
        bp.page.wait_for_timeout(2000)
        if safety.read_modal(bp.page):
            safety.dismiss_modal(bp.page, verbose=verbose) or \
                safety.force_close_modal(bp.page, verbose=verbose)
            bp.page.wait_for_timeout(1200)
    except Exception:  # noqa: BLE001
        pass
    return not form_is_open(bp)


def why_failed(bp, key: str) -> str:
    """FAIL ka karan record karo -- andaza lagane ki jagah data."""
    try:
        info = bp.page.evaluate(r"""
          () => {
            const h = document.querySelector('h1, .mhead, .pageTitle');
            return {
              url: location.href,
              heading: h ? (h.innerText||'').trim().slice(0,60) : '(koi heading nahi)',
              menuOpen: !!document.querySelector('.collapse.show, ul.show, li.open'),
              formOpen: /Party Name/i.test(document.body.innerText||''),
              body: (document.body.innerText||'').replace(/\s+/g,' ').trim().slice(0,120),
            };
          }
        """)
        return (f"url={info['url']} | heading={info['heading']!r} | "
                f"menuOpen={info['menuOpen']} | formOpen={info['formOpen']}\n"
                f"        body: {info['body']}")
    except Exception as e:  # noqa: BLE001
        return f"(diagnosis fail: {e})"


def close_open_form(bp) -> None:
    """
    Khula transaction form band karo -- BINA navigate kiye.
    Save kabhi nahi dabate; sirf Esc / Close / X.
    """
    page = bp.page
    try:
        safety.audit_key("Escape", "close_open_form")
        page.keyboard.press("Escape")
        page.wait_for_timeout(900)
        safety.dismiss_modal(page)      # Counter Sale jaise screens Yes/No poochte hain
    except Exception:  # noqa: BLE001
        pass

    for label in ("Close", "Esc Close", "Cancel"):
        try:
            btn = page.get_by_role("button", name=label, exact=False).first
            if btn.is_visible(timeout=800):
                safety.guarded_click(btn, f"close:{label}", timeout=2000)
                page.wait_for_timeout(800)
                return
        except Exception:  # noqa: BLE001
            continue

    # tab ka chhota "x" (Sale Bill 1 ×)
    try:
        x = page.locator('.nav-tabs .close, [class*="tab"] .close').first
        if x.is_visible(timeout=600):
            safety.guarded_click(x, "tab.close_x", timeout=1500)
            page.wait_for_timeout(800)
    except Exception:  # noqa: BLE001
        pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--menu", help="sirf ek menu, jaise sale / purchase / master")
    ap.add_argument("--only", help="comma separated screen names")
    ap.add_argument("--via", default="menu", choices=["menu", "url"],
                    help="menu (default) = asli navigation test. url = sirf tez check.")
    args = ap.parse_args()

    wanted = dict(SCREENS)
    if args.menu:
        wanted = {k: v for k, v in wanted.items() if v.get("menu") == args.menu}
    if args.only:
        keep = {x.strip() for x in args.only.split(",")}
        wanted = {k: v for k, v in wanted.items() if k in keep}
    if not wanted:
        print("Koi screen match nahi hua.")
        return

    # menu ke hisaab se group -- ek menu ke saare screens ek saath
    groups: dict[str, list[str]] = defaultdict(list)
    for k, v in wanted.items():
        groups[v.get("menu") or "_direct"].append(k)

    settings.validate()
    run = settings.init_run("screens check")
    ok, bad, skipped = [], [], []
    diagnostics: dict[str, str] = {}
    t0 = time.time()

    with sync_playwright() as pw:
        browser, ctx = launch(pw)
        bp = login(ctx.new_page(), verbose=True)
        print(f"Window: {describe_window(bp.page)}")

        print(f"\n{len(wanted)} screens, {len(groups)} menus")
        print(f"Navigation: {args.via.upper()}"
              + ("  (menu ka asli rasta test ho raha hai)" if args.via == "menu"
                 else "  (sirf tez check -- menu test NAHI hoga)") + "\n")

        for menu, keys in groups.items():
            print(f"--- {menu.upper()} ({len(keys)}) ---")
            for key in keys:
                ensure_neutral(bp)        # <-- khulne se PEHLE saaf haalat
                status, reason = "FAIL", ""
                try:
                    good = open_screen(bp, key, verbose=False, prefer=args.via)
                    if not good:
                        # ek dobara mauka, poore reset ke baad
                        ensure_neutral(bp, verbose=True)
                        good = open_screen(bp, key, verbose=True, prefer=args.via)
                    if good:
                        status = "OK  "
                        ok.append(key)
                    else:
                        reason = why_failed(bp, key)
                        bad.append(key)
                        diagnostics[key] = reason
                except ModuleNotEnabled as e:
                    status = "SKIP"       # Control Room me band hai -- bug nahi
                    skipped.append(key)
                    diagnostics[key] = str(e)[:150]
                except Exception as e:  # noqa: BLE001
                    reason = f"{type(e).__name__}: {str(e)[:120]}"
                    bad.append(key)
                    diagnostics[key] = reason

                print(f"  {status}  {key}")
                if reason:
                    print(f"        {reason}")
                bp.screenshot(f"screen_{key}")
                ensure_neutral(bp)        # <-- khulne ke BAAD bhi saaf karo

        # suraksha ki report -- kya kuch roka gaya
        ev_path = event_recorder.report(bp.page, settings.ARTIFACTS / "events.log")
        del_path = safety.delete_report(bp.page, settings.ARTIFACTS / "delete_attempts.log")
        n_del = safety.delete_count(bp.page)
        if n_del:
            print(f"\n  !! DELETE confirmation {n_del} baar aayi -- har baar 'No' dabaya")
            print(f"     Kyun aayi, ye dekho: {del_path}")
        ng_path = netguard.report()
        if netguard.count():
            print(f"\n  !! {netguard.count()} DELETE request ROKI GAYIN -> {ng_path}")
        browser.close()

    mins = (time.time() - t0) / 60

    # natija file me bhi likh do
    lines = [f"SCREEN CHECK -- {settings.RUN_ID}",
             f"navigation: {args.via}",
             f"{len(ok)} khule | {len(bad)} nahi khule | {len(skipped)} skip (module OFF)",
             f"time: {mins:.1f} min", ""]
    lines += ["KHULE:"] + [f"  {k}" for k in ok]
    if bad:
        lines += ["", "NAHI KHULE:"] + [f"  {k}" for k in bad]
    if skipped:
        lines += ["", "CONTROL ROOM ME OFF:"] + [f"  {k}" for k in skipped]
    if diagnostics:
        lines += ["", "=" * 50, "KARAN (kyun fail hua):", ""]
        for k, v in diagnostics.items():
            lines += [f"[{k}]", f"  {v}", ""]
    (run / "screens_result.txt").write_text("\n".join(lines), encoding="utf-8")

    print(f"\n{'='*58}")
    print(f"  {len(ok)} khule | {len(bad)} nahi khule | {len(skipped)} skip (module OFF)")
    if bad:
        print(f"\n  Nahi khule : {bad}")
    if skipped:
        print(f"  Control Room me OFF: {skipped}")
    print(f"\n  Time: {mins:.1f} min")
    print(f"  Screenshots + screens_result.txt: {run}")
    print(f"{'='*58}")


if __name__ == "__main__":
    main()
