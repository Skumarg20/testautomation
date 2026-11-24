"""
MargBooks auto-login -- TEEN step hain (ye asli flow hai, dump se confirm kiya):

  Screen 1  accounts.margbooks.com  -> Mobile/Email ID  -> SIGN IN
  Screen 2  Password                -> CONTINUE
  Screen 3  Organisation List       -> company pe CLICK   <-- ye step miss ho raha tha
  Screen 4  books<N>.margbooks.com/dashboard -- ab app asli me khulta hai

Screen 3 kiye bina koi bhi page khaali grey aata hai.
"""
from __future__ import annotations

import threading
import time as _time
from contextlib import contextmanager

from playwright.sync_api import Page

from config.settings import settings
from framework import safety
from framework.browser import launch
from framework.base_page import BasePage

# Header pe ye text tab hi aata hai jab company chun li gayi ho -- yahi asli
# "app ready" ka pakka signal hai.
READY_MARKER = "Books From"

# Organisation List ka apna URL hai -- text dhoondhne se kahin zyada pakka.
# Pehle sirf "Organisation List" text dekhta tha, aur page dheere load hone par
# robot "anjaan screen" keh kar ruk jata tha.
ORG_URL_MARK = "user-company"
ORG_TEXTS = ("Organisation List", "Organisation Name")


class LoginBlocked(RuntimeError):
    pass


class LoginStopped(LoginBlocked):
    """The run was stopped by the user while it was signing in."""


# A time limit (and a stop signal) for one sign-in. Every wait inside login() asks _budget_ms() first, so a hanging
# MargBooks (hand-off page, Organisation List) ends the sign-in within the limit instead of adding up its many
# 60 s waits (a run was seen holding the shared login for 14 minutes). Thread-local: only the thread that called
# login() under time_limit() is limited; app_ready() elsewhere keeps its own timeout.
_limit = threading.local()


@contextmanager
def time_limit(seconds: float, stop=None):
    """Limit the login() calls in this block to `seconds` in all; `stop` (a threading.Event) ends them early."""
    old = getattr(_limit, "v", None)
    _limit.v = (_time.time() + float(seconds), float(seconds), stop)
    try:
        yield
    finally:
        _limit.v = old


def _budget_ms(want: int) -> int:
    """`want` ms, cut to what is left of the sign-in time limit. Raises when the limit is over or Stop was pressed."""
    v = getattr(_limit, "v", None)
    if not v:
        return want
    deadline, secs, stop = v
    if stop is not None and stop.is_set():
        raise LoginStopped("Stopped by the user while signing in.")
    left = int((deadline - _time.time()) * 1000)
    if left <= 0:
        raise LoginBlocked(f"Sign-in did not finish within {int(secs)} s (MargBooks did not open the company).")
    return max(1, min(int(want), left))


def _pause(page: Page, ms: int) -> None:
    page.wait_for_timeout(_budget_ms(ms))


def on_org_page(page: Page) -> bool:
    """Abhi Organisation List pe hain?"""
    if ORG_URL_MARK in (page.url or "").lower():
        return True
    try:
        body = page.inner_text("body") or ""
    except Exception:  # noqa: BLE001
        return False
    return any(t.lower() in body.lower() for t in ORG_TEXTS)


def wait_for_next_screen(page: Page, timeout_ms: int = 30000) -> str:
    """
    Password ke baad kya aaya, iska intezaar karo -- 'app' ya 'org' ya 'unknown'.

    Pehle main ek fixed wait ke baad turant faisla kar leta tha. Page dheere
    load ho to robot 'anjaan screen' keh kar ruk jata tha, jabki wo Organisation
    List par hi khada hota tha. Ab poll karte hain.
    """
    import time as _t
    deadline = _t.time() + timeout_ms / 1000
    while _t.time() < deadline:
        if app_ready(page, 1200):
            return "app"
        if on_org_page(page):
            # list ki rows aane do
            try:
                page.wait_for_selector("tr, [role='row']", timeout=6000)
            except Exception:  # noqa: BLE001
                pass
            return "org"
        _pause(page, 700)
    return "unknown"


def _safe_url(url: str) -> str:
    """The URL without its query string: the app's hand-off URL (login?c=...) carries the user's
    credentials Base64-encoded, and error messages end up in logs and on screen."""
    return str(url).split("?", 1)[0] + ("?..." if "?" in str(url) else "")


def _settle(page: Page, timeout_ms: int = 15000) -> None:
    """Wait for the network to go quiet, but do not fail when it never does.

    The live app (books6) keeps polling in the background, so "networkidle" sometimes never comes and the
    login died with a TimeoutError although it had worked. What decides success is checked right after
    (app_ready / the Organisation List), so a quiet network is only a nicety here."""
    timeout_ms = _budget_ms(timeout_ms)
    try:
        page.wait_for_load_state("networkidle", timeout=timeout_ms)
    except Exception:  # noqa: BLE001
        page.wait_for_load_state("domcontentloaded", timeout=_budget_ms(30000))


def app_ready(page: Page, timeout_ms: int = 20000) -> bool:
    """Company chuni ja chuki hai aur app poora load ho gaya hai?"""
    timeout_ms = _budget_ms(timeout_ms)
    try:
        page.get_by_text(READY_MARKER, exact=False).first.wait_for(
            state="visible", timeout=timeout_ms)
        return True
    except Exception:  # noqa: BLE001
        return False


def _arm_safety(page):
    """
    Organisation List pe har khatarnaak click rok do. Chaar layer:
      1. Har confirm/alert popup -> Cancel
      2. Delete/edit icons -> pointer-events: none
      3. Capture-phase listener -> table ke andar kisi bhi button/icon pe
         click ho to usko wahin nigal jao (page tak pahunchne hi mat do)
      4. Action column ke saare cells -> pointer-events: none
    """
    try:
        page.evaluate("""
          () => {
            if (window.__qaGuard) return;
            window.__qaGuard = true;

            // 3. sabse zaroori: koi bhi button/icon click capture phase me hi block
            document.addEventListener('click', (e) => {
              const t = e.target;
              if (!t || !t.closest) return;
              if (t.closest('[class*="del"], [class*="trash"], [id*="delete"], [id*="Griddelete"]')) {
                e.stopImmediatePropagation();
                e.preventDefault();
                console.warn('[QA GUARD] button click blocked');
              }
            }, true);

            const kill = () => {
              document.querySelectorAll(
                '[class*="del"], [class*="trash"], [id*="delete"], [id*="Griddelete"], button.mksBtn'
              ).forEach(el => { el.style.pointerEvents = 'none'; });
              // 4. har row ka AAKHRI cell (Action column) bhi band
              document.querySelectorAll('tr').forEach(tr => {
                const tds = tr.querySelectorAll('td');
                if (tds.length > 1) tds[tds.length - 1].style.pointerEvents = 'none';
              });
            };
            kill();
            new MutationObserver(kill).observe(document.body, {childList: true, subtree: true});
          }
        """)
    except Exception:  # noqa: BLE001
        pass


def _org_rows(page) -> list[str]:
    """Organisation List ke naam. Table-based aur div-based dono grid handle karta hai."""
    for sel in ("tr td:first-child", "tr th:first-child",
                '[role="row"] [role="cell"]:first-child',
                ".ag-row .ag-cell:first-child", "tbody tr > *:first-child"):
        try:
            vals = [t.strip() for t in page.locator(sel).all_inner_texts() if t.strip()]
            if vals:
                return vals
        except Exception:  # noqa: BLE001
            continue
    return []


def _dump_org_page(page):
    """Fail hone pe org page ka dhaancha file me likh do -- taki structure dikhe."""
    try:
        info = page.evaluate("""
          () => {
            const rows = [...document.querySelectorAll('tr, [role="row"], .ag-row')]
              .slice(0, 50)
              .map(r => [...r.children].slice(0,4).map(c => (c.innerText||'').trim()).join(' | '));
            const inputs = [...document.querySelectorAll('input,button')]
              .slice(0, 40)
              .map(e => `<${e.tagName.toLowerCase()}> id=${e.id} ph=${e.getAttribute('placeholder')||''} text=${(e.innerText||'').trim().slice(0,30)}`);
            return `URL: ${location.href}\n\n--- ROWS (${rows.length}) ---\n` +
                   rows.join('\n') + `\n\n--- CONTROLS ---\n` + inputs.join('\n');
          }
        """)
        (settings.ARTIFACTS / "org_list.txt").write_text(info, encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass


def _org_opened(bp: BasePage, ms: int) -> bool:
    """Did the click open the company? On a busy MargBooks the click works but the app takes longer than `ms` to
    load: once the page is no longer the Organisation List, give it up to a minute (like the hand-off page)."""
    page = bp.page
    if app_ready(page, ms):
        return True
    try:
        on_list = bp.page_has_text("Organisation List") or bp.page_has_text("Organisation Name")
    except Exception:  # noqa: BLE001  (page navigating)
        on_list = False
    return (not on_list) and app_ready(page, 60000)


def _pick_organisation(bp: BasePage, verbose: bool) -> bool:
    """
    Organisation List se company chuno.

    SAFETY:
      - Search box me kuch TYPE nahi karte (filter list khali kar deta tha).
      - Poori <tr> row pe kabhi click nahi karte.
      - Sirf pehle column ke cell pe click, aur wo bhi naam match hone par.
      - Click se pehle _arm_safety har button ko bekaar kar chuka hota hai.
    """
    page = bp.page
    company = settings.COMPANY.strip()
    if not company:
        raise LoginBlocked("Organisation List aa gayi par .env me MARGBOOKS_COMPANY khali hai.")

    _arm_safety(page)
    # rows render hone do -- turant padhne se list khali milti thi
    for _ in range(10):
        if _org_rows(page):
            break
        _pause(page, 700)
    _pause(page, 500)

    names = _org_rows(page)
    if verbose:
        print(f"  [login] list me {len(names)} organisations mile")
        print(f"  [login] dhoondh rahe hain: {company}")

    target = company.strip().lower()

    def matches(n: str) -> bool:
        a = n.strip().lower()
        return a == target or a.replace(" ", "") == target.replace(" ", "")

    cells = page.locator("tr td:first-child")
    for i in range(min(cells.count(), 60)):
        cell = cells.nth(i)
        try:
            txt = cell.inner_text()
            if not matches(txt):
                continue
            if verbose:
                print(f"  [login] row {i} match -> click (Organisation Name cell)")
            cell.scroll_into_view_if_needed()

            # (a) seedha cell pe click
            safety.guarded_click(cell, "org.name_cell", timeout=5000)
            _pause(page, 3500)
            if _org_opened(bp, 12000):
                return True

            # (b) double click -- kai ERP grids me row double-click se khulti hai
            if verbose:
                print("      single click se nahi khula, double click try...")
            safety.assert_safe(cell, "org.dblclick")
            safety.audit_click(cell, "org.dblclick")
            cell.dblclick(timeout=4000)
            _pause(page, 3500)
            if _org_opened(bp, 12000):
                return True

            # (c) row ka apna click handler seedha JS se chalao.
            #     Ye coordinates use nahi karta, isliye delete button chhoo hi
            #     nahi sakta -- sirf <tr> element ka handler fire hota hai.
            if verbose:
                print("      double click se bhi nahi, row handler JS se fire kar rahe hain...")
            cell.evaluate("""
              c => {
                const tr = c.closest('tr') || c.parentElement;
                const ev = new MouseEvent('click', {bubbles: true, cancelable: true, view: window});
                tr.dispatchEvent(ev);
                c.dispatchEvent(ev);
              }
            """)
            _pause(page, 4000)
            if _org_opened(bp, 12000):
                return True

            # (d) cell ke andar koi link/span ho to uspe
            try:
                inner = cell.locator("a, span, div").first
                safety.guarded_click(inner, "org.name_inner", timeout=3000)
                _pause(page, 3500)
                if _org_opened(bp, 12000):
                    return True
            except Exception:  # noqa: BLE001
                pass

            if verbose:
                print(f"      row {i}: chaar tareeke fail. URL abhi: {_safe_url(page.url)}")
                bp.screenshot(f"org_click_try_{i}")
        except Exception:  # noqa: BLE001
            # the cell went away mid-try: usually the company started to open (the list was replaced)
            if _org_opened(bp, 5000):
                return True
            continue

    # --- fallback: kisi bhi element pe jiska text bilkul company name ho ---
    if verbose:
        print("  [login] table me nahi mila, text se dhoondh rahe hain...")
    try:
        loc = page.get_by_text(company, exact=True)
        for i in range(min(loc.count(), 10)):
            el = loc.nth(i)
            try:
                # button/icon ke andar ho to chhod do
                bad = el.evaluate("e => !!e.closest('button, [class*=\"mksBtn\"], [class*=\"del\"]')")
                if bad:
                    continue
                el.scroll_into_view_if_needed()
                safety.guarded_click(el, "org.by_text", timeout=4000)
                _pause(page, 4000)
                if app_ready(page):
                    return True
            except Exception:  # noqa: BLE001
                continue
    except Exception:  # noqa: BLE001
        pass

    # a slow MargBooks may still be opening the company after the last try
    if app_ready(page, 20000):
        return True
    # failure -> diagnosis ke liye poora page dump kar do
    bp.screenshot("login_org_pick_failed")
    _dump_org_page(page)
    raise LoginBlocked(
        f"'{company}' Organisation List me nahi mila (ya click kaam nahi kiya).\n"
        f"List me ye {len(names)} naam dikhe:\n  " + "\n  ".join(names[:30]) +
        f"\n\nIn me se EXACT naam .env ke MARGBOOKS_COMPANY me daalo.\n"
        f"Dekho: artifacts/login_org_pick_failed.png aur artifacts/org_list.txt"
    )


def sync_app_host(page: Page, verbose: bool = False) -> str | None:
    """
    Login ke baad app jis host pe khuli hai, wahi BASE_URL bana do.

    ASLI BUG: .env me books5 likha tha, par company login ke baad books4 pe
    khulti thi. Session cookie books4 ki hoti hai, isliye jab bhi koi code
    `bp.goto("/dashboard")` karta tha (crawler har page ke baad karta tha) wo
    books5 pe jaata tha -- wahan login nahi hota, aur Sign In page aa jata tha.
    Crawler ko laga "app mar gayi", dobara login kiya, aur wahi chakkar chalta
    raha.

    MargBooks ka host account/company ke hisaab se badalta hai
    (books<N>), isliye .env ke bharose rehna galat hai. Jahan login ne asli me
    pahunchaya, wahi sach hai.

    Wapas: naya BASE_URL, ya None agar kuch badla nahi.
    """
    from urllib.parse import urlparse
    u = urlparse(page.url or "")
    if u.scheme not in ("http", "https") or not u.netloc:
        return None
    # login domain ko app ka domain na maan lo
    if u.netloc == urlparse(settings.LOGIN_URL).netloc:
        return None
    origin = f"{u.scheme}://{u.netloc}"
    old = settings.BASE_URL
    if origin.rstrip("/") == (old or "").rstrip("/"):
        return None
    # class aur instance dono par -- warna instance ki purani value dhak leti hai
    type(settings).BASE_URL = origin
    settings.BASE_URL = origin
    from framework import logbook
    logbook.write("execution", "app_host_fixed", "warn", was=old, now=origin)
    if verbose:
        print(f"  [login] app host alag nikla: {old} -> {origin} "
              f"(.env ki value galat thi, asli wala use ho raha hai)")
    return origin


def login(page: Page, verbose: bool = False) -> BasePage:
    bp = BasePage(page)

    # Window screen me fit hai? Nahi to theek karo. Ye har flow me hota hai
    # kyunki har flow login se guzarta hai.
    try:
        from framework.browser import fit_window
        fit_window(page, verbose=True)     # hamesha dikhao, artifacts/window.txt me bhi
    except Exception:  # noqa: BLE001
        pass
    # Dialog handling: delete/remove wale popup CANCEL, baaki ACCEPT.
    # (Pehle sab cancel karte the -- usse "company kholein?" wala confirm bhi
    #  cancel ho jata tha aur login aage nahi badhta tha.)
    def _on_dialog(d):
        msg = (d.message or "").lower()
        danger = any(w in msg for w in ("delete", "remove", "permanently", "hata", "mita"))
        print(f"  [dialog] {'CANCEL' if danger else 'OK'}: {d.message[:90]}")
        d.dismiss() if danger else d.accept()

    page.on("dialog", _on_dialog)

    def say(m):
        if verbose:
            print(f"  [login] {m}")

    # optional saved session
    if settings.USE_SAVED_SESSION:
        bp.goto(f"{settings.BASE_URL}/dashboard")
        _pause(page, 2500)
        if app_ready(page, 6000):
            say("saved session chal gaya")
            sync_app_host(page, verbose=verbose)
            return bp

    # --- 1. Mobile / Email ---
    say(f"opening {settings.LOGIN_URL}")
    bp.goto(settings.LOGIN_URL)
    _settle(page)
    if verbose:
        bp.screenshot("login_1_signin")

    say(f"user = {settings.USER}")
    bp.fill("login.username", settings.USER)
    bp.click("login.submit")
    _pause(page, 3500)
    if verbose:
        bp.screenshot("login_2_password")

    # --- 2. Password / PIN ---
    if bp.is_visible("login.password", timeout_ms=6000):
        secret = settings.PIN or settings.PASSWORD
        if not secret:
            raise LoginBlocked("Password screen aa gayi par .env me PASS/PIN nahi hai")
        say("password bhar rahe hain -> CONTINUE")
        bp.fill("login.password", secret)
        bp.click("login.continue")
        _settle(page)
        _pause(page, 4000)
    elif bp.page_has_text("OTP") and not bp.page_has_text("Login With OTP"):
        bp.screenshot("login_otp_blocked")
        raise LoginBlocked(
            "MargBooks OTP maang raha hai -- SMS ka code robot padh nahi sakta.\n"
            "Fix: 'Set My PIN' se PIN banao, phir .env me MARGBOOKS_PIN=xxxx daalo."
        )

    if verbose:
        bp.screenshot("login_3_org_list")   # fail ho to bhi rukega nahi

    # --- 3. Organisation List (ye step pehle miss ho raha tha) ---
    # After sign-in the app passes through its own hand-off page (<app>/login?c=...) before the dashboard.
    # On a slow server it stays there for a while; that is not an unknown screen, so wait for the app.
    if not app_ready(page, 6000) and "/login?c=" in page.url and "accounts." not in page.url:
        app_ready(page, 60000)
        # Busy server (several logins at the same moment): the hand-off page can hang. Loading it again
        # usually finishes the sign-in; seen when 8 Studio runs logged in together.
        for _ in range(2):
            if app_ready(page, 3000) or "/login" not in page.url:
                break
            say("hand-off page hangs -> loading it again")
            try:
                page.reload(wait_until="domcontentloaded", timeout=_budget_ms(60000))
            except Exception:  # noqa: BLE001
                pass
            _settle(page)
            app_ready(page, 60000)
    if not app_ready(page, 6000):
        if bp.page_has_text("Organisation List") or bp.page_has_text("Organisation Name"):
            _pick_organisation(bp, verbose)
        else:
            bp.screenshot("login_unknown_screen")
            raise LoginBlocked(
                f"Anjaan screen pe atke hain: {_safe_url(page.url)}\n"
                f"artifacts/login_unknown_screen.png dekho."
            )

    if not app_ready(page):
        bp.screenshot("login_not_ready")
        raise LoginBlocked(
            f"Company chun li par app load nahi hua ('{READY_MARKER}' nahi mila).\n"
            f"URL: {_safe_url(page.url)} -- artifacts/login_not_ready.png dekho."
        )

    # Asli host pakdo -- is se PEHLE koi bhi bp.goto("/...") galat host pe jayega
    sync_app_host(page, verbose=True)

    if verbose:
        bp.screenshot("login_4_ready")
        say(f"READY -> {_safe_url(page.url)}")

    if settings.USE_SAVED_SESSION:
        page.context.storage_state(path=str(settings.STORAGE_STATE))
    return bp


def check():
    """python -m framework.auth --check"""
    from playwright.sync_api import sync_playwright

    settings.validate()
    settings.init_run("login check")
    print(f"\nLogin URL : {settings.LOGIN_URL}")
    print(f"App URL   : {settings.BASE_URL}")
    print(f"User      : {settings.USER}")
    print(f"Company   : {settings.COMPANY or '(KHALI -- ye zaroori hai!)'}\n")

    with sync_playwright() as pw:
        browser, ctx = launch(pw)
        page = ctx.new_page()
        try:
            login(page, verbose=True)
            print(f"\n*** LOGIN + COMPANY SELECT SUCCESS ***\n{_safe_url(page.url)}")
        except Exception as e:
            print(f"\n*** FAIL ***\n{e}")
        finally:
            page.wait_for_timeout(3000)
            print(f"\nScreenshots: {settings.ARTIFACTS}")
            browser.close()


if __name__ == "__main__":
    check()
