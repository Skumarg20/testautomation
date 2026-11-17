"""
Browser kholne ki EK jagah.

Pehle ye code paanch files me alag-alag padha tha, isliye viewport bhi paanch
jagah hardcode tha. Ab sab yahin se.

Window size ke teen tareeke (.env se):
  BROWSER_MAXIMIZE=true   -> screen jitni badi ho utni (default). Dekhne ke liye best.
  VIEWPORT_W / VIEWPORT_H -> pakka size. CI aur repeatable tests ke liye.
  HEADLESS=true           -> window dikhegi hi nahi, tab fixed size hi chalega.

Ye sirf sahulat ki baat nahi: MargBooks responsive hai. Chhoti screen pe
sidebar simat jata hai aur kuch button chhup jate hain -- to galat size pe
test jhootha fail de sakta hai.
"""
from __future__ import annotations

from playwright.sync_api import Playwright

from config.settings import settings
from framework import safety, netguard, event_recorder, net_wait


_SCREEN: tuple[int, int] | None = None


def detect_screen(pw=None) -> tuple[int, int]:
    """
    Asli screen ka naap -- OPERATING SYSTEM se poochte hain, browser se nahi.

    Pehle main headless browser khol kar screen.availWidth padhta tha. Wo
    bilkul galat tha: headless browser ki koi asli screen hoti hi nahi, wo
    apna nakli default (1280x720) bata deta hai. Isliye 1366x768 wali machine
    pe bhi galat naap aa raha tha.

    Windows pe taskbar chhod kar bacha hua "work area" lete hain, taaki window
    taskbar ke peeche na chali jaye.
    """
    global _SCREEN
    if _SCREEN:
        return _SCREEN

    # 1. Windows -- work area (taskbar ke bina)
    try:
        import ctypes
        from ctypes import wintypes
        user32 = ctypes.windll.user32
        user32.SetProcessDPIAware()
        rect = wintypes.RECT()
        SPI_GETWORKAREA = 0x0030
        if user32.SystemParametersInfoW(SPI_GETWORKAREA, 0, ctypes.byref(rect), 0):
            w, h = rect.right - rect.left, rect.bottom - rect.top
            if w > 400 and h > 300:
                _SCREEN = (w, h)
                return _SCREEN
        w = user32.GetSystemMetrics(0)
        h = user32.GetSystemMetrics(1)
        if w > 400:
            _SCREEN = (w, h - 48)          # taskbar ka andaza
            return _SCREEN
    except Exception:  # noqa: BLE001
        pass

    # 2. Mac / Linux -- tkinter
    try:
        import tkinter
        root = tkinter.Tk()
        root.withdraw()
        w, h = root.winfo_screenwidth(), root.winfo_screenheight()
        root.destroy()
        if w > 400:
            _SCREEN = (w, h - 60)
            return _SCREEN
    except Exception:  # noqa: BLE001
        pass

    # 3. kuch na chale to .env wala size
    _SCREEN = (settings.VIEWPORT_W, settings.VIEWPORT_H)
    return _SCREEN


def launch(pw: Playwright, slow_mo: int | None = None,
           record_video: bool = False):
    """(browser, context) do -- guard, toast-watcher aur sahi size ke saath."""
    maximize = settings.BROWSER_MAXIMIZE and not settings.HEADLESS

    args = ["--disable-blink-features=AutomationControlled"]
    if maximize:
        # Yahan koi naap NAHI dete.
        #
        # Teen baar naap ka hisaab lagaya aur teeno baar galat nikla:
        #   - headless browser ne nakli screen batai (1280x720)
        #   - Windows API ne galat work-area diya
        #   - Chrome ne --window-size ko viewport maan kar upar toolbar jod diya
        # Aur aakhir me browser (1280x720) aur Windows (1366x768) ki naap hi
        # aapas me alag nikli.
        #
        # Sahi hal: hisaab lagao hi mat. Window manager ko "maximize" bolo --
        # use pata hai screen kitni hai. Ye launch ke baad CDP se hota hai
        # (fit_window me), kyunki --start-maximized par bharosa nahi.
        args += ["--window-position=0,0"]

    browser = pw.chromium.launch(
        headless=settings.HEADLESS,
        slow_mo=settings.SLOWMO_MS if slow_mo is None else slow_mo,
        args=args,
    )

    state = (str(settings.STORAGE_STATE)
             if settings.USE_SAVED_SESSION and settings.STORAGE_STATE.exists() else None)

    kwargs = {}
    if record_video:
        kwargs["record_video_dir"] = str(settings.ARTIFACTS / "video")

    ctx = browser.new_context(
        storage_state=state,
        # viewport=None -> page window ke barabar ho jata hai (maximized)
        # viewport=None -> content window ke barabar phailega
        viewport=None if maximize else {"width": settings.VIEWPORT_W,
                                        "height": settings.VIEWPORT_H},
        ignore_https_errors=True,
        **kwargs,
    )
    safety.arm_context(ctx)      # click-level guard (browser ke andar)
    event_recorder.arm(ctx)      # har click/key ka record
    netguard.arm(ctx)            # network-level: delete request server tak jayegi hi nahi
    net_wait.arm(ctx)            # API kab tak chal rahi hai, uska hisaab
    return browser, ctx


def describe_window(page) -> str:
    """Abhi ka asli size -- report me likhne ke liye."""
    try:
        d = page.evaluate("""() => ({
            w: window.innerWidth, h: window.innerHeight,
            sw: screen.width, sh: screen.height,
            dpr: window.devicePixelRatio
        })""")
        return (f"viewport {d['w']}x{d['h']} | screen {d['sw']}x{d['sh']} "
                f"| zoom {d['dpr']}")
    except Exception:  # noqa: BLE001
        return "(size pata nahi chala)"


def fit_window(page, verbose: bool = False) -> dict:
    """
    Window ko maximize karo -- aur bas.

    YAHAN SABSE ZAROORI BAAT: maximize ke baad KOI JAANCH NAHI.

    Pehle main maximize karke phir `screen.availWidth` se jaanchta tha ki
    window fit hui ya nahi. Wo jaanch hi galat thi -- browser screen ko
    1280x720 batata hai jabki Windows me wo 1366x768 hai. Isliye sahi-sahi
    maximized window (1296x788) ko code ne "badi" samajh kar CHHOTA kar diya,
    aur user ko window pehle badi hoti phir sikudti dikhi.

    Maximize Windows karta hai. Windows apni hi screen se badi window nahi
    banayega. Us par bharosa karna hi sahi hai -- uske baad naapna bewakoofi.

    Naap wala fallback sirf tab chalta hai jab maximize KHUD FAIL ho jaye
    (jaise Linux pe jahan window manager hi na ho).
    """
    if settings.HEADLESS:
        return {"skipped": "headless"}
    if not settings.BROWSER_MAXIMIZE:
        return {"skipped": "BROWSER_MAXIMIZE=false"}

    def measure():
        try:
            return page.evaluate("""() => ({
                ow: window.outerWidth,  oh: window.outerHeight,
                vw: window.innerWidth,  vh: window.innerHeight,
                aw: screen.availWidth,  ah: screen.availHeight,
                docW: document.documentElement.scrollWidth})""")
        except Exception:  # noqa: BLE001
            return {}

    m0 = measure()
    out = {"before": f"{m0.get('ow')}x{m0.get('oh')}",
           "browser_kehta_hai_screen": f"{m0.get('aw')}x{m0.get('ah')}"}

    maximized = False
    try:
        cdp = page.context.new_cdp_session(page)
        win_id = cdp.send("Browser.getWindowForTarget")["windowId"]
        cdp.send("Browser.setWindowBounds",
                 {"windowId": win_id, "bounds": {"windowState": "maximized"}})
        page.wait_for_timeout(900)
        maximized = True
        out["method"] = "maximized (OS ne kiya)"
    except Exception as e:  # noqa: BLE001
        out["maximize_error"] = str(e)[:70]

    # Fallback SIRF tab jab maximize hi na chala ho
    if not maximized:
        m = measure()
        if m:
            try:
                cdp = page.context.new_cdp_session(page)
                win_id = cdp.send("Browser.getWindowForTarget")["windowId"]
                cdp.send("Browser.setWindowBounds", {
                    "windowId": win_id,
                    "bounds": {"left": 0, "top": 0,
                               "width": m["aw"], "height": m["ah"],
                               "windowState": "normal"}})
                page.wait_for_timeout(700)
                out["method"] = "explicit bounds (maximize fail hua tha)"
            except Exception as e:  # noqa: BLE001
                out["bounds_error"] = str(e)[:70]

    m = measure()
    out["after"] = f"{m.get('ow')}x{m.get('oh')}"
    out["viewport"] = f"{m.get('vw')}x{m.get('vh')}"
    out["fit"] = maximized          # OS ne maximize kiya = fit hai, bas.
    out["content_overflow"] = max(0, m.get("docW", 0) - m.get("vw", 0))

    try:
        settings.ARTIFACTS.mkdir(parents=True, exist_ok=True)
        (settings.ARTIFACTS / "window.txt").write_text(
            "\n".join(f"{k}: {v}" for k, v in out.items()), encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass

    if verbose:
        print(f"  [window] {out['before']} -> {out['after']}  ({out.get('method', '?')})"
              f"  viewport {out['viewport']}")
        if out["content_overflow"]:
            print(f"  [window] page {out['content_overflow']}px chauda hai window se"
                  f" -- ye MargBooks ka apna minimum width hai")
    return out
