"""
Window screen me fit hoti hai ya nahi -- SIRF yahi dekhta hai.
MargBooks login nahi karta, isliye 15 second me natija.

    python -m framework.window_check     (ya window-check.bat)
"""
from playwright.sync_api import sync_playwright

from config.settings import settings
from framework.browser import launch, fit_window


def main():
    run = settings.init_run("window check")
    print("\n=== WINDOW CHECK ===\n")

    with sync_playwright() as pw:
        browser, ctx = launch(pw)
        page = ctx.new_page()
        page.goto("data:text/html,<h1 style='font:40px sans-serif'>Window test</h1>")
        page.wait_for_timeout(800)

        before = page.evaluate("""() => ({ow: window.outerWidth, oh: window.outerHeight,
            aw: screen.availWidth, ah: screen.availHeight,
            sw: screen.width, sh: screen.height, dpr: window.devicePixelRatio})""")
        print(f"  Screen (browser ke hisaab se) : {before['sw']} x {before['sh']}")
        print(f"  Usable (taskbar ke bina)      : {before['aw']} x {before['ah']}")
        print(f"  Zoom                          : {before['dpr']}")
        print(f"  Window fit se pehle           : {before['ow']} x {before['oh']}")

        info = fit_window(page, verbose=False)
        after = page.evaluate("""() => ({ow: window.outerWidth, oh: window.outerHeight,
            vw: window.innerWidth, vh: window.innerHeight})""")
        print(f"  Tareeka                       : {info.get('method', 'kuch nahi')}")
        print(f"  Window fit ke baad            : {after['ow']} x {after['oh']}")
        print(f"  Page ke andar ki jagah        : {after['vw']} x {after['vh']}")

        # DHYAAN: screen.availWidth par faisla NAHI karte. Wo jhoothi nikli --
        # browser 1280x720 kehta hai jabki Windows me screen 1366x768 hai.
        # Maximize OS ne kiya hai, isliye wahi sach hai.
        if info.get("fit"):
            print(f"\n  MAXIMIZED -- Windows ne khud kiya, isliye screen me fit hai")
        else:
            print(f"\n  MAXIMIZE FAIL: {info.get('maximize_error', 'pata nahi')}")
        if before["aw"] != after["ow"]:
            print(f"  (Note: browser screen ko {before['aw']}x{before['ah']} batata hai,"
                  f" jo Windows ki naap se alag ho sakta hai -- isse farak nahi padta)")
        print("\n  Browser 10 second khula rahega -- APNI AANKHON SE DEKHO.")
        print("  Yahi asli faisla hai, koi number nahi.")
        page.wait_for_timeout(10000)
        browser.close()

    print(f"\n  Report: {run / 'window.txt'}")


if __name__ == "__main__":
    main()
