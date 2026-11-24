from playwright.sync_api import expect

from pages.dashboard_page import DashboardPage


def btn(page):
    return page.get_by_role("main").get_by_role("button").filter(has=page.locator("strong"))

def period(page, opt):
    expect(btn(page)).to_be_visible(timeout=120000)
    btn(page).click()
    page.locator(opt).click()
    page.wait_for_timeout(5000)

def cards(page):
    return page.get_by_role("main").get_by_role("heading", level=4).all_inner_texts()

def test_p(page_as):
    page = page_as("chemist")
    DashboardPage(page).open()
    period(page, "#txtthisMonth"); print("THISMONTH", cards(page))
    period(page, "#txtlastmonth"); print("PREVMONTH", btn(page).inner_text(), cards(page))
    period(page, "#txtthisweek"); print("THISWEEK", btn(page).inner_text(), cards(page))
    page.reload(); expect(btn(page)).to_be_visible(timeout=120000); page.wait_for_timeout(5000)
    print("RELOAD", btn(page).inner_text(), cards(page))
    print("STORAGE", page.evaluate("() => Object.keys(localStorage).concat(Object.keys(sessionStorage))"))
    period(page, "#txtlast30d"); print("FINAL", btn(page).inner_text())
    page.get_by_role("link", name="Shortcut").click()
    panel = page.get_by_role("heading", name="SHORTCUT KEYS")
    expect(panel).to_be_visible()
    print("PANELTXT", panel.locator("xpath=..").inner_text()[:300])
    page.goto("/report/grossProfitLoss"); page.wait_for_timeout(6000)
    page.get_by_role("link", name="Dashboard", exact=True).click(); page.wait_for_timeout(4000)
    print("SIDEBAR ->", page.url)
