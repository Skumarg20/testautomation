"""
UI ka asli browser me test.

Ye offline UI-test se alag hai: wo API check karta hai, ye dekhta hai ki page
sach me BANTA hai -- rail bharti hai, menu click kaam karta hai, koi JS error
nahi aata, aur CSS ki class aapas me nahi takratin.

CSS collision ek baar ho chuki hai: alert box aur tape-line dono '.warn'
kehlate the, aur alert ka amber background tape par chadh gaya tha.
"""
import json
import threading
import time

import pytest
from playwright.sync_api import sync_playwright

PORT = 8794
BASE = f"http://127.0.0.1:{PORT}"


def _tab(ui, name):
    """Open a tab. Import / What it has learned / Maintenance live in the More menu."""
    if name in ("imp", "cat", "tools") and ui.locator("#moreMenu").is_hidden():
        ui.locator("#moreBtn").click()
    ui.locator(f'#tabs [data-tab="{name}"]').click()


@pytest.fixture(scope="module")
def ui():
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
        pg = b.new_page(viewport={"width": 1366, "height": 720})
        errs = []
        pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
        pg.on("pageerror", lambda e: errs.append(f"pageerror: {e}"))
        pg.goto(BASE, wait_until="networkidle")
        pg.wait_for_timeout(900)
        pg.errors = errs
        yield pg
        b.close()
    srv.shutdown()


@pytest.fixture(autouse=True)
def _reset(ui):
    # Rail ab Tools/Settings/History par chhup jata hai. Pichhla test
    # wahan chhod de to agla "rail nahi mila" kehta hai -- akele pass,
    # saath me fail. Isliye har test Run tab se shuru hota hai.
    """
    Har test ko SAAF shuruaat do.

    Ye tests ek hi page share karte hain (naya browser har baar kholna bahut
    dheema hoga). Par uska matlab ye hai ki pichhle test ki chhodi hui haalat
    agle ko gira sakti hai -- khula modal tab ke click ko hi rok deta tha.

    Akele chalane par pass, saath me fail: aisa bug dhoondhna sabse mushkil
    hota hai. Isliye har test se pehle sab band kar dete hain.
    """
    try:
        ui.keyboard.press("Escape")
        ui.evaluate("""() => {
            const s = document.getElementById('envScrim');
            if (s) s.hidden = true;
        }""")
        _tab(ui, "run")
        ui.wait_for_timeout(200)
    except Exception:  # noqa: BLE001
        pass
    yield


def test_page_bina_JS_error_ke_chalta_hai(ui):
    assert not ui.errors, f"console errors: {ui.errors}"


def test_side_rail_me_MargBooks_ka_menu_hai(ui):
    """Tester ke dimaag me sidebar hota hai, flat list nahi."""
    labels = ui.locator("#rail .mnode .lbl").all_inner_texts()
    for must in ("Master", "Sale", "Purchase", "Item", "Ledger"):
        assert any(must == l.strip() for l in labels), f"'{must}' rail me nahi"
    assert ui.locator("#rail .mnode").count() > 30


def test_menu_pe_click_karne_se_uska_naam_upar_aata_hai(ui):
    """
    Library ab khali hai, isliye kisi menu item par test hon ye zaroori
    nahi. Par click karne par uska naam upar aana chahiye aur list usi ki
    dikhni chahiye.
    """
    ui.locator("#expAll").click(); ui.wait_for_timeout(300)
    ui.locator('#rail [data-pick="master.inventory.item"]').click()
    ui.wait_for_timeout(400)
    # Naam MENU se aana chahiye, tests se nahi -- warna jis item par koi
    # test na ho wahan "Selected" aa jata hai.
    title = ui.locator("#listTitle").inner_text().lower()
    assert "item" in title, f"heading me menu ka naam nahi: {title!r}"


def test_menu_chunne_par_heading_do_baar_nahi_dikhta(ui):
    """Panel ki heading me menu ka naam pehle se hai -- list me dobara bekaar."""
    ui.locator("#expAll").click(); ui.wait_for_timeout(300)
    ui.locator('#rail [data-pick="master.inventory.item"]').click()
    ui.wait_for_timeout(400)
    assert ui.locator("#tlist .grp-head").count() == 0


def test_tape_khali_hone_par_bhi_kuch_kehti_hai(ui):
    """Kaali khaali dabba kuch nahi batata. Empty state kaam ka hona chahiye."""
    _tab(ui, "run")
    ui.wait_for_timeout(300)
    txt = ui.locator("#tape").inner_text()
    assert "Nothing running" in txt
    assert "press Run" in txt


def test_har_tab_khulta_hai(ui):
    for tab in ("new", "imp", "cat", "hist", "env", "run"):
        _tab(ui, tab)
        ui.wait_for_timeout(350)
        assert ui.locator(f"#tab-{tab}").is_visible(), f"{tab} tab nahi khula"
    assert not ui.errors, ui.errors


def test_plain_language_se_steps_ban_jate_hain(ui):
    _tab(ui, "new")
    ui.wait_for_timeout(300)
    ui.locator("#exBtn").click()
    ui.wait_for_timeout(200)
    ui.locator("#convBtn").click()
    ui.wait_for_timeout(1500)
    n = ui.locator("#steps .srow:not(.shead)").count()
    assert n >= 5, f"sirf {n} step bane"
    assert "step" in ui.locator("#convMsg").inner_text()


def test_steps_ke_saare_column_screen_me_aate_hain(ui):
    """1366px pe Value ka column kat raha tha."""
    _tab(ui, "new")
    ui.wait_for_timeout(300)
    box = ui.locator("#steps .srow:not(.shead) .v").first.bounding_box()
    page_w = ui.viewport_size["width"]
    assert box and box["x"] + box["width"] <= page_w, \
        f"Value column screen se bahar: {box}"


def test_CSS_class_aapas_me_nahi_takratin(ui):
    """
    '.warn' do cheezon ke liye use ho raha tha -- alert box aur tape ki line.
    Alert ka amber background tape par chadh gaya tha.
    """
    html = ui.content()
    assert 'class="warn"' not in html, "'.warn' box dobara aa gaya"
    bg = ui.evaluate("""() => {
        const d = document.createElement('div');
        d.className = 'tl warn';
        document.body.appendChild(d);
        const c = getComputedStyle(d).backgroundColor;
        d.remove();
        return c;
    }""")
    assert bg in ("rgba(0, 0, 0, 0)", "transparent"), \
        f"tape ki warn line par background chadh gaya: {bg}"


def test_UI_ka_text_english_me_hai(ui):
    import re
    HINGLISH = ["chalao", "chuno", "dabao", "karo", "kahan", "naya", "purane",
                "juda nahi", "koi nahi", "milta", "dikhega", "tumhara"]
    body = ui.locator("body").inner_text()
    # test ke naam Hinglish me hain -- wo data hai, UI nahi
    chrome = "\n".join([
        ui.locator("#tabs").inner_text(),
        ui.locator("#rail").inner_text(),
        ui.locator("#runHint").inner_text(),
        ui.locator("#tape").inner_text(),
    ])
    found = [w for w in HINGLISH if re.search(rf"\b{w}\b", chrome, re.I)]
    assert not found, f"UI me Hinglish shabd: {found}"


# ---------- rail expand / collapse ----------

def _visible_nodes(pg):
    return pg.locator("#rail .mnode:visible").count()


def test_rail_collapse_aur_expand_hota_hai(ui):
    """
    Sidebar me 50+ item hain. Sab khule rehne se dhoondhna mushkil ho jata hai.
    """
    ui.locator("#colAll").click(); ui.wait_for_timeout(300)
    shut = _visible_nodes(ui)
    ui.locator("#expAll").click(); ui.wait_for_timeout(300)
    open_ = _visible_nodes(ui)
    assert shut < open_, f"collapse kaam nahi kiya ({shut} vs {open_})"
    assert open_ > 40, f"expand ke baad sirf {open_} node"
    assert shut < 15, f"collapse ke baad bhi {shut} node dikh rahe"


def test_ek_group_alag_se_khol_sakte_hain(ui):
    ui.locator("#colAll").click(); ui.wait_for_timeout(250)
    before = _visible_nodes(ui)
    ui.locator('[data-toggle="master"]').first.click()
    ui.wait_for_timeout(300)
    assert _visible_nodes(ui) > before
    # dobara click -> band
    ui.locator('[data-toggle="master"]').first.click()
    ui.wait_for_timeout(300)
    assert _visible_nodes(ui) == before


def test_group_band_hone_par_bhi_uska_naam_dikhta_hai(ui):
    """
    Band group ka naam aur (jahan test hon) ginti dikhni chahiye -- warna
    tester ko har group khol kar dhoondhna padega.

    Ginti sirf wahan aati hai jahan test hain. Library khali ho to sirf
    "All tests" par aayegi -- aur wahi sahi hai, khali group par "0" likhna
    bekaar shor hai.
    """
    ui.locator("#colAll").click(); ui.wait_for_timeout(300)
    txt = ui.locator("#rail").inner_text()
    for must in ("Master", "Sale", "Purchase"):
        assert must in txt, f"'{must}' band hone par gayab ho gaya"
    assert ui.locator("#rail .mcount").count() >= 1


# ---------- AI card ----------

def test_settings_me_AI_setup_hai(ui):
    """Tester ko .env kholne ki zaroorat na pade."""
    _tab(ui, "env")
    ui.wait_for_timeout(500)
    body = ui.locator("#tab-env").inner_text()
    assert "aistudio.google.com/apikey" in body, "key kahan se laayein, ye nahi likha"
    assert "Create API key" in body, "kadam nahi likhe"
    assert ui.locator("#aiKey").is_visible()
    assert ui.locator("#aiSave").is_visible()


def test_AI_key_password_field_me_hai(ui):
    """Key screen par khuli nahi dikhni chahiye."""
    _tab(ui, "env")
    ui.wait_for_timeout(400)
    assert ui.locator("#aiKey").get_attribute("type") == "password"


# ---------- file khud saaf hai ----------

def test_app_html_me_JS_do_baar_nahi_hai():
    """
    Ek baar poora JS block DOBARA chipak gaya tha (CSS aur JS dono me ek jaisa
    comment tha, aur splice galat jagah lag gaya). Page bilkul khali khul raha
    tha: 'Unexpected token'.
    """
    import re
    from pathlib import Path
    html = (Path(__file__).resolve().parent.parent.parent
            / "ui" / "app.html").read_text(encoding="utf-8")
    assert html.count("<script>") == 1 and html.count("</script>") == 1
    assert len(re.findall(r"const \$\$ = s =>", html)) == 1, "JS do baar hai"
    assert len(re.findall(r"async function loadMenu\(", html)) == 1
    assert len(re.findall(r"async function boot\(", html)) == 1


def test_jin_menu_me_test_hain_wo_shuru_se_khule_hote_hain(ui):
    """
    Jahan test hain wo group shuru se khula ho. Library khali hone par ye
    baat lagu hi nahi hoti -- tab sab band rehna hi theek hai.
    """
    ui.reload(wait_until="networkidle")
    ui.wait_for_timeout(1000)
    counts = ui.locator("#rail .mcount").count()
    if counts <= 1:                    # sirf "All tests" wali ginti
        ui.locator("#expAll").click(); ui.wait_for_timeout(300)
        assert ui.locator('#rail [data-pick="master.inventory.item"]').is_visible()
        return
    visible = [el for el in ui.locator("#rail [data-pick]").all()
               if el.is_visible()]
    assert len(visible) > 3, "jin menu me test hain wo khule nahi mile"


def test_control_room_ki_poori_list_dhoondhi_ja_sakti_hai(ui):
    """
    544 settings padhi jaati hain. Bina search ke wo list bekaar padi rehti
    hai -- koi 544 rows scroll karke nahi dhoondhega.
    """
    _tab(ui, "cat")
    ui.wait_for_timeout(700)
    assert ui.locator("#crSearch").is_visible(), "settings me search hi nahi hai"
    assert ui.locator("#crAll").count() == 1


# ---------- environment modal ----------

def _any_builtin() -> str:
    """
    Koi bhi bundled test ka id.

    Pehle yahan 'TC_SALE_001' likha tha. Library khali kar dene par wo test
    hi nahi raha aur char test toot gaye. Kisi khaas id par tikna galat hai
    -- library badalti rehti hai.
    """
    from ui import store
    for c in store.list_all():
        if not c.source_file.startswith("saved"):
            return c.id
    raise AssertionError("koi built-in test hai hi nahi")


def _open_settings(ui):
    _tab(ui, "env")
    ui.wait_for_timeout(500)


def test_environment_ki_saari_jaankari_list_me_dikhti_hai(ui):
    """
    ASLI BUG: user aur company hamesha '—' dikhte the, jabki .env me bhare
    the. environments.json purane version me bana tha jisme wo likhe hi nahi
    jate the, aur file ek baar ban jaye to us purani haalat me atki reh jati.
    """
    _open_settings(ui)
    txt = ui.locator("#envList").inner_text()
    for label in ("App", "Sign-in", "User", "Password", "Company"):
        assert label in txt, f"'{label}' list me nahi dikh raha"


def test_edit_par_modal_khulta_hai_aur_bhara_hua_aata_hai(ui):
    _open_settings(ui)
    ui.locator("#envList [data-edit]").first.click()
    ui.wait_for_timeout(350)
    assert not ui.locator("#envScrim").is_hidden(), "modal khula hi nahi"
    assert "Edit" in ui.locator("#envDlgTitle").inner_text()
    assert ui.locator("#eName").input_value(), "naam bhara hua nahi aaya"
    assert ui.locator("#eApp").input_value().startswith("http")


def test_add_par_khali_modal_aur_writes_ON(ui):
    """Writes ON -- warna data likhne wale test skip ho jate hain."""
    _open_settings(ui)
    ui.locator("#envNew").click()
    ui.wait_for_timeout(350)
    assert ui.locator("#envDlgTitle").inner_text() == "Add environment"
    assert ui.locator("#eName").input_value() == ""
    assert ui.locator("#eWrites").is_checked(), "writes default ON nahi hai"
    ui.locator("#envCancel").click()


def test_writes_ON_hone_par_chetavni_dikhti_hai(ui):
    """
    Writes ON matlab test ASLI data banayenge aur badlenge. Ye chhupana
    nahi chahiye -- default ON hai, isliye chetavni aur zaroori ho jati hai.
    """
    _open_settings(ui)
    ui.locator("#envNew").click()
    ui.wait_for_timeout(350)
    assert "real data" in ui.locator("#eWritesWarn").inner_text().lower()
    ui.locator("#eWrites").uncheck()
    ui.wait_for_timeout(150)
    assert ui.locator("#eWritesWarn").inner_text().strip() == ""
    ui.locator("#envCancel").click()


def test_password_khali_dikhta_hai_par_matlab_saaf_hai(ui):
    """
    Password kabhi wapas nahi bheja jata. Edit me khali dikhta hai -- par
    uska matlab "hata do" nahi, "jo hai wahi rehne do" hai. Ye label me
    likha hona chahiye, warna log samjhenge password ud gaya.
    """
    _open_settings(ui)
    ui.locator("#envList [data-edit]").first.click()
    ui.wait_for_timeout(350)
    assert ui.locator("#ePass").input_value() == ""
    label = ui.locator("#ePassLabel").inner_text().lower()
    assert "keeps" in label or "not set" in label, label
    ui.locator("#envCancel").click()


@pytest.mark.parametrize("how", ["escape", "backdrop", "cancel", "cross"])
def test_modal_char_tareeke_se_band_hota_hai(ui, how):
    _open_settings(ui)
    ui.locator("#envNew").click()
    ui.wait_for_timeout(300)
    if how == "escape":
        ui.keyboard.press("Escape")
    elif how == "backdrop":
        ui.mouse.click(60, 400)
    elif how == "cancel":
        ui.locator("#envCancel").click()
    else:
        ui.locator("#envClose").click()
    ui.wait_for_timeout(300)
    assert ui.locator("#envScrim").is_hidden(), f"{how} se band nahi hua"


def test_settings_me_dono_card_saath_dikhte_hain(ui):
    """Modal alag layer me hai -- kholne se page ka layout nahi hilna chahiye."""
    _open_settings(ui)
    before = ui.locator("#envList").bounding_box()
    ui.locator("#envNew").click()
    ui.wait_for_timeout(350)
    after = ui.locator("#envList").bounding_box()
    # 1px ka farak scrollbar se aa sakta hai -- wo khiskna nahi hai
    for k in ("x", "y", "width"):
        assert abs(before[k] - after[k]) <= 2, \
            f"modal khulte hi page khisak gaya ({k}: {before[k]} -> {after[k]})"
    ui.locator("#envCancel").click()


def test_app_html_me_koi_section_do_baar_nahi_hai():
    """
    HISTORY aur SETTINGS dono do baar aa gaye the -- kyunki maine index se
    kaat-jod kiya aur unka kram ulta tha. Do same id wale element hon to
    Playwright aur browser dono confuse hote hain.
    """
    import re
    from pathlib import Path
    html = (Path(__file__).resolve().parent.parent.parent
            / "ui" / "app.html").read_text(encoding="utf-8")
    names = re.findall(r"<!-- =+ ([A-Z ]+) =+ -->", html)
    dupes = [n for n in set(names) if names.count(n) > 1]
    assert not dupes, f"ye section do baar hain: {dupes}"
    assert html.count('<section') == html.count('</section>')
    for el_id in ("envList", "envNew", "aiKey", "envScrim", "tlist", "tape"):
        assert html.count(f'id="{el_id}"') == 1, f"id '{el_id}' ek se zyada baar"


# ---------- test edit / delete ----------

def _make_test(name="Pytest ka test"):
    from ui import store
    return store.save(name=name, description="check", module="masters",
                      author="pytest",
                      steps=[{"action": "open_screen", "target": "item"},
                             {"action": "assert_text", "value": "Item List"}])["id"]


def test_har_test_par_edit_ka_option_hai(ui):
    _tab(ui, "run")
    ui.wait_for_timeout(400)
    n_tests = ui.locator("#tlist .tc").count()
    assert ui.locator("[data-edit-test]").count() == n_tests, \
        "kuch test par Edit/Copy ka button nahi hai"


def test_built_in_test_MITAYA_nahi_ja_sakta(ui):
    """
    Built-in test agle update me wapas aa jayega -- use mitane ka option
    dena jhooth hoga. Isliye uspe delete ka button hi nahi hai.
    """
    _tab(ui, "run")
    ui.wait_for_timeout(400)
    bid = _any_builtin()
    row = ui.locator(f'.tc:has([data-edit-test="{bid}"])')
    assert row.locator("[data-del-test]").count() == 0
    assert "Copy" in row.locator("[data-edit-test]").inner_text()


def test_tester_ke_test_par_delete_dikhta_hai(ui):
    cid = _make_test("Delete dikhne ka test")
    try:
        ui.reload(wait_until="networkidle"); ui.wait_for_timeout(900)
        assert ui.locator(f'[data-del-test="{cid}"]').count() == 1
    finally:
        from ui import store
        store.delete(cid)


def test_edit_par_poora_test_bhar_kar_aata_hai(ui):
    cid = _make_test("Bharne ka test")
    try:
        ui.reload(wait_until="networkidle"); ui.wait_for_timeout(900)
        ui.locator(f'[data-edit-test="{cid}"]').click()
        ui.wait_for_timeout(600)
        assert cid in ui.locator("#newTitle").inner_text()
        assert ui.locator("#nName").input_value() == "Bharne ka test"
        assert ui.locator("#nDesc").input_value() == "check"
        assert ui.locator("#nWho").input_value() == "pytest"
        assert ui.locator("#steps .srow:not(.shead)").count() == 2
        assert "update" in ui.locator("#saveBtn").inner_text().lower()
    finally:
        from ui import store
        store.delete(cid)


def test_built_in_ka_COPY_banta_hai_overwrite_nahi(ui):
    """
    Built-in ko overwrite karne se badlav agle update me chup-chaap ud
    jayega. Isliye uski copy banti hai aur asli waisa hi rehta hai.
    """
    _tab(ui, "run")
    ui.wait_for_timeout(400)
    ui.locator(f'[data-edit-test="{_any_builtin()}"]').click()
    ui.wait_for_timeout(600)
    # heading CSS se BADE akshar me dikhti hai
    assert "copy" in ui.locator("#newTitle").inner_text().lower()
    assert "(copy)" in ui.locator("#nName").input_value()
    banner = ui.locator("#editBanner").inner_text().lower()
    assert "built-in" in banner and "copy" in banner
    ui.locator("#cancelEdit").click()


def test_edit_mode_me_upar_wala_box_bhram_nahi_deta(ui):
    """Placeholder "naya likho" kehta rehta tha jabki steps pehle se bhare the."""
    cid = _make_test("Placeholder test")
    try:
        ui.reload(wait_until="networkidle"); ui.wait_for_timeout(900)
        ui.locator(f'[data-edit-test="{cid}"]').click()
        ui.wait_for_timeout(500)
        ph = ui.locator("#nPlain").get_attribute("placeholder").lower()
        assert "loaded on the right" in ph, ph
        ui.locator("#cancelEdit").click()
        ui.wait_for_timeout(200)
        assert "sale bill" in ui.locator("#nPlain").get_attribute("placeholder").lower()
    finally:
        from ui import store
        store.delete(cid)


def test_delete_se_pehle_poochta_hai(ui):
    cid = _make_test("Poochne ka test")
    try:
        ui.reload(wait_until="networkidle"); ui.wait_for_timeout(900)
        ui.locator(f'[data-del-test="{cid}"]').click()
        ui.wait_for_timeout(400)
        assert not ui.locator("#delScrim").is_hidden()
        assert cid in ui.locator("#delWhat").inner_text()
        ui.locator("#delCancel").click()
        ui.wait_for_timeout(300)
        from ui import store
        assert store.get(cid), "Cancel dabane par bhi mit gaya"
    finally:
        from ui import store
        store.delete(cid)


def test_delete_sach_me_mitata_hai(ui):
    cid = _make_test("Mitne wala test")
    ui.reload(wait_until="networkidle"); ui.wait_for_timeout(900)
    ui.locator(f'[data-del-test="{cid}"]').click()
    ui.wait_for_timeout(400)
    ui.locator("#delGo").click()
    ui.wait_for_timeout(1000)
    from ui import store
    assert not store.get(cid), "delete ke baad bhi maujood hai"


def test_environment_list_me_writes_ka_toggle_hai(ui):
    """Poora modal kholne ki zaroorat na pade -- yahi setting sabse zyada badalti hai."""
    _open_settings(ui)
    assert ui.locator("#envList [data-writes]").count() >= 1
    label = ui.locator("#envList label:has([data-writes])").first.inner_text()
    assert "writes" in label.lower()


def test_add_modal_me_writes_pehle_se_ON_hai(ui):
    _open_settings(ui)
    ui.locator("#envNew").click()
    ui.wait_for_timeout(350)
    assert ui.locator("#eWrites").is_checked(), \
        "naya environment banate waqt writes ON hona chahiye"
    ui.locator("#envCancel").click()


def test_edit_par_bhi_writes_ON_dikhta_hai(ui):
    """Modal khulte hi checked -- add me bhi, edit me bhi."""
    _open_settings(ui)
    ui.locator("#envList [data-edit]").first.click()
    ui.wait_for_timeout(400)
    assert ui.locator("#eWrites").is_checked(), "edit me writes ON nahi hai"
    ui.locator("#envCancel").click()


def test_writes_OFF_se_ON_ho_raha_ho_to_SAAF_likhta_hai(ui):
    """
    Khatra ye tha: koi sirf URL theek karne Edit kholega, Save dabayega, aur
    writes bina jaane ON ho jayenge. Chup-chaap badalna galat hai -- isliye
    jab saved value OFF ho, notice dikhta hai.
    """
    from ui import envs
    envs.upsert({"name": "off-env", "login_url": "https://accounts.margbooks.com",
                 "app_url": "https://off.margbooks.com", "allow_writes": False})
    try:
        ui.reload(wait_until="networkidle"); ui.wait_for_timeout(900)
        _open_settings(ui)
        ui.locator('[data-edit="off-env"]').click()
        ui.wait_for_timeout(400)
        assert ui.locator("#eWrites").is_checked()
        notice = ui.locator("#eWritesChange")
        assert not notice.is_hidden(), "badlav ka notice dikha hi nahi"
        txt = notice.inner_text().lower()
        assert "writes off" in txt and "turns them on" in txt, txt
        ui.locator("#envCancel").click()
    finally:
        envs.remove("off-env")


def test_writes_pehle_se_ON_ho_to_notice_nahi_dikhta(ui):
    """Jab kuch badal hi nahi raha, to chetavni dena shor hai."""
    from ui import envs
    envs.upsert({"name": "on-env", "login_url": "https://accounts.margbooks.com",
                 "app_url": "https://on.margbooks.com", "allow_writes": True})
    try:
        ui.reload(wait_until="networkidle"); ui.wait_for_timeout(900)
        _open_settings(ui)
        ui.locator('[data-edit="on-env"]').click()
        ui.wait_for_timeout(400)
        assert ui.locator("#eWrites").is_checked()
        assert ui.locator("#eWritesChange").is_hidden(), \
            "kuch badal nahi raha, phir bhi notice dikh raha hai"
        ui.locator("#envCancel").click()
    finally:
        envs.remove("on-env")


# ---------- source scanner ----------

def test_scanner_card_hai(ui):
    _tab(ui, "cat")
    ui.wait_for_timeout(600)
    assert ui.locator("#scanPath").is_visible()
    body = ui.locator("#tab-cat").inner_text().lower()
    assert "node_modules" in body, "kaunse folder chhode jayenge, ye likha nahi"


def test_scanner_sach_me_scan_karta_hai(ui, tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "x.component.html").write_text(
        '<label for="txtFoo">Foo Name</label><input id="txtFoo">')
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "junk.js").write_text('<input id="junkField">')

    import framework.code_scanner as cs
    old = cs.FILE
    cs.FILE = tmp_path / "metadata.json"
    try:
        _tab(ui, "cat")
        ui.wait_for_timeout(500)
        ui.locator("#scanPath").fill(str(tmp_path))
        ui.locator("#scanBtn").click()
        ui.wait_for_timeout(1500)
        # scan ke turant baad panel refresh ho jata hai, isliye "Fields found"
        # wali table nahi, aakhri-scan wali line dikhti hai. Dono me se koi
        # bhi ho -- asli jaanch to file me hai.
        out = ui.locator("#scanOut").inner_text()
        assert "field" in out.lower(), out
        saved = str(cs.load())
        assert "txtFoo" in saved
        assert "junkField" not in saved, "node_modules bhi scan kar liya"
    finally:
        cs.FILE = old


# ---------- codegen import ----------

def test_recording_import_ka_box_hai(ui):
    _tab(ui, "imp")
    ui.wait_for_timeout(500)
    assert ui.locator("#cgScript").is_visible()
    assert "codegen" in ui.locator("#tab-imp").inner_text().lower()


def test_recording_steps_me_badal_jaati_hai(ui):
    _tab(ui, "imp")
    ui.wait_for_timeout(500)
    ui.locator("#cgScript").fill(
        "await page.goto('https://books5.margbooks.com/item-master/list');\n"
        "await page.getByRole('button', { name: 'Create/F2' }).click();\n"
        "await page.locator('#txtItemName').fill('QA Item');")
    ui.locator("#cgName").fill("From recording")
    ui.locator("#cgBtn").click()
    ui.wait_for_timeout(1200)
    out = ui.locator("#impOut").inner_text()
    assert "open_screen" in out and "QA Item" in out, out
    assert "3 step" in ui.locator("#cgMsg").inner_text()


# ---------- view code ----------

def test_test_ka_code_dekha_ja_sakta_hai(ui):
    _tab(ui, "run")
    ui.wait_for_timeout(400)
    ui.locator("[data-code-test]").first.click()
    ui.wait_for_timeout(600)
    assert not ui.locator("#codeScrim").is_hidden()
    code = ui.locator("#codeBody").inner_text()
    assert "@playwright/test" in code
    ui.locator("#codeDone").click()


def test_code_saaf_batata_hai_ki_run_YAML_se_hota_hai(ui):
    """
    Script dekh kar koi soch sakta hai ki wahi chal rahi hai. Asli run YAML
    se hota hai -- usme safety guard, control-room jaanch aur self-healing
    hain, jo plain script me nahi hote. Ye farak chhupana galat hoga.
    """
    _tab(ui, "run")
    ui.wait_for_timeout(400)
    ui.locator("[data-code-test]").first.click()
    ui.wait_for_timeout(600)
    both = (ui.locator("#codeBody").inner_text()
            + ui.locator("#codeScrim").inner_text()).lower()
    assert "yaml" in both, "ye farak kahin likha hi nahi"
    ui.locator("#codeDone").click()


# ---------- simple layout for non-technical testers ----------

def test_sirf_chaar_mukhya_tab_dikhte_hain_baaki_More_me(ui):
    """
    A layman should see four clear choices, not seven. The technical pages
    (Import, what the tool has learned, Maintenance) sit behind More.
    """
    top = [b.inner_text().strip() for b in ui.locator("#tabs > button").all()]
    assert top == ["Run tests", "Write a test", "Past results", "Settings"], top
    assert ui.locator("#moreMenu").is_hidden()
    ui.locator("#moreBtn").click()
    ui.wait_for_timeout(150)
    assert ui.locator("#moreMenu").is_visible()
    items = ui.locator("#moreMenu button").all_inner_texts()
    assert len(items) == 3
    ui.keyboard.press("Escape")
    ui.wait_for_timeout(150)
    assert ui.locator("#moreMenu").is_hidden(), "Escape should close More"


def test_more_menu_page_kholne_par_more_chamakta_hai(ui):
    _tab(ui, "tools")
    ui.wait_for_timeout(300)
    assert ui.locator("#tab-tools").is_visible()
    assert ui.locator("#moreBtn").get_attribute("aria-current") == "true"
    assert ui.locator("#moreMenu").is_hidden(), "menu should close after choosing"
    assert "set this tool up" in ui.locator("#tab-tools").inner_text()


def test_header_me_technical_shabd_nahi(ui):
    """No build numbers, 'env' or 'WRITES ON' in the header -- plain status only."""
    meta = ui.locator("#meta").inner_text().lower()
    assert "testing:" in meta
    assert "build" not in meta and "env " not in meta, meta
    assert "look only" in meta or "change data" in meta, meta


def test_test_card_par_id_aur_jargon_nahi(ui):
    ui.locator('#tabs [data-tab="run"]').click()
    ui.wait_for_timeout(300)
    card = ui.locator("#tlist .tc").first.inner_text()
    assert "TC_" not in card, "test ID should not clutter the card"
    low = card.lower()
    assert "signs out" not in low and "writes data" not in low


def test_how_it_works_guide_band_hota_hai_aur_yaad_rehta_hai(ui):
    ui.evaluate("() => localStorage.removeItem('howtoHidden')")
    ui.reload(wait_until="networkidle")
    ui.wait_for_timeout(600)
    assert ui.locator("#howto").is_visible()
    assert "Choose tests" in ui.locator("#howto").inner_text()
    ui.locator("#howtoHide").click()
    ui.reload(wait_until="networkidle")
    ui.wait_for_timeout(600)
    assert ui.locator("#howto").is_hidden(), "dismissed guide came back"
    ui.evaluate("() => localStorage.removeItem('howtoHidden')")


def test_natija_se_pehle_ek_saaf_vakya_aata_hai(ui):
    """After a run: one sentence saying whether it went well, before any numbers."""
    ui.evaluate("""() => drawResults([
        {id:'A', title:'One', outcome:'passed', seconds:1},
        {id:'B', title:'Two', outcome:'failed', seconds:2, error:'step 2 broke'}])""")
    v = ui.locator("#verdict")
    assert v.is_visible()
    assert "1 of 2" in v.inner_text() and "need" in v.inner_text()
    ui.evaluate("""() => drawResults([
        {id:'A', title:'One', outcome:'passed', seconds:1},
        {id:'C', title:'Three', outcome:'skipped'}])""")
    assert "No failures" in ui.locator("#verdict").inner_text()
    assert ui.locator("#legend").is_visible(), "Skipped needs a plain explanation"
    ui.evaluate("""() => drawResults([{id:'A', title:'One', outcome:'passed'}])""")
    assert "All 1 test passed" in ui.locator("#verdict").inner_text()
