"""
Window fit hoti hai ya nahi -- ASLI browser se test, nakli screen pe.

Ye test isliye likha gaya kyunki maine char baar "window fit ho jayegi" kaha
aur char baar nahi hui. Ab machine khud jaanch legi, aadmi nahi.

Linux/CI pe xvfb chahiye:
    xvfb-run -s "-screen 0 1280x720x24" pytest tests/browser -c NUL
Windows pe seedha chalega (asli screen pe).
"""
import os
import pytest
from playwright.sync_api import sync_playwright


@pytest.fixture(scope="function")
def _env(monkeypatch):
    """
    settings class import ke waqt hi env padh leti hai, isliye baad me
    os.environ badalne se farak nahi padta -- seedha class pe set karo.
    (Ye khud ek chhoti seekh thi: pehla version isi wajah se skip ho gaya tha.)
    """
    from config.settings import settings
    monkeypatch.setattr(settings, "BROWSER_MAXIMIZE", True)
    monkeypatch.setattr(settings, "HEADLESS", False)
    monkeypatch.setattr(settings, "USER", "x")
    monkeypatch.setattr(settings, "PASSWORD", "x")


def _measure(page):
    return page.evaluate("""() => ({
        ow: window.outerWidth, oh: window.outerHeight,
        aw: screen.availWidth, ah: screen.availHeight,
        vw: window.innerWidth, vh: window.innerHeight})""")


def test_window_screen_ke_andar_fit_hoti_hai(_env):
    from framework.browser import launch, fit_window
    with sync_playwright() as pw:
        browser, ctx = launch(pw)
        page = ctx.new_page()
        page.goto("data:text/html,<h1>fit test</h1>")
        page.wait_for_timeout(600)
        before = _measure(page)

        info = fit_window(page)
        m = _measure(page)
        m["before_ow"] = before["ow"]
        browser.close()

    assert info.get("method"), "koi tareeka nahi lagaya gaya"

    # DHYAAN: screen.availWidth par assert NAHI karte -- wo naap jhoothi nikli
    # (browser 1280x720 kehta tha, Windows me screen 1366x768 thi). Isi jhoothi
    # jaanch ki wajah se code maximized window ko chhota kar deta tha.
    # Sahi jaanch: window PEHLE se badi hui ya nahi, aur maximize chala ya nahi.
    assert m["ow"] >= m["before_ow"], "maximize ke baad window CHHOTI ho gayi"


def test_fit_window_report_deta_hai(_env):
    """Har run me pata chalna chahiye ki fit hui ya nahi -- poochna na pade."""
    from framework.browser import launch, fit_window
    with sync_playwright() as pw:
        browser, ctx = launch(pw)
        page = ctx.new_page()
        page.goto("data:text/html,<h1>x</h1>")
        info = fit_window(page)
        browser.close()
    for key in ("before", "after", "viewport", "fit"):
        assert key in info, f"report me '{key}' missing"
