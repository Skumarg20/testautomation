"""
Teen dikkatein jo asli crawl me mili -- teeno ka apna test.

  1. Sale ke chheon form par "Sale Bill Setting x" panel chipka reh gaya,
     aur uske 280-300 element form ke naam se save ho gaye.
  2. Purchase ka "Start Manual Entry" DOM me tha par visible=False --
     popup abhi bana hi nahi tha jab humne dekha.
  3. Voucher ka button "+ Create Receipt Voucher List" hota hai, sirf
     "Create" nahi.
"""
import pytest
from playwright.sync_api import sync_playwright


@pytest.fixture(scope="module")
def bp():
    with sync_playwright() as pw:
        b = pw.chromium.launch(headless=True)
        pg = b.new_page(viewport={"width": 1280, "height": 720})
        from framework.base_page import BasePage
        yield BasePage(pg)
        b.close()


def _crawler(bp):
    import framework.crawler as C
    c = C.Crawler.__new__(C.Crawler)
    c.bp, c.page, c.verbose, c.retry = bp, bp.page, False, 0
    return c


# ---------- 1. Settings panel chipka hua ----------

SETTINGS_STUCK = """
<h1 class="mhead">Sale Bill Setting &times;</h1>
<div id="panel">
  <label>Cursor wait on</label>
  <select id="txtCursorshouldwait"><option>All</option><option>Quantity</option></select>
  <button id="txtApply">Apply</button>
  <button id="btnClose">Esc Close</button>
</div>
<div id="form">
  <label for="txtLedgerName56">Party Name</label><input id="txtLedgerName56">
  <button id="btnEsc56">Esc Close</button>
</div>
<div id="log">panel-open</div>
<script>
  btnClose.onclick = () => {
    panel.remove();
    document.querySelector('h1').textContent = 'Sale Bill';
    log.textContent = 'panel-closed';
  };
  btnEsc56.onclick = () => { log.textContent = 'FORM-CLOSED'; };
  txtApply.onclick = () => { log.textContent = 'SETTINGS-SAVED'; };
</script>
"""


def test_settings_panel_band_ho_jata_hai(bp):
    bp.page.set_content(SETTINGS_STUCK)
    assert _crawler(bp)._close_settings_panel()
    assert bp.page.locator("#log").inner_text() == "panel-closed"


def test_panel_band_karte_waqt_FORM_band_nahi_hota(bp):
    """
    btnEsc* poora form band kar deta hai, sirf panel nahi. Use chhoona
    matlab jo form kholne ki mehnat ki wo bekaar.
    """
    bp.page.set_content(SETTINGS_STUCK)
    _crawler(bp)._close_settings_panel()
    assert bp.page.locator("#log").inner_text() != "FORM-CLOSED"
    assert bp.page.locator("#txtLedgerName56").count() == 1, "form ud gaya"


def test_APPLY_kabhi_nahi_dabta(bp):
    """
    Apply settings SAVE kar deta hai. Crawler ka kaam dekhna hai, badalna
    nahi -- aur ye company ki asli setting hoti.
    """
    bp.page.set_content(SETTINGS_STUCK)
    _crawler(bp)._close_settings_panel()
    assert bp.page.locator("#log").inner_text() != "SETTINGS-SAVED"


def test_panel_na_ho_to_kuch_nahi_karta(bp):
    """Aam form par khaamakha kuch band karne ki koshish na ho."""
    bp.page.set_content('<h1 class="mhead">Create Item</h1><input id="a">')
    assert not _crawler(bp)._close_settings_panel()


# ---------- 2. popup der se aata hai ----------

LATE_POPUP = """
<div id="form"><input id="txtLedgerName33"></div>
<div id="out">nothing</div>
<script>
  setTimeout(() => {
    const d = document.createElement('div');
    d.className = 'modal';
    d.innerHTML = '<p>How would you like to create your purchase bill?</p>' +
      '<button id="btnManual">Start Manual Entry</button>';
    document.body.appendChild(d);
    document.getElementById('btnManual').onclick = () => {
      d.remove(); out.textContent = 'MANUAL';
    };
  }, 1200);
</script>
"""


def test_DER_SE_aane_wala_popup_bhi_dabta_hai(bp):
    """
    ASLI BUG: popup 1-2 second baad banta hai. Turant dekh kar "nahi mila"
    maan lena galat tha -- metadata me wo button DOM me tha par
    visible=False.
    """
    bp.page.set_content(LATE_POPUP)
    _crawler(bp)._clear_create_popups()
    bp.page.wait_for_timeout(300)
    assert bp.page.locator("#out").inner_text() == "MANUAL", \
        "der se aane wala popup chhoot gaya"


# ---------- 3. voucher ka poora naam ----------

VOUCHER_LIST = """
<h1 class="mhead">Receipt Voucher List</h1>
<p>No Receipt Voucher Created Yet</p>
<button id="btnCreateV">+ Create Receipt Voucher List</button>
<div id="vform" style="display:none">
  <label for="txtvchno">Voucher No.</label><input id="txtvchno">
</div>
<script>
  btnCreateV.onclick = () => {
    vform.style.display = 'block';
    document.querySelector('h1').textContent = 'Create Receipt Voucher';
  };
</script>
"""


def test_voucher_ka_poora_naam_wala_button_dabta_hai(bp):
    """Button "+ Create Receipt Voucher List" hai, sirf "Create" nahi."""
    bp.page.set_content(VOUCHER_LIST)
    assert _crawler(bp)._open_create("Accounting Trans.", "Receipt")
    assert bp.page.locator("#vform").is_visible()


def test_voucher_form_khulne_par_heading_badal_jati_hai(bp):
    """
    Pehle heading "Receipt Voucher List" hi rehti thi -- matlab form khula
    hi nahi tha, par crawler ne 245 element list ke hi save kar diye.
    """
    bp.page.set_content(VOUCHER_LIST)
    c = _crawler(bp)
    c._open_create("Accounting Trans.", "Receipt")
    ok, head = c._form_matches("Receipt")
    assert ok and "Create" in head, head


# ---------- form khula ya nahi: NAYE FIELD se pata chalta hai ----------

# Store/Salt/Unit/Manufacturer aur paanchon voucher aise hi hain:
# form PANEL ki tarah khulta hai aur list ka heading waisa hi reh jata hai.
PANEL_FORM = """
<h1 class="mhead">Store List</h1>
<input id="searchStore" placeholder="Search">
<button id="btnCreateF2">Create/F2</button>
<div id="panel" style="display:none">
  <label for="txtStoreName">Store Name</label><input id="txtStoreName">
  <input id="txtStoreCode">
  <select id="ddlStoreType"><option>Main</option></select>
</div>
<script>
  btnCreateF2.onclick = () => { panel.style.display='block'; };
</script>
"""

DEAD_CREATE = """
<h1 class="mhead">Salt List</h1>
<input id="searchSalt">
<button id="btnCreateF2">Create/F2</button>
<script>btnCreateF2.onclick = () => {};</script>
"""


def test_heading_na_badle_to_bhi_form_pehchana_jata_hai(bp):
    """
    ASLI BUG: heading "Store List" hi rehti thi, isliye crawler ne LIST ke
    254 element "create form" ke naam se save kar diye.

    Naye field aana pakka signal hai -- form khula to kuch naya aayega.
    """
    bp.page.set_content(PANEL_FORM)
    c = _crawler(bp)
    c.pages, c.status, c.state = [], [], {"done": []}
    import framework.crawler as C, tempfile, pathlib as _p
    old = C.OUT
    C.OUT = _p.Path(tempfile.mkdtemp()) / "out"
    (C.OUT / "raw").mkdir(parents=True)
    try:
        row = c._do_create("Master", "Store", before=c._field_ids())
        assert row, "form khula par pakda nahi gaya"
        assert "txtStoreName" in row["newFields"], row["newFields"]
        assert "searchStore" not in row["newFields"], "list ka field bhi gin liya"
        assert row["newFieldCount"] == 3
    finally:
        C.OUT = old


def test_create_dabane_par_kuch_na_ho_to_BLOCKED(bp):
    """
    Button daba par kuch khula hi nahi -- to list ke element "create form"
    ke naam se save karna jhooth hoga.
    """
    bp.page.set_content(DEAD_CREATE)
    c = _crawler(bp)
    c.pages, c.status, c.state = [], [], {"done": []}
    import framework.crawler as C, tempfile, pathlib as _p
    old = C.OUT
    C.OUT = _p.Path(tempfile.mkdtemp()) / "out"
    (C.OUT / "raw").mkdir(parents=True)
    try:
        assert c._do_create("Master", "Salt", before=c._field_ids()) is None
        assert any(x["status"] == C.BLOCKED and "naya field" in x.get("reason", "")
                   for x in c.status), c.status
    finally:
        C.OUT = old


# ---------- Settings panel: der se aata hai ----------

LATE_PANEL = """
<h1 class="mhead">Sale Bill</h1>
<div id="form">
  <input id="txtLedgerName56"><button id="btnEsc56">Esc Close</button>
</div>
<div id="log">no-panel</div>
<script>
  setTimeout(() => {
    document.querySelector('h1').textContent = 'Sale Bill Setting \\u00d7';
    const d = document.createElement('div');
    d.innerHTML = '<button id="close-12">Esc Close</button>';
    document.body.appendChild(d);
    document.getElementById('close-12').onclick = () => {
      d.remove();
      document.querySelector('h1').textContent = 'Sale Bill';
      log.textContent = 'panel-closed';
    };
  }, 1200);
</script>
"""


def test_DER_SE_aane_wala_settings_panel_bhi_band_hota_hai(bp):
    """
    Pichhli baar maine turant dekha aur "panel nahi hai" maan liya -- par
    wo ek-do second baad bana, aur extract ne use pakad liya.
    Wahi galti Purchase popup ke saath bhi hui thi.
    """
    bp.page.set_content(LATE_PANEL)
    assert _crawler(bp)._close_settings_panel(wait_s=5)
    assert bp.page.locator("#log").inner_text() == "panel-closed"
    assert bp.page.locator("#txtLedgerName56").count() == 1, "form ud gaya"


FORM_KILLER = """
<h1 class="mhead">Sale Bill Setting &times;</h1>
<div id="form"><input id="txtLedgerName56"></div>
<button id="btnClose">Esc Close</button>
<script>
  btnClose.onclick = () => { form.remove(); };
</script>
"""


def test_form_band_karne_wale_button_par_ruk_jata_hai(bp):
    """
    "#btnClose" ka text "Esc Close" hai -- bilkul form ke btnEsc56 jaisa.
    Wo panel ka nahi, FORM ka close bhi ho sakta hai. Us soorat me jo
    mehnat form kholne me lagi wo bekaar chali jayegi.
    """
    bp.page.set_content(FORM_KILLER)
    assert not _crawler(bp)._close_settings_panel(wait_s=2)


# ---------- app mar jaye to ruk jao ----------

ALIVE = """
<div id="nav">
  <a class="menulink" id="m1">Master</a><a class="menulink" id="m2">Sale</a>
  <a class="menulink" id="m3">Purchase</a><a class="menulink" id="m4">Report</a>
</div>
"""
DEAD = "<div id='nav'></div><p>session khatam</p>"


def test_app_zinda_hai_ya_nahi_pata_chalta_hai(bp):
    """
    ASLI GHATNA: crawl 28.7 GHANTE chala aur sirf 3 page nikale. App ka
    session beech me khatam ho gaya -- saare menu gayab. Crawler ne use
    "menu nahi mila" samjha aur har menu par retry karta raha, har retry
    par 12-20 second ka wait.

    Ek mari hui app par ghanton koshish karna bekaar hai.
    """
    bp.page.set_content(ALIVE)
    assert _crawler(bp)._app_alive()
    bp.page.set_content(DEAD)
    assert not _crawler(bp)._app_alive()


def test_app_mari_ho_to_page_BLOCKED_hota_hai(bp):
    bp.page.set_content(DEAD)
    c = _crawler(bp)
    c.pages, c.status, c.state = [], [], {"done": []}
    import framework.crawler as C
    res = c._do_page("Master", "Ledger")
    assert res["status"] == C.BLOCKED
    assert any("app se koi jawab nahi" in x.get("reason", "") for x in c.status)


def test_waqt_ki_seema_hai():
    """
    28 ghante ka crawl kisi kaam ka nahi. Seema par pahunche to jo mila
    wo lekar saaf ruk jao.
    """
    import inspect
    from framework.crawler import Crawler
    assert inspect.signature(Crawler.__init__).parameters["budget_min"].default == 90
    src = inspect.getsource(Crawler.run)
    assert "budget_s" in src and "waqt ki seema" in src
    # seema par bache hue menu ko bhi haal milna chahiye -- chupchaap nahi chhodna
    assert src.count('_mark("menu"') >= 3


def test_seema_par_bache_menu_bhi_haal_paate_hain():
    import inspect
    from framework.crawler import Crawler, BLOCKED
    src = inspect.getsource(Crawler.run)
    i = src.index("waqt ki seema")
    assert "for rest in menus[" in src[i:i + 900], \
        "bache hue menu chupchaap chhoot jayenge"


def test_app_wapas_laane_ki_koshish_hoti_hai():
    """Ek baar dashboard, phir dobara login -- phir haar maan lo."""
    import inspect
    from framework.crawler import Crawler
    src = inspect.getsource(Crawler._revive)
    assert "/dashboard" in src and "from framework.auth import login" in src


# ---------- asli panel: .itemcontrolClose ----------

# Bilkul waise jaise MargBooks ke dump me hai:
#     <h2 class="headingItem">Sale Bill Setting x</h2>
#     <button class="close itemcontrolClose">x</button>
REAL_PANEL = """
<h2 class="headingItem">Sale Bill Setting &times;</h2>
<button class="close itemcontrolClose">&times;</button>
<div id="panel"><select id="txtCursorshouldwait"><option>All</option></select></div>
<div id="form"><input id="txtLedgerName56"><button id="btnEsc56">Esc Close</button></div>
<div id="log">panel-open</div>
<script>
  document.querySelector('.itemcontrolClose').onclick = () => {
    panel.remove();
    document.querySelector('h2').textContent = 'Sale Bill';
    log.textContent = 'panel-closed';
  };
  btnEsc56.onclick = () => { log.textContent = 'FORM-CLOSED'; };
</script>
"""


def test_asli_panel_ka_close_button_kaam_karta_hai(bp):
    """
    ASLI BUG: panel band karne wala button ".itemcontrolClose" hai -- aur
    wo meri list me tha hi nahi. Saboot dump me pehle se maujood tha, par
    maine metadata me "close" jaise BUTTON dhoondhe aur ye chhoot gaya.

    Isi ek chhooti hui line se Sale ke SAATON form block hue: form khule
    the, panel bhi khula tha, aur crawler ne mila-jula data lene se
    (sahi hi) mana kar diya.
    """
    bp.page.set_content(REAL_PANEL)
    assert _crawler(bp)._close_settings_panel(wait_s=3)
    assert bp.page.locator("#log").inner_text() == "panel-closed"
    assert bp.page.locator("#txtLedgerName56").count() == 1, "form ud gaya"


def test_itemcontrolClose_SABSE_PEHLE_try_hota_hai():
    """
    Ye MargBooks ka apna panel-close hai. Baaki selector andaze hain --
    unme se koi form ka close nikal sakta hai.
    """
    import inspect
    from framework.crawler import Crawler
    src = inspect.getsource(Crawler._close_settings_panel)
    i = src.index("sels = (")
    order = src[i:src.index(")", i)]
    assert order.index("itemcontrolClose") < order.index("btnClose")


def test_popup_ka_intezaar_12_second_hai():
    """
    6 second kam pada tha -- Purchase ke saaton form chhoot gaye.
    """
    import inspect
    from framework.crawler import Crawler
    src = inspect.getsource(Crawler._clear_create_popups)
    assert "time.time() + 12" in src
    assert "css_fallbacks" in src, "text se dhoondhne ka rasta nahi hai"
