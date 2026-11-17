"""
Tools tab -- jitne kaam pehle batch file se hote the, wahi UI se.

Tester ko folder khol kar 20 bat file me se sahi wali dhoondhni padti thi,
aur output ek kaali khidki me aata tha jo band hote hi ud jata tha.
"""
import threading
import time

import pytest
from playwright.sync_api import sync_playwright

PORT = 8796


def _tab(ui, name):
    """Open a tab. Import / What it has learned / Maintenance live in the More menu."""
    if name in ("imp", "cat", "tools") and ui.locator("#moreMenu").is_hidden():
        ui.locator("#moreBtn").click()
    ui.locator(f'#tabs [data-tab="{name}"]').click()


@pytest.fixture(scope="module")
def ui():
    """
    Apna server aur browser. test_ui_render.py ka 'ui' doosri file me hai,
    aur pytest fixture file ke paar apne aap nahi milti -- isliye yahan
    apna banate hain (alag PORT par, taaki dono ek saath chal sakein).
    """
    from http.server import ThreadingHTTPServer
    from ui.server import Handler
    from config.settings import settings
    settings.USER = settings.USER or "qa@example.com"
    settings.PASSWORD = settings.PASSWORD or "x"

    srv = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    time.sleep(0.4)
    with sync_playwright() as pw:
        b = pw.chromium.launch(headless=True)
        pg = b.new_page(viewport={"width": 1366, "height": 760})
        pg.goto(f"http://127.0.0.1:{PORT}", wait_until="networkidle")
        pg.wait_for_timeout(900)
        yield pg
        b.close()
    srv.shutdown()


def _open_tools(ui):
    _tab(ui, "tools")
    ui.wait_for_timeout(700)


@pytest.fixture(autouse=True)
def _no_job_running():
    """
    Har test se pehle koi kaam chal na raha ho.

    Ek waqt me ek hi kaam chalta hai (jaan-boojh kar). Isliye pichhle test
    ka kaam agle ko "abhi chal raha hai" keh kar gira deta tha -- akele
    pass, saath me fail.
    """
    from ui import tools
    for j in list(tools.JOBS.values()):
        if j["status"] == "running":
            tools.stop(j["id"])
    for _ in range(20):
        if not any(j["status"] == "running" for j in tools.JOBS.values()):
            break
        time.sleep(0.3)
    yield


def test_saare_kaam_UI_me_dikhte_hain(ui):
    _open_tools(ui)
    assert ui.locator(".tool").count() >= 10, "kuch kaam gayab hain"


def test_har_kaam_ke_saath_teen_baatein_likhi_hain(ui):
    """
    kya karta hai, kitni der, aur data badalta hai ya nahi.
    Aakhri baat sabse zaroori -- wo button ke saath likhi honi chahiye,
    kisi dastavez me chhupi nahi.
    """
    _open_tools(ui)
    for el in ui.locator(".tool").all():
        t = el.inner_text()
        assert len(t) > 60, f"parichay nahi: {t[:40]}"
        assert "read only" in t or "changes data" in t, \
            f"khatra likha hi nahi: {t[:40]}"
        assert ("sec" in t or "min" in t), f"samay nahi likha: {t[:40]}"


def test_crawler_sabse_upar_hai(ui):
    """Wahi sabse zyada chalega. Health check zaroori hai par roz nahi."""
    _open_tools(ui)
    assert "crawl" in ui.locator(".tool").first.inner_text().lower()


def test_data_badalne_wale_kaam_alag_dikhte_hain(ui):
    _open_tools(ui)
    assert ui.locator(".tag.w").count() >= 2, \
        "'changes data' wala nishaan kahin nahi"
    # settings ON karne wala vikalp peela hona chahiye
    assert ui.locator(".tool .opt.hot").count() >= 1


def test_crawler_ke_vikalp_aur_seema_dikhte_hain(ui):
    _open_tools(ui)
    assert ui.locator('[data-opt="crawler"]').count() == 2, "--enable/--resume"
    box = ui.locator('[data-arg="crawler"]')
    assert box.count() == 1 and box.input_value() == "90", "seema ka khaana"


def test_kaam_sach_me_chalta_hai_aur_output_dikhta_hai(ui):
    """
    Output ab screen par rehta hai. Pehle kaali khidki band hote hi ud
    jata tha, aur tester ko pata hi nahi chalta ki kya hua.
    """
    _open_tools(ui)
    ui.locator('[data-run="doctor"]').click()
    for _ in range(40):
        ui.wait_for_timeout(1000)
        if "running" not in ui.locator("#jobTitle").inner_text().lower():
            break
    log = ui.locator("#jobLog").inner_text()
    assert "Health Check" in log, log[:200]
    assert "Finished" in log, "khatam hone par kuch bataya hi nahi"


def test_ek_waqt_me_ek_hi_kaam(ui):
    """Do browser ek saath kholna ya do baar login karna dono ko gira deta hai."""
    from ui import tools
    a = tools.start("doctor")
    try:
        b = tools.start("doctor")
        assert "error" in b and "still running" in b["error"]
    finally:
        tools.stop(a["job"])


def test_chalta_hua_kaam_roka_ja_sakta_hai():
    """
    Crawl 45 minute ka hota hai. Beech me galti dikhe to rokne ka raasta
    hona chahiye -- warna tester browser hi band kar dega.
    """
    from ui import tools
    # Ek lamba kaam chahiye jise beech me roka ja sake
    r = tools.start("screens")
    assert "job" in r, r
    time.sleep(2)
    res = tools.stop(r["job"])
    assert res.get("status") == "stopped", res
    time.sleep(1)
    assert tools.status(r["job"])["status"] == "stopped"


def test_tools_par_bayan_menu_chhup_jata_hai(ui):
    """MargBooks ka menu sirf test list chunne ke kaam ka hai."""
    _open_tools(ui)
    assert ui.locator("#rail").is_hidden()
    _tab(ui, "run")
    ui.wait_for_timeout(400)
    assert ui.locator("#rail").is_visible()


def test_app_html_me_CSS_script_ke_andar_nahi_hai():
    """
    Ek baar CSS galti se <script> ke andar chali gayi thi -- poora JS mar
    gaya aur Tools tab khali dikha. Browser ne bas 'Unexpected token .'
    kaha, jisse kuch pata nahi chalta.
    """
    from pathlib import Path
    html = (Path(__file__).resolve().parent.parent.parent
            / "ui" / "app.html").read_text(encoding="utf-8")
    js = html[html.index("<script>") + 8: html.rindex("</script>")]
    bad = [l for l in js.split("\n")
           if l.startswith(".") and l.rstrip().endswith(("{", ";"))
           and "//" not in l]
    assert not bad, f"CSS script ke andar hai: {bad[:3]}"


def test_CSS_ke_naam_takrate_nahi_hain():
    """
    Maine ".grp" naam ki nayi class banayi -- par wahi naam pehle se rail
    ke menu node par tha (.mnode.grp). Meri class us par chadh gayi aur
    rail ke saare naam BADE AKSHAR me ho gaye ("Master" -> "MASTER").
    Do purane test toote, aur wajah dhoondhne me der lagi.

    CSS me naam ki takkar aise hi chupke se hoti hai -- na error aati
    hai, na kuch dikhta hai.
    """
    import re
    from pathlib import Path
    html = (Path(__file__).resolve().parent.parent.parent
            / "ui" / "app.html").read_text(encoding="utf-8")
    style = html[html.index("<style>"): html.index("</style>")]

    # har class ka apna niyam ek hi baar seedha define ho
    plain = re.findall(r"^\.([a-zA-Z][\w-]*)\s*\{", style, re.M)
    dupes = {c for c in plain if plain.count(c) > 1}
    assert not dupes, f"ye class do baar define hai: {sorted(dupes)}"


def test_dashboard_par_sab_ENGLISH_me_hai(ui):
    """
    Dashboard manual testers ke liye hai. Aadha English aadha Hinglish
    padhne me atakta hai -- aur naye aadmi ko samajh hi nahi aata.

    (Code ke comment Hinglish me hain, wo theek hai -- wo dashboard par
    nahi dikhte.)
    """
    HINGLISH = ("hai", "nahi", "karo", "chahiye", "kaam", "wala", "jata",
                "gaya", "raha", "dobara", "hota", "milta", "chalta",
                "sakta", "bina", "padhta", "kholta", "batata")
    bad = []
    for tab in ("run", "new", "imp", "cat", "tools", "hist", "env"):
        _tab(ui, tab)
        ui.wait_for_timeout(500)
        # The job output box is raw program output, not wording we write.
        shown = ui.evaluate("""(id) => {
            const c = document.getElementById(id).cloneNode(true);
            c.querySelectorAll('#jobLog').forEach(e => e.remove());
            return c.innerText;
        }""", f"tab-{tab}")
        for line in shown.split("\n"):
            t = line.strip()
            if len(t) < 12:
                continue
            hits = [w for w in HINGLISH
                    if f" {w} " in f" {t.lower()} " or t.lower().endswith(f" {w}")]
            if len(hits) >= 2:
                bad.append(f"{tab}: {t[:70]}")
    _tab(ui, "run")
    assert not bad, "dashboard par Hinglish:\n  " + "\n  ".join(bad[:8])


def test_test_case_ke_naam_bhi_english_hain():
    """Library me jo case bundled hain, wo bhi tester hi padhta hai."""
    from framework.case_loader import load_all
    HINGLISH = ("hai", "nahi", "chahiye", "hona", "karne", "wali", "wala")
    bad = [c.title for c in load_all()
           if sum(1 for w in HINGLISH if f" {w} " in f" {c.title.lower()} ") >= 2]
    assert not bad, f"ye title Hinglish me hain: {bad}"
