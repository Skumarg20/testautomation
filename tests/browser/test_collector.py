"""
Element collection ka pakka imtihan -- nakli MargBooks pages par.

Review me jo cheezein chhoot rahi thin, har ek ka alag test:
  - div/span/i ka click, <a> bina href, custom dropdown
  - tabs aur accordion ke andar ke field
  - ag-Grid ke wo column jo scroll se bahar the
  - shadow DOM, iframe
  - dropdown badalne par aane wale field
  - adhoora data (Sign In, not authorized, bahut kam element) ab PASS nahi
"""
import tempfile
import pathlib

import pytest
from playwright.sync_api import sync_playwright

from framework.crawler import (assess, collect, count_elements, extract,
                               merge_data)


@pytest.fixture(scope="module")
def bp():
    with sync_playwright() as pw:
        b = pw.chromium.launch(headless=True)
        pg = b.new_page(viewport={"width": 1280, "height": 720})
        from framework.base_page import BasePage
        yield BasePage(pg)
        b.close()


def _ids(rows):
    return {r.get("id") or r.get("formControlName") or r.get("name") for r in rows}


# ---------- 1. click wali cheezein ----------

CLICKABLES = """
<div id="addRow" onclick="1">+ Add row</div>
<span id="calc" style="cursor:pointer">Calculator</span>
<a id="lnkNoHref" onclick="1">Print preview</a>
<div id="box" style="cursor:pointer"><span id="inner">inside</span>
  <i id="ic" style="display:inline-block;width:10px;height:10px"></i></div>
<i id="trash" class="fa fa-trash" onclick="1"
   style="display:inline-block;width:12px;height:12px"></i>
<button id="b">Save</button>
<nav><div id="navItem" style="cursor:pointer" onclick="1">Side</div></nav>
"""


def test_div_span_aur_a_bina_href_ke_click_milte_hain(bp):
    """Angular ka (click) DOM me nahi dikhta -- par cursor:pointer aur onclick dikhte hain."""
    bp.page.set_content(CLICKABLES)
    got = extract(bp)
    ids = _ids(got["clickables"])
    assert {"addRow", "calc", "lnkNoHref", "box", "trash"} <= ids, ids


def test_pointer_ke_bacche_dobara_nahi_gine_jate(bp):
    """cursor:pointer CSS se bacchon me utarta hai -- sirf sabse upar wala lo."""
    bp.page.set_content(CLICKABLES)
    ids = _ids(extract(bp)["clickables"])
    assert "inner" not in ids and "ic" not in ids, ids


def test_button_aur_sidebar_clickables_me_nahi(bp):
    bp.page.set_content(CLICKABLES)
    ids = _ids(extract(bp)["clickables"])
    assert "b" not in ids, "button pehle se buttons me hai"
    assert "navItem" not in ids, "sidebar har page par dohrata -- shor"


def test_delete_jaisa_clickable_danger_mark_hota_hai(bp):
    bp.page.set_content(CLICKABLES)
    row = next(c for c in extract(bp)["clickables"] if c["id"] == "trash")
    assert row["danger"] is True


# ---------- 2. custom dropdown ----------

def test_custom_dropdown_milta_hai_aur_uski_value_padhi_jati_hai(bp):
    bp.page.set_content("""
      <div class="ng-select" id="grp"><div class="ng-value-label">Medicine</div></div>
      <div class="ng-select" id="grp2"><div class="ng-value-label">Other</div></div>""")
    cs = {c["id"]: c for c in extract(bp)["customSelects"]}
    assert set(cs) == {"grp", "grp2"}
    assert cs["grp"]["value"] == "Medicine"
    assert cs["grp"]["uid"].startswith("cs")


# ---------- 3. tab aur accordion ----------

TABS = """
<ul class="nav-tabs">
  <li class="active"><a id="t1" class="nav-link active" href="#" onclick="return false">Purchase</a></li>
  <li><a id="t2" class="nav-link" href="#" onclick="show('sale');return false">Sale</a></li>
  <li><a id="t3" class="nav-link" href="/other/page">Elsewhere</a></li>
  <li><a id="t4" class="nav-link" href="#" onclick="show('del');return false">Delete tab</a></li>
</ul>
<div id="pane"><input id="purRate"></div>
<script>
  window.__clicked = [];
  function show(w) {
    window.__clicked.push(w);
    document.getElementById('pane').innerHTML =
      w === 'sale' ? '<input id="saleRate"><input id="disc1">' : '<input id="shouldNot">';
  }
</script>
"""


def test_dusre_tab_ke_andar_ke_field_milte_hain(bp):
    bp.page.set_content(TABS)
    data = collect(bp)
    assert {"purRate", "saleRate", "disc1"} <= _ids(data["inputs"])
    sale = next(i for i in data["inputs"] if i["id"] == "saleRate")
    assert sale["state"] == "tab:Sale", "kis tab ke andar mila, ye likha hona chahiye"


def test_tab_jo_doosre_page_le_jaye_ya_delete_jaisa_ho_nahi_dabta(bp):
    bp.page.set_content(TABS)
    data = collect(bp)
    assert "shouldNot" not in _ids(data["inputs"]), "Delete tab dab gaya"
    assert bp.page.evaluate("() => window.__clicked") == ["sale"]
    by = {s["state"]: s for s in data["states"]}
    assert by["tab:Elsewhere"]["ok"] is False and "link" in by["tab:Elsewhere"]["why"]
    assert by["tab:Delete tab"]["ok"] is False
    assert bp.page.url == "about:blank", "page se bahar chala gaya"


def test_active_tab_dobara_nahi_dabta(bp):
    bp.page.set_content(TABS)
    data = collect(bp)
    assert "tab:Purchase" not in {s["state"] for s in data["states"]}


ACCORDION = """
<a id="acc" data-toggle="collapse" href="#c1" aria-expanded="false" class="collapsed"
   onclick="document.getElementById('c1').innerHTML='<input id=lateField>';
            this.setAttribute('aria-expanded','true'); return false;">More details</a>
<div id="c1"></div>
"""


def test_band_accordion_kholkar_andar_ka_field_milta_hai(bp):
    bp.page.set_content(ACCORDION)
    data = collect(bp)
    f = next(i for i in data["inputs"] if i["id"] == "lateField")
    assert f["state"] == "section:More details"


def test_tab_dabane_ke_baad_naye_tab_bhi_dabte_hain(bp):
    """Ek tab ke andar aur tab ho to wo bhi (nested)."""
    bp.page.set_content("""
      <ul class="nav-tabs"><li><a id="o" class="nav-link active" href="#" onclick="return false">Outer</a></li>
        <li><a id="o2" class="nav-link" href="#" onclick="
            document.getElementById('in').innerHTML =
              '<ul class=nav-tabs><li><a id=i1 class=nav-link href=# onclick=&quot;document.getElementById(\\'deep\\').innerHTML=\\'<input id=deepField>\\';return false&quot;>Inner</a></li></ul><div id=deep></div>';
            return false;">Second</a></li></ul>
      <div id="in"></div>""")
    data = collect(bp)
    assert "deepField" in _ids(data["inputs"]), data["states"]


# ---------- 4. ag-Grid ke saare column ----------

GRID = """
<div class="ag-center-cols-viewport" style="width:300px;height:40px;overflow-x:auto">
  <div style="width:2200px;height:20px"></div></div>
<div id="hdr"></div>
<script>
(function () {   // IIFE: set_content dobara chale to 'const' dobara declare na ho
  const cols = ['Product','Qty','Rate','Disc1','Disc2','Batch','Expiry','Amount'];
  const vp = document.querySelector('.ag-center-cols-viewport');
  function render() {
    const first = Math.floor(vp.scrollLeft / 260);
    document.getElementById('hdr').innerHTML = cols.slice(first, first + 2)
      .map(c => `<div role="columnheader" col-id="${c}">${c}</div>`).join('');
  }
  vp.addEventListener('scroll', render); render();
})();
</script>
"""


def test_grid_ke_scroll_se_bahar_ke_column_bhi_milte_hain(bp):
    """ag-Grid bahar ke column banata hi nahi -- scroll karke hi milte hain."""
    bp.page.set_content(GRID)
    snap = extract(bp)
    assert len(snap["gridColumns"]) <= 2, "ek snapshot me saare column nahi aane chahiye"
    data = collect(bp)
    got = {c["id"] for c in data["gridColumns"]}
    assert got == {"Product", "Qty", "Rate", "Disc1", "Disc2", "Batch", "Expiry", "Amount"}, got


def test_grid_scroll_ke_baad_jahan_the_wahin_wapas(bp):
    bp.page.set_content(GRID)
    collect(bp)
    assert bp.page.evaluate("() => document.querySelector('.ag-center-cols-viewport').scrollLeft") == 0


def test_scroll_se_mile_column_par_state_likha_hai(bp):
    bp.page.set_content(GRID)
    data = collect(bp)
    amt = next(c for c in data["gridColumns"] if c["id"] == "Amount")
    assert amt["state"].startswith("grid-scroll")


# ---------- 5. shadow DOM aur iframe ----------

def test_shadow_dom_aur_iframe_ke_andar_ke_element_milte_hain(bp):
    bp.page.set_content("""
      <div id="host"></div>
      <script>
        const r = document.getElementById('host').attachShadow({mode: 'open'});
        r.innerHTML = '<input id="shadowIn"><button id="shadowBtn">Go</button>';
      </script>
      <iframe srcdoc='<input id="frameIn"><button id="frameBtn">x</button>'></iframe>""")
    bp.page.wait_for_timeout(600)
    got = extract(bp)
    assert "shadowIn" in _ids(got["inputs"]) and "shadowBtn" in _ids(got["buttons"])
    fr = next(i for i in got["inputs"] if i["id"] == "frameIn")
    assert fr["frame"].startswith("about:srcdoc"), "kis frame ka hai, ye likha hona chahiye"


# ---------- 6. dropdown badalne par conditional field ----------

CONDITIONAL = """
<header><select id="co"><option>A</option><option>B</option></select></header>
<label for="rt">Registration Type</label>
<select id="rt"><option>Unregistered</option><option>Registered</option><option>Composition</option></select>
<select id="big"><option>1</option><option>2</option><option>3</option><option>4</option>
  <option>5</option><option>6</option><option>7</option><option>8</option><option>9</option></select>
<div id="extra"></div>
<button id="btnSave1">Save</button><button id="btnEsc1">Close</button>
<script>
  window.__saved = 0; window.__touched = [];
  document.getElementById('btnSave1').onclick = () => window.__saved++;
  ['co', 'big'].forEach(id => document.getElementById(id)
      .addEventListener('change', () => window.__touched.push(id)));
  document.getElementById('rt').addEventListener('change', e => {
    const v = e.target.options[e.target.selectedIndex].text;
    document.getElementById('extra').innerHTML =
      v === 'Registered' ? '<input id="gstin">'
      : v === 'Composition' ? '<input id="compScheme">' : '';
  });
</script>
"""


def test_dropdown_badalne_par_aane_wale_field_milte_hain(bp):
    bp.page.set_content(CONDITIONAL)
    data = collect(bp, deep=True)
    assert {"gstin", "compScheme"} <= _ids(data["inputs"])
    g = next(i for i in data["inputs"] if i["id"] == "gstin")
    assert g["state"] == "when:Registration Type=Registered"
    cond = {c["when"]: c["newFields"] for c in data["conditional"]}
    assert "gstin" in cond["Registration Type = Registered"]
    assert "compScheme" in cond["Registration Type = Composition"]


def test_dropdown_purani_value_par_wapas_aata_hai(bp):
    bp.page.set_content(CONDITIONAL)
    collect(bp, deep=True)
    assert bp.page.evaluate("() => document.getElementById('rt').value") == "Unregistered"


def test_dropdown_badalte_waqt_save_kabhi_nahi_dabta(bp):
    bp.page.set_content(CONDITIONAL)
    collect(bp, deep=True)
    assert bp.page.evaluate("() => window.__saved") == 0


def test_header_aur_lambe_dropdown_nahi_chhute(bp):
    """Header ka dropdown (company badalna jaisa) aur 9 vikalp wala dropdown chhodte hain."""
    bp.page.set_content(CONDITIONAL)
    collect(bp, deep=True)
    assert bp.page.evaluate("() => window.__touched") == []


def test_bina_deep_ke_dropdown_chhua_nahi_jata(bp):
    """Sirf create form me (deep=True) -- list page ke dropdown nahi."""
    bp.page.set_content(CONDITIONAL)
    data = collect(bp)
    assert "gstin" not in _ids(data["inputs"]) and not data.get("conditional")


def test_settings_panel_ke_dropdown_nahi_chhute(bp):
    bp.page.set_content(CONDITIONAL.replace("</header>", "</header><h1 class='mhead'>Sale Bill Setting</h1>", 1))
    collect(bp, deep=True)
    assert bp.page.evaluate("() => document.getElementById('rt').value") == "Unregistered"
    assert not bp.page.evaluate("() => document.getElementById('extra').innerHTML")


# ---------- 7. adhoora data PASS nahi ----------

def test_sign_in_page_PASS_nahi_hota():
    q = assess({"inputs": [{}] * 5,
                "page": {"bodyHint": "sign in to continue with margbooks mobile / email id"}})
    assert q["level"] == "partial" and "login_page" in q["flags"]


def test_not_authorized_PASS_nahi_hota():
    q = assess({"inputs": [{}] * 5, "page": {"bodyHint": "oops! you are not authorized"}})
    assert q["level"] == "partial" and "not_authorized" in q["flags"]


@pytest.mark.parametrize("n,flag", [(0, "empty"), (2, "few_elements")])
def test_bahut_kam_element_par_shak_likha_jata_hai(n, flag):
    q = assess({"inputs": [{}] * n, "page": {"bodyHint": "item list"}})
    assert q["level"] == "partial" and flag in q["flags"]


def test_ready_na_ho_to_shak_likha_jata_hai():
    q = assess({"inputs": [{}] * 6, "ready": False, "page": {}})
    assert "not_ready" in q["flags"]


def test_theek_page_ok_hai():
    q = assess({"inputs": [{}] * 6, "ready": True, "page": {"bodyHint": "item list"}})
    assert q == {"level": "ok", "flags": [], "elements": 6}


def test_adhoora_page_par_dobara_koshish_aur_der_se_aaye_field_jud_jate_hain(bp):
    """Page 1.3s baad bharta hai; pehli snapshot me sirf ek button hota hai."""
    bp.page.set_content("""
      <button id="only">x</button><div id="app"></div>
      <script>setTimeout(() => {
        document.getElementById('app').innerHTML =
          '<input id="lateA"><input id="lateB"><input id="lateC">';
      }, 1300);</script>""")
    data = collect(bp)
    assert {"lateA", "lateB", "lateC"} <= _ids(data["inputs"]), data["states"]
    assert data["quality"]["level"] == "ok"
    assert any(s["state"] == "retry" for s in data["states"]), "dobara koshish nahi hui"


# ---------- 8. merge ----------

def test_merge_pehle_se_maujood_ko_dobara_nahi_jodta():
    a = {"inputs": [{"elementType": "input", "id": "x", "xpath": "//*[@id='x']"}]}
    added = merge_data(a, {"inputs": [{"elementType": "input", "id": "x",
                                       "xpath": "//*[@id='x']"}]}, state="late")
    assert added == [] and len(a["inputs"]) == 1


def test_merge_naye_par_state_likhta_hai():
    a = {"inputs": []}
    added = merge_data(a, {"inputs": [{"elementType": "input", "id": "y"}]}, state="tab:Sale")
    assert added[0]["state"] == "tab:Sale" and a["inputs"][0]["state"] == "tab:Sale"


def test_merge_tab_ki_taaza_uid_le_leta_hai():
    """Angular re-render kare to uid badalti hai -- purani par click nahi ho sakta."""
    a = {"tabs": [{"elementType": "tab", "id": "t", "uid": "tab1", "active": False}]}
    merge_data(a, {"tabs": [{"elementType": "tab", "id": "t", "uid": "tab9", "active": True}]})
    assert a["tabs"][0]["uid"] == "tab9" and a["tabs"][0]["active"] is True


def test_count_naye_groups_ginta_hai():
    assert count_elements({"clickables": [1, 2], "tabs": [1], "customSelects": [1]}) == 4


# ---------- 9. crawler ke andar ----------

CREATE_WITH_TABS = """
<div id="nav"><a id="menuMaster" class="menulink">Master</a></div>
<h1 class="mhead">Item List</h1>
<button id="btnCreateF2">Create/F2</button>
<div id="form" style="display:none">
  <h1 class="mhead">Create Item</h1>
  <label for="n">Item Name</label><input id="n">
  <ul class="nav-tabs">
    <li><a id="tA" class="nav-link active" href="#" onclick="return false">General</a></li>
    <li><a id="tB" class="nav-link" href="#"
           onclick="document.getElementById('pane').innerHTML='<input id=taxRate>';return false">Tax Info</a></li>
  </ul>
  <div id="pane"></div>
  <select id="ddl"><option>Pcs</option><option>Box</option></select>
  <button id="btnSave99">F10 Save</button><button id="btnEsc99">Esc Close</button>
</div>
<div id="discardBox" style="display:none">Transaction data will be loss, Are you sure?
  <button id="btnYes">Yes</button><button id="btnNo">No</button></div>
<script>
  btnCreateF2.onclick = () => { form.style.display = 'block'; };
  btnEsc99.onclick = () => { discardBox.style.display = 'block'; };
  btnYes.onclick = () => { discardBox.style.display = 'none'; form.style.display = 'none'; };
  btnSave99.onclick = () => { window.__SAVED = true; };
</script>
"""


def _crawler(bp):
    import framework.crawler as C
    c = C.Crawler.__new__(C.Crawler)
    c.bp, c.page, c.verbose, c.retry = bp, bp.page, False, 0
    c.say = lambda *_a, **_k: None
    c.pages, c.status, c.state, c.menus = [], [], {"done": []}, []
    c._trail, c.sidebar_info, c.discover = [], {}, True
    return c


def test_create_form_ke_tab_ka_field_row_me_aata_hai_aur_save_nahi_dabta(bp):
    import framework.crawler as C
    bp.page.set_content(CREATE_WITH_TABS)
    c = _crawler(bp)
    old = C.OUT
    C.OUT = pathlib.Path(tempfile.mkdtemp()) / "out"
    (C.OUT / "raw").mkdir(parents=True)
    try:
        row = c._do_create("Master", "Item", before=c._field_ids())
        assert row, "create form khula hi nahi"
        assert "taxRate" in _ids(row["inputs"]), "Tax Info tab ka field nahi mila"
        assert any(s["state"] == "tab:Tax Info" and s["ok"] for s in row["states"])
        assert row["quality"]["level"] == "ok" and row["status"] == C.PASS
        assert not bp.page.evaluate("() => window.__SAVED"), "SAVE daba diya"
        assert bp.page.locator("#form").is_hidden(), "form band nahi hua"
    finally:
        C.OUT = old


def test_shak_wala_page_PARTIAL_dikhta_hai_PASS_nahi(bp):
    """Sirf ek element wala page: collect ka haal "partial", aur row PARTIAL banti hai."""
    import framework.crawler as C
    bp.page.set_content("<p>hi</p><button id='x'>x</button>")
    data = C.collect(bp)
    assert data["quality"]["level"] == "partial"
    assert "few_elements" in data["quality"]["flags"]
    # row ka status isi se banta hai (dekho _do_page / _do_create)
    import inspect
    src = inspect.getsource(C.Crawler._do_page)
    assert 'st = PASS if q.get("level") == "ok" else PARTIAL' in src


def test_summary_PARTIAL_page_ko_poora_PASS_nahi_kehta():
    import inspect
    from framework.crawler import Crawler
    src = inspect.getsource(Crawler._finish)
    assert "pagesPartial" in src
    assert 'n("page", PARTIAL) == 0' in src
