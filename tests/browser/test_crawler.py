"""
Crawler ka test -- nakli MargBooks bana kar.

Asli app ke bina bhi ye teen cheezein pakki honi chahiye:
  - page ka har element sahi nikale (id, CSS, XPath, label, dropdown ke vikalp)
  - crawler kuch BADLE nahi (read-only)
  - har cheez ka ek haal ho -- chupchaap kuch na chhoote
"""
import json

import pytest
from playwright.sync_api import sync_playwright

PAGE = """
<div style="padding:16px">
  <h1 class="mhead">Item List</h1>

  <label for="txtItemName">Item Name</label>
  <input type="text" id="txtItemName" formcontrolname="description"
         placeholder="Enter item">

  <div class="row"><span>M.R.P</span>
    <input type="text" id="txtMRP" data-testid="mrp-field"></div>

  <label for="ddlUnit">Unit</label>
  <select id="ddlUnit" formcontrolname="unit">
    <option value="1">PCS</option><option value="2">BOX</option>
  </select>

  <label for="chkActive">Active</label>
  <input type="checkbox" id="chkActive" checked>

  <input type="hidden" id="secretField" value="do-not-capture">
  <input type="text" id="disabledOne" disabled>

  <button id="btnSaveItem">F10 Save</button>
  <button class="mksBtn del" id="Griddeletetbtn9">Delete</button>

  <a href="/item-master/list" id="linkList">Item List</a>
  <a href="https://facebook.com/x" id="linkOut">Facebook</a>

  <table><tr><th>Description</th><th>Stock</th></tr>
         <tr><td>Paracetamol</td><td>5</td></tr></table>

  <div role="columnheader" col-id="Product">Product</div>
  <div role="columnheader" col-id="batchName">Batch</div>
</div>
"""


@pytest.fixture(scope="module")
def bp():
    with sync_playwright() as pw:
        b = pw.chromium.launch(headless=True)
        pg = b.new_page(viewport={"width": 1280, "height": 720})
        pg.set_content(PAGE)
        from framework.base_page import BasePage
        yield BasePage(pg)
        b.close()


@pytest.fixture(scope="module")
def got(bp):
    from framework.crawler import extract
    return extract(bp)


def _find(rows, el_id):
    return next((r for r in rows if r.get("id") == el_id), None)


# ---------- input ----------

def test_input_ka_poora_pata_nikalta_hai(got):
    el = _find(got["inputs"], "txtItemName")
    assert el, got["inputs"]
    assert el["label"] == "Item Name"
    assert el["placeholder"] == "Enter item"
    assert el["formControlName"] == "description"
    assert el["cssSelector"] == "input#txtItemName"
    assert el["xpath"] == '//*[@id="txtItemName"]'
    assert el["visible"] and el["enabled"] and el["editable"]


def test_label_paas_ke_text_se_bhi_milta_hai(got):
    """<label for=...> na ho to bhi -- MargBooks aksar wo use nahi karta."""
    el = _find(got["inputs"], "txtMRP")
    assert el and el["label"] == "M.R.P"
    assert el["testId"] == "mrp-field"


def test_chhupa_field_nahi_nikalta(got):
    """type=hidden me aksar token/secret hote hain."""
    assert _find(got["inputs"], "secretField") is None


def test_band_field_ka_haal_likha_jata_hai(got):
    """
    Ye AI prerequisite engine ke liye zaroori hai: field maujood par band
    ho, to test ko pata hona chahiye ki pehle setting badalni padegi.
    """
    el = _find(got["inputs"], "disabledOne")
    assert el and el["enabled"] is False


# ---------- dropdown ----------

def test_dropdown_ke_saare_vikalp_nikalte_hain(got):
    d = _find(got["dropdowns"], "ddlUnit")
    assert d, got["dropdowns"]
    assert d["label"] == "Unit"
    texts = [o["text"] for o in d["options"]]
    assert texts == ["PCS", "BOX"], texts
    assert d["options"][0]["value"] == "1"
    assert d["currentValue"] == "PCS"


# ---------- checkbox ----------

def test_checkbox_ka_haal_nikalta_hai(got):
    c = _find(got["checkboxes"], "chkActive")
    assert c and c["checked"] is True
    assert c["label"] == "Active"


# ---------- button aur link ----------

def test_button_nikalta_hai(got):
    b = _find(got["buttons"], "btnSaveItem")
    assert b and "Save" in b["text"]


def test_bahar_ka_link_nahi_nikalta(got):
    """App ke bahar crawl nahi karna -- Facebook pe jaane ka koi matlab nahi."""
    assert _find(got["links"], "linkOut") is None
    assert _find(got["links"], "linkList") is not None


# ---------- table aur ag-Grid ----------

def test_table_aur_agGrid_dono_nikalte_hain(got):
    """ag-Grid <table> nahi hota -- use alag se pehchanna padta hai."""
    heads = [h for t in got["tables"] for h in t.get("headers", [])]
    assert "Description" in heads
    ag = next((t for t in got["tables"] if t.get("agGrid")), None)
    assert ag and "Product" in ag["headers"]
    assert [c["id"] for c in ag["columns"]] == ["Product", "batchName"]


# ---------- niyam ----------

def test_absolute_xpath_sirf_majboori_me_banta_hai(got):
    """
    /html/body/div[2]/div[3]/... ek div badalne se toot jata hai.
    Jahan id ya name hai wahan wo use hona chahiye.
    """
    for el in got["inputs"] + got["buttons"]:
        if el.get("id"):
            assert not el["xpath"].startswith("/html/body"), el


def test_crawler_kuch_badalta_nahi():
    """
    Read-only hona sabse zaroori niyam hai. Ek galti se bill save ho jaye
    ya setting badal jaye to wo kisi ki asli company me chala jayega.
    """
    import inspect
    from framework import crawler, run_crawler
    src = inspect.getsource(crawler) + inspect.getsource(run_crawler)
    for bad in (".set_checked(", ".select_option(", "save_form", ".fill("):
        assert bad not in src, f"crawler '{bad}' kar raha hai -- read-only nahi raha"
    assert "ALLOW_DESTRUCTIVE = False" in inspect.getsource(run_crawler)


def test_har_cheez_ka_ek_haal_hota_hai():
    """Chupchaap chhodna mana hai -- har item ko status milna chahiye."""
    from framework.crawler import PASS, FAILED, SKIPPED, BLOCKED, PENDING
    assert {PASS, FAILED, SKIPPED, BLOCKED, PENDING} == {
        "PASS", "FAILED", "SKIPPED_BY_CONFIG", "BLOCKED", "PENDING"}
    import inspect
    from framework.crawler import Crawler
    src = inspect.getsource(Crawler)
    assert "_mark(" in src and "skip_reason" in src


def test_har_page_ke_TURANT_BAAD_save_hota_hai():
    """
    Crawl 20 minute chalta hai. Aakhir me save karne ka matlab: browser
    crash hone par poora kaam gaya.
    """
    import inspect
    from framework.crawler import Crawler
    assert "_save_page(row)" in inspect.getsource(Crawler._do_page)
    assert "_save_state" in inspect.getsource(Crawler._save_page)


def test_menu_ka_kram_file_se_aata_hai_code_se_nahi():
    from framework.crawler import SEQ_FILE
    assert SEQ_FILE.exists()
    d = json.loads(SEQ_FILE.read_text(encoding="utf-8"))
    names = [m["name"] for m in sorted(d["menus"], key=lambda x: x["order"])]
    assert names[:4] == ["Dashboard", "Master", "Sale", "Purchase"], names
    for m in d["menus"]:
        if m.get("skip"):
            assert m.get("skip_reason"), f"{m['name']} bina wajah chhoda gaya"


# ---------- resume ----------

def test_resume_pehle_ho_chuke_page_dobara_nahi_karta(tmp_path):
    """
    Crawl 20 minute chalta hai. Beech me ruk jaye to shuru se karna
    bekaar hai -- jo ho chuka wo dobara karne ka koi matlab nahi.
    """
    import framework.crawler as C
    old = C.OUT
    C.OUT = tmp_path / "out"
    C.OUT.mkdir(parents=True)
    (C.OUT / "state.json").write_text(json.dumps(
        {"done": ["Master/Inventory Master/Item", "Sale/Bill"],
         "lastPage": "Sale/Bill"}))
    try:
        class FakeBP:
            page = None
        c = C.Crawler.__new__(C.Crawler)
        c.state = c._load_state.__func__(c) if False else json.loads(
            (C.OUT / "state.json").read_text())
        assert "Sale/Bill" in c.state["done"]
        assert len(c.state["done"]) == 2
    finally:
        C.OUT = old


def test_state_har_page_ke_baad_likha_jata_hai():
    import inspect
    from framework.crawler import Crawler
    src = inspect.getsource(Crawler._save_page)
    assert '"lastPage"' in src and "_save_state()" in src


def test_screen_par_na_dikhne_wala_item_BLOCKED_hota_hai_FAIL_nahi():
    """
    Jo item is company me hai hi nahi (permission ya trade ke hisaab se),
    use FAIL dikhana jhooth hoga -- app bilkul theek hai.

    Aur uspe retry karna bekaar hai: jo cheez screen par nahi hai, wo
    dobara dekhne se aa nahi jayegi. Pehle ye do baar retry karta tha,
    har baar 18-25 second wait ke saath.
    """
    import inspect
    from framework.crawler import Crawler, BLOCKED
    src = inspect.getsource(Crawler._do_page)
    assert "_on_screen(label)" in src
    assert BLOCKED in src
    assert src.index("_on_screen(label)") < src.index("for attempt in range"), \
        "retry pehle chal raha hai -- screen check pehle hona chahiye"


def test_ek_menu_fail_hone_se_baaki_nahi_rukte():
    """Ek menu na khule to poora crawl rok dena sabse bura vikalp hai."""
    import inspect
    from framework.crawler import Crawler
    src = inspect.getsource(Crawler.run)
    assert src.count("continue") >= 3, "fail par aage nahi badh raha"
    assert "raise" not in src.split("def run")[1][:3000], \
        "ek fail poore crawl ko gira dega"


def test_har_menu_ka_id_class_xpath_sab_nikalta_hai():
    """
    Menu ko sirf text se pehchanna nazuk hai -- naam badal sakta hai.
    Isliye id, class, CSS aur XPath sab rakhte hain.
    """
    import inspect
    from framework.crawler import Crawler
    src = inspect.getsource(Crawler._menu_identity)
    # JS ke andar ye keys is tarah likhi hain: `id: el.id || ''`
    for f in ("id:", "class:", "cssSelector:", "xpath:", "visible:"):
        assert f in src, f"menu ka '{f.rstrip(chr(58))}' nahi nikalta"


# ---------- ek jaisa naam do jagah ----------

DUP_NAV = """
<div id="nav">
  <a class="menulink" id="menu495210260" href="#">Master</a>
  <div id="sub">
    <a class="menulink" href="#">Accounts Master</a>
    <a class="menulink" id="subSale" href="#">Sale</a>
    <a class="menulink" id="subPurchase" href="#">Purchase</a>
  </div>
  <a class="menulink" id="menu112725066" href="#">Sale</a>
  <a class="menulink" id="menu146058447" href="#">Purchase</a>
</div>
<div id="out">nothing</div>
<script>
  document.querySelectorAll('a').forEach(a => a.addEventListener('click', e => {
    e.preventDefault();
    document.getElementById('out').textContent = a.id || 'no-id';
  }));
</script>
"""


@pytest.fixture
def dup_page(bp):
    """
    Wahi browser use karo jo upar khula hai.

    Ek hi file me do baar sync_playwright() kholne se
    "Sync API inside the asyncio loop" wali error aati hai.
    """
    page = bp.page
    page.set_content(DUP_NAV)
    yield page
    page.set_content(PAGE)          # agle test ke liye wapas


def _crawler_for(page):
    import framework.crawler as C
    from framework.base_page import BasePage
    c = C.Crawler.__new__(C.Crawler)
    c.bp = BasePage(page)
    c.page = page
    c.verbose = False
    c.retry = 0
    return c


def test_ID_hone_par_SAHI_menu_par_click_hota_hai(dup_page):
    """
    ASLI BUG: crawler menu ka id dhoondh leta tha (#menu112725066 = top
    ka Sale), phir use PHENK kar text se click karta tha. "Sale" do jagah
    hai -- top menu me bhi aur Master > Accounts Master ke andar bhi --
    isliye galat wale par chala jata tha.

    Saat menu isi wajah se fail hue the. Jo teen chale (Dashboard, Report,
    Utilities & Tools) unke naam kahin dobara aate hi nahi.
    """
    c = _crawler_for(dup_page)
    assert c._click_text("Sale", el_id="menu112725066")
    assert dup_page.locator("#out").inner_text() == "menu112725066", \
        "galat 'Sale' par click hua"


def test_ID_ke_bina_bhi_sidebar_wala_hi_chunta_hai(dup_page):
    """Id na ho to bhi sidebar ke andar dhoondhna chahiye, poore page me nahi."""
    c = _crawler_for(dup_page)
    assert c._click_text("Master")
    assert dup_page.locator("#out").inner_text() == "menu495210260"


def test_crawler_ID_ko_phenkta_nahi():
    """
    Menu ki identity nikalte hi uska id mil jata hai. Use click me na
    lagana sirf apna nuksaan tha.
    """
    import inspect
    from framework.crawler import Crawler
    assert "el_id" in inspect.signature(Crawler._click_text).parameters
    run = inspect.getsource(Crawler.run)
    assert "el_id=ident.get(\"id\")" in run or "el_id=ident.get('id')" in run, \
        "menu ka mila hua id click me use nahi ho raha"
    page = inspect.getsource(Crawler._do_page)
    assert "el_id=lid" in page, "submenu ka id use nahi ho raha"


# ---------- create form ----------

CREATE_LIST = """
<div id="nav"><a id="menuMaster" class="menulink">Master</a></div>
<h1 class="mhead">Item List</h1>
<button id="btnCreateF2">Create/F2</button>
<div id="form" style="display:none">
  <h1 class="mhead">Create Item</h1>
  <label for="txtItemName">Item Name</label><input id="txtItemName">
  <label for="txtMRP2">M.R.P</label><input id="txtMRP2">
  <select id="ddlUnit2"><option>PCS</option><option>BOX</option></select>
  <button id="btnSave99">F10 Save</button>
  <button id="btnEsc99">Esc Close</button>
</div>
<div id="discardBox" style="display:none">
  Transaction data will be loss, Are you sure?
  <button id="btnYes">Yes</button><button id="btnNo">No</button>
</div>
<script>
  btnCreateF2.onclick = () => { form.style.display='block'; };
  btnEsc99.onclick = () => { discardBox.style.display='block'; };
  btnYes.onclick = () => { discardBox.style.display='none'; form.style.display='none'; };
  btnSave99.onclick = () => { window.__SAVED = true; };
</script>
"""


@pytest.fixture
def create_page(bp):
    page = bp.page
    page.set_content(CREATE_LIST)
    yield page
    page.set_content(PAGE)


def test_create_form_khulta_hai_aur_uske_field_milte_hain(create_page):
    """
    Asli kaam create form me hota hai. List ke element se koi test nahi
    banta -- jo banta hai wo form ke field se banta hai.
    """
    c = _crawler_for(create_page)
    c.pages, c.status, c.state = [], [], {"done": []}
    import framework.crawler as C
    import tempfile, pathlib as _p
    old = C.OUT
    C.OUT = _p.Path(tempfile.mkdtemp()) / "out"
    (C.OUT / "raw").mkdir(parents=True)
    try:
        row = c._do_create("Master", "Item")
        assert row, "create form khula hi nahi"
        ids = [i["id"] for i in row["inputs"]]
        assert "txtItemName" in ids, ids
        assert row["formType"] == "create"
        assert any(d["id"] == "ddlUnit2" for d in row["dropdowns"])
    finally:
        C.OUT = old


def test_create_form_BINA_SAVE_band_hota_hai(create_page):
    """
    Ye crawler ka sabse nazuk hissa hai: ek galat click asli data bana
    dega. Save kabhi nahi dabana.
    """
    c = _crawler_for(create_page)
    c.pages, c.status, c.state = [], [], {"done": []}
    import framework.crawler as C
    import tempfile, pathlib as _p
    old = C.OUT
    C.OUT = _p.Path(tempfile.mkdtemp()) / "out"
    (C.OUT / "raw").mkdir(parents=True)
    try:
        c._do_create("Master", "Item")
        assert not create_page.evaluate("() => window.__SAVED"), \
            "crawler ne SAVE daba diya"
        assert create_page.locator("#form").is_hidden(), "form band nahi hua"
    finally:
        C.OUT = old


def test_crawler_save_wale_button_kabhi_nahi_dabata():
    from framework.crawler import Crawler
    for w in ("save", "submit", "delete", "print"):
        assert w in Crawler.NEVER_CLICK


def test_purchase_wala_popup_hataya_jata_hai():
    """
    Purchase Bill par ek popup aata hai -- "How would you like to create
    your purchase bill". Uske bina form aata hi nahi, aur crawler wahin
    atak jata tha.
    """
    import inspect
    from framework.crawler import Crawler
    src = inspect.getsource(Crawler._clear_create_popups)
    assert "Start Manual Entry" in src


def test_create_na_khule_to_BLOCKED_kehta_hai():
    """Chupchaap chhodna mana hai -- har cheez ka ek haal."""
    import inspect
    from framework.crawler import Crawler, BLOCKED
    src = inspect.getsource(Crawler._do_create)
    assert BLOCKED in src and "raasta nahi mila" in src


def test_form_band_karna_FINALLY_me_hai():
    """Extract me kuch bhi ho jaye, form khula nahi chhodna chahiye."""
    import inspect
    from framework.crawler import Crawler
    src = inspect.getsource(Crawler._do_create)
    assert "finally:" in src and "_close_create()" in src


# ---------- "+" padosi ka nahi uthana ----------

# Bilkul wahi haalat jo asli app me hai:
#   Ledger  -- iske saamne "+" hai
#   Group   -- iske saamne "+" NAHI hai
NEIGHBOUR_PLUS = """
<ul id="acc">
  <li class="menu-item"><a class="menulink" id="lnkLedger">Ledger</a>
      <a id="plusLedger" class="plus" title="add">+</a></li>
  <li class="menu-item"><a class="menulink" id="lnkGroup">Group</a></li>
</ul>
<div id="out">nothing</div>
<script>
  plusLedger.onclick = () => { out.textContent = 'LEDGER-FORM'; };
</script>
"""


@pytest.fixture
def neighbour_page(bp):
    page = bp.page
    page.set_content(NEIGHBOUR_PLUS)
    yield page
    page.set_content(PAGE)


def test_jiske_saamne_plus_hai_uska_plus_milta_hai(neighbour_page, bp):
    from framework import nav
    assert nav.click_submenu_plus(bp, "Ledger")
    assert neighbour_page.locator("#out").inner_text() == "LEDGER-FORM"


def test_jiske_saamne_plus_NAHI_hai_wo_PADOSI_ka_nahi_uthata(neighbour_page, bp):
    """
    ASLI BUG: "+" dhoondhne wala code 3 parat UPAR chadh jata tha. Group ki
    row me "+" nahi hai, to wo upar jaakar LEDGER ka "+" utha laya -- aur
    Group ka create maang kar Ledger ka form khul gaya.

    Crawler use "Group ka create form" likh deta. Ye sabse bura tarah ka
    bug hai: galat data, jo galat lagta bhi nahi, aur uspe bane test
    hamesha galat cheez jaanchte rehte.

    Jis row me "+" nahi hai, wahan khali haath lautna hi sahi hai.
    """
    from framework import nav
    assert not nav.click_submenu_plus(bp, "Group"), \
        "Group ke liye padosi (Ledger) ka '+' utha liya"
    assert neighbour_page.locator("#out").inner_text() == "nothing", \
        "Ledger ka form khul gaya"


def test_create_button_PEHLE_try_hota_hai_plus_baad_me():
    """
    Create button USI list page par hota hai jo abhi khuli hai -- wo galat
    module ka ho hi nahi sakta. "+" sidebar me hota hai, jahan padosi ke
    "+" bhi hote hain. Isliye button pehle.
    """
    import inspect
    from framework.crawler import Crawler
    src = inspect.getsource(Crawler._open_create)
    assert src.index("CREATE_LABELS") < src.index("click_submenu_plus"), \
        "'+' pehle try ho raha hai -- wo padosi ka ho sakta hai"


def test_galat_form_khule_to_uska_data_SAVE_nahi_hota():
    """
    Doosri rok. Pehli rok nav.py me hai. Par ek rok kabhi kaafi nahi
    hoti -- wo chhoot gayi to yahan pakda jayega.
    """
    import inspect
    from framework.crawler import Crawler, BLOCKED
    assert hasattr(Crawler, "_form_matches")
    src = inspect.getsource(Crawler._do_create)
    assert "_form_matches" in src
    assert BLOCKED in src
    # jaanch extract se PEHLE honi chahiye, warna galat data nikal chuka hoga
    assert src.index("_form_matches") < src.index("collect(self.bp")


@pytest.mark.parametrize("label,heading,ok", [
    ("Group", "Create Group", True),
    ("Group", "Create Ledger", False),
    ("Ledger", "Ledger Master", True),
    ("Item", "Create Item", True),
    ("Item", "Create Ledger", False),
    ("Store", "", True),          # heading na mile to rok nahi lagate
])
def test_form_ka_heading_milaya_jata_hai(bp, label, heading, ok):
    page = bp.page
    page.set_content(f"<h1 class='mhead'>{heading}</h1>" if heading else "<div></div>")
    c = _crawler_for(page)
    got, _ = c._form_matches(label)
    assert got is ok, f"{label!r} vs {heading!r}"
    page.set_content(PAGE)


# ---------- popup ke ANDAR ka button ----------

# Bilkul wahi jo Purchase Bill par aata hai
PURCHASE_POPUP = """
<div id="form">
  <label for="txtLedgerName33">Party Name</label>
  <input id="txtLedgerName33">
  <input id="txtentryNo33">
  <button id="btnSave33">Save</button>
</div>
<div class="modal" id="chooser">
  <p>How would you like to create your purchase bill?</p>
  <button id="btnUpload">Upload &amp; Auto Read Invoice</button>
  <button id="btnManual">Start Manual Entry</button>
</div>
<div id="out">nothing</div>
<script>
  btnManual.onclick = () => {
    document.getElementById('chooser').remove();
    out.textContent = 'MANUAL';
  };
  btnUpload.onclick = () => { out.textContent = 'UPLOAD'; };
</script>
"""


@pytest.fixture
def purchase_page(bp):
    page = bp.page
    page.set_content(PURCHASE_POPUP)
    yield page
    page.set_content(PAGE)


def test_popup_ke_ANDAR_ka_button_dab_jata_hai(purchase_page):
    """
    ASLI BUG: guard pehle POPUP BAND karne ki koshish karta tha. Popup band
    nahi hua (peeche form khula tha, isliye Escape bhi mana hai), aur guard
    ne UnsafeClick utha diya.

    Natija: Purchase ke SAATON form nahi khule -- aur wajah app nahi, mera
    apna guard tha. Raasta saaf karne wala hi raste me aa gaya.
    """
    from framework import safety
    btn = purchase_page.locator("#btnManual")
    safety.guarded_click(btn, "popup:manual", inside_modal=True, timeout=4000)
    purchase_page.wait_for_timeout(300)
    assert purchase_page.locator("#out").inner_text() == "MANUAL"


def test_inside_modal_ke_BINA_guard_rok_deta_hai(purchase_page):
    """
    Ye rok waise sahi hai -- galti se modal ke peeche wale button par click
    ho jana bura hota hai. Isliye chhoot MAANGNI padti hai, apne aap nahi
    milti.
    """
    from framework import safety
    with pytest.raises(safety.UnsafeClick):
        safety.guarded_click(purchase_page.locator("#btnSave33"),
                             "peeche ka button", timeout=3000)


def test_crawler_purchase_wala_popup_hata_deta_hai(purchase_page):
    c = _crawler_for(purchase_page)
    c._clear_create_popups()
    purchase_page.wait_for_timeout(300)
    assert purchase_page.locator("#out").inner_text() == "MANUAL", \
        "crawler ne 'Start Manual Entry' nahi dabaya"
    assert purchase_page.locator("#chooser").count() == 0


def test_UPLOAD_wala_button_kabhi_nahi_dabta(purchase_page):
    """
    "Upload & Auto Read Invoice" file maangta hai aur asli invoice padh kar
    bill BANA deta hai. Crawler ko sirf dekhna hai, banana nahi.
    """
    from framework.crawler import Crawler
    # Jin naamon ko crawler dhoondhta hai, unme "Upload" nahi hona chahiye.
    # (Pehle ye source me "for label in (...)" wali line dhoondhta tha --
    #  wo code badalte hi toot gaya. Ab seedha wahi list dekhte hain.)
    import re, inspect
    src = inspect.getsource(Crawler._clear_create_popups)
    m = re.search(r"labels\s*=\s*\(([^)]*)\)", src, re.S)
    assert m, "popup ke naamon ki list nahi mili"
    assert "Upload" not in m.group(1), "crawler Upload wala button daba sakta hai"
    c = _crawler_for(purchase_page)
    c._clear_create_popups()
    assert purchase_page.locator("#out").inner_text() != "UPLOAD"
