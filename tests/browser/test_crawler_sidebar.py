"""
Sidebar se crawl ki list banana -- MargBooks ke asli template jaisa nakli page.

Asli template: Layout/menu.component.html. Teen baatein jo wahan hain aur yahan
dobara banayi gayi hain:
  - nested group me <a> par id NAHI hoti, sirf href="#menu-.." hota hai
  - nested <ul> ek <menu> element ke andar hota hai
  - "+" ek alag <a class="addLInks"> hai, leaf ke bagal me
  - group click par KHULTE-BAND (toggle) hote hain
"""
import json
import tempfile
import pathlib

import pytest
from playwright.sync_api import sync_playwright

SIDEBAR = """
<style>.collapse:not(.show){display:none} li[hidden]{display:none} a{display:block}</style>
<ul id="ul_id">
  <li class="grandParent"><a id="menu-0-565546851" class="menulink" href="javascript:void(0)"><span>Dashboard</span></a></li>

  <li class="grandParent">
    <a id="menu495210260" class="dropdown-toggle collapsed" aria-expanded="false" href="#menu-1-495210260"><span>Master</span></a>
    <ul class="list-unstyled collapse" id="menu-1-495210260">
      <li class="parent">
        <a class="dropdown-toggle collapsed" aria-expanded="false" href="#menu-1-0-111"><span>Inventory Master</span></a>
        <menu><ul class="collapse" id="menu-1-0-111">
          <li class="grandChild"><a id="menu-1-0-0-777" href="javascript:void(0)"><span>Item</span></a></li>
          <li class="grandChild"><a id="menu-1-0-1-778" href="javascript:void(0)"><span>Store</span></a></li>
          <li class="grandChild"><a class="dropdown-toggle collapsed" aria-expanded="false" href="#menu-1-0-2-900"><span>Deep Group</span></a>
            <menu><ul class="collapse" id="menu-1-0-2-900">
              <li class="grandChild"><a id="menu-1-0-2-0-901" href="javascript:void(0)"><span>Deep Page</span></a></li>
            </ul></menu></li>
        </ul></menu>
      </li>
      <li class="parent"><a id="menu-1-1-222" href="javascript:void(0)"><span>Currency</span></a></li>
    </ul>
  </li>

  <li class="grandParent">
    <a id="menu112725066" class="dropdown-toggle collapsed" aria-expanded="false" href="#menu-2-112725066"><span>Sale</span></a>
    <ul class="list-unstyled collapse" id="menu-2-112725066">
      <li class="parent"><a id="menu-2-0-5" href="javascript:void(0)"><span>Bill</span></a>
                         <a class="addLInks" href="javascript:void(0)">+</a></li>
      <li class="parent"><a id="menu-2-1-6" href="javascript:void(0)"><span>Draft</span></a></li>
      <li class="parent" hidden><a id="menu-2-2-7" href="javascript:void(0)"><span>Secret Thing</span></a></li>
    </ul>
  </li>

  <li class="grandParent">
    <a id="menu938595313" class="dropdown-toggle collapsed" aria-expanded="false" href="#menu-3-938595313"><span>Banking</span></a>
    <ul class="list-unstyled collapse" id="menu-3-938595313">
      <li class="parent"><a id="menu-3-0-8" href="javascript:void(0)"><span>Bank Statement</span></a></li>
    </ul>
  </li>

  <li class="grandParent"><a id="menu-4-fav-565546851" class="menulink" href="javascript:void(0)"><span>Dashboard</span></a></li>
</ul>
<div id="out">-</div>
<script>
  window.__clicked = [];
  document.querySelectorAll('a').forEach(a => a.addEventListener('click', e => {
    e.preventDefault();
    const tgt = a.classList.contains('dropdown-toggle') && a.getAttribute('href');
    if (tgt && tgt.startsWith('#')) {                      // bootstrap collapse: TOGGLE
      const ul = document.getElementById(tgt.slice(1));
      const open = ul.classList.toggle('show');
      a.classList.toggle('collapsed', !open);
      a.setAttribute('aria-expanded', open ? 'true' : 'false');
    } else {
      window.__clicked.push(a.id || a.textContent.trim());
      document.getElementById('out').textContent = a.id || a.textContent;
    }
  }));
</script>
"""

CONFIG = {
    "menus": [
        {"order": 1, "name": "Dashboard", "leaf": True},
        {"order": 2, "name": "Master", "submenus": [
            {"order": 1, "name": "Inventory Master", "children": [
                {"order": 1, "name": "Item", "screen": "item", "create": True,
                 "formNames": ["Description"]},
                {"order": 2, "name": "Store", "create": False}]}]},
        {"order": 3, "name": "Other Products", "leaf": True, "skip": True,
         "skip_reason": "alag product hai"},
    ]
}


@pytest.fixture(scope="module")
def bp():
    with sync_playwright() as pw:
        b = pw.chromium.launch(headless=True)
        pg = b.new_page(viewport={"width": 1280, "height": 720})
        from framework.base_page import BasePage
        yield BasePage(pg)
        b.close()


@pytest.fixture
def page(bp):
    bp.page.set_content(SIDEBAR)
    return bp.page


def _crawler(bp):
    import framework.crawler as C
    c = C.Crawler.__new__(C.Crawler)
    c.bp, c.page, c.verbose, c.retry = bp, bp.page, False, 0
    c.say = lambda *_a, **_k: None
    c.pages, c.status, c.state, c.menus = [], [], {"done": []}, []
    c._trail, c.sidebar_info, c.discover = [], {}, True
    return c


def _flat(nodes, trail=()):
    for n in nodes:
        p = trail + (n["name"],)
        yield p, n
        yield from _flat(n.get("children") or [], p)


# ---------- discovery ----------

def test_sidebar_ka_poora_tree_bina_click_ke_milta_hai(page):
    from framework.crawler import discover_sidebar
    tree = discover_sidebar(page, wait_s=2)
    assert [n["name"] for n in tree] == ["Dashboard", "Master", "Sale", "Banking", "Dashboard"]
    paths = {" > ".join(p) for p, _ in _flat(tree)}
    # band (collapsed) group ke andar ke item bhi, 3 parat neeche tak
    assert "Master > Inventory Master > Item" in paths
    assert "Master > Inventory Master > Deep Group > Deep Page" in paths
    assert page.evaluate("() => window.__clicked.length") == 0, "discovery ne click kiya"


def test_nested_group_me_id_nahi_to_href_se_selector_milta_hai(page):
    from framework.crawler import discover_sidebar
    tree = discover_sidebar(page, wait_s=2)
    inv = dict(_flat(tree))[("Master", "Inventory Master")]
    assert inv["id"] == "" and inv["kind"] == "group"
    assert inv["sel"] == 'a[href="#menu-1-0-111"]'
    top = dict(_flat(tree))[("Master",)]
    assert top["id"] == "menu495210260" and top["sel"] == '[id="menu495210260"]'


def test_plus_aur_hidden_pehchane_jate_hain(page):
    from framework.crawler import discover_sidebar
    d = dict(_flat(discover_sidebar(page, wait_s=2)))
    bill = d[("Sale", "Bill")]
    assert bill["create"] is True and bill["plusSel"].endswith("+ a.addLInks")
    assert d[("Sale", "Draft")]["create"] is False
    assert d[("Sale", "Secret Thing")]["hidden"] is True
    assert page.locator(bill["plusSel"]).count() == 1, "plus ka selector kaam nahi karta"


def test_sidebar_na_ho_to_None_aur_jaldi(bp):
    from framework.crawler import discover_sidebar
    bp.page.set_content("<div>koi sidebar nahi</div>")
    assert discover_sidebar(bp.page, wait_s=0.6) is None


# ---------- sequence banana ----------

def test_config_sirf_jaankari_jodti_hai_list_sidebar_ki_hai(page):
    from framework.crawler import discover_sidebar, build_sequence
    seq = build_sequence(discover_sidebar(page, wait_s=2), CONFIG)
    names = [m["name"] for m in seq["menus"]]
    # sidebar ke 4 asli menu (fav duplicate nahi) + config ka wo jo sidebar me nahi
    assert names == ["Dashboard", "Master", "Sale", "Banking", "Other Products"], names
    assert seq["menus"][-1].get("notInSidebar") is True, "chupchaap gira diya"
    assert seq["menus"][-1]["skip"] is True

    d = dict(_flat(seq["menus"][1]["submenus"], ("Master",)))
    item = d[("Master", "Inventory Master", "Item")]
    assert item["screen"] == "item" and item["formNames"] == ["Description"], \
        "config ki jaankari merge nahi hui"
    # Banking config me hai hi nahi -- phir bhi iska page list me hai
    bank = seq["menus"][3]["submenus"]
    assert bank[0]["name"] == "Bank Statement"


def test_create_ka_default_niyam(page):
    from framework.crawler import discover_sidebar, build_sequence
    seq = build_sequence(discover_sidebar(page, wait_s=2), {})
    d = {}
    for m in seq["menus"]:
        d.update(dict(_flat(m.get("submenus") or [], (m["name"],))))
    assert d[("Master", "Currency")]["create"] is True        # master: Create button
    assert d[("Master", "Inventory Master", "Store")]["create"] is True
    assert d[("Sale", "Bill")]["create"] is True              # "+" hai
    assert d[("Sale", "Draft")]["create"] is False            # sirf list
    assert d[("Banking", "Bank Statement")]["create"] is True


def test_config_create_false_sidebar_ke_default_par_bhari_hai(page):
    from framework.crawler import discover_sidebar, build_sequence
    seq = build_sequence(discover_sidebar(page, wait_s=2), CONFIG)
    d = dict(_flat(seq["menus"][1]["submenus"], ("Master",)))
    assert d[("Master", "Inventory Master", "Store")]["create"] is False


def test_chhupa_item_chupchaap_nahi_girta_SKIP_wajah_ke_saath(page):
    from framework.crawler import discover_sidebar, build_sequence
    seq = build_sequence(discover_sidebar(page, wait_s=2), {})
    sale = dict(_flat(seq["menus"][2]["submenus"], ("Sale",)))
    secret = sale[("Sale", "Secret Thing")]
    assert secret["skip"] is True and "chhupa" in secret["skip_reason"]


def test_page_ginti(page):
    from framework.crawler import discover_sidebar, build_sequence, count_pages
    seq = build_sequence(discover_sidebar(page, wait_s=2), {})
    # Dashboard(1) + Item, Store, Deep Page, Currency (4) + Bill, Draft, Secret (3)
    # + Bank Statement (1) = 9
    assert count_pages(seq) == 9


# ---------- group kholna: toggle nahi ----------

def test_khule_group_ko_dobara_click_se_band_nahi_karta(bp, page):
    from framework.crawler import discover_sidebar
    c = _crawler(bp)
    master = dict(_flat(discover_sidebar(page, wait_s=2)))[("Master",)]
    assert c._ensure_open(master) is True
    assert c._expanded(master["sel"]) is True
    assert c._ensure_open(master) is True, "khule hue ko chhedna nahi tha"
    assert c._expanded(master["sel"]) is True, "dobara click se band ho gaya (toggle)"


def test_nested_group_bina_id_ke_khulta_hai(bp, page):
    from framework.crawler import discover_sidebar
    c = _crawler(bp)
    d = dict(_flat(discover_sidebar(page, wait_s=2)))
    assert c._open_trail([d[("Master",)], d[("Master", "Inventory Master")]])
    assert c._sel_visible('[id="menu-1-0-0-777"]'), "Item dikh hi nahi raha"


# ---------- poora crawl ----------

def _no_create(seq):
    """Test ko sirf page chahiye -- create form ka flow alag test hota hai."""
    def walk(nodes):
        for n in nodes or []:
            if "create" in n:
                n["create"] = False
            walk(n.get("children"))
    for m in seq["menus"]:
        walk(m.get("submenus"))


def _fresh_home(c):
    """Asli _home() URL kholta hai; yahan sidebar ko band haalat me wapas rakhte hain."""
    c._clicks = []

    def home():
        # set_content naya page banata hai aur click ki list saaf kar deta hai --
        # pehle usse apni list me utha lo.
        c._clicks += c.page.evaluate("() => window.__clicked || []")
        c.page.set_content(SIDEBAR)
    return home


def test_recursive_crawl_har_patte_tak_pahunchta_hai(bp, page):
    import framework.crawler as C
    from framework.crawler import discover_sidebar, build_sequence
    c = _crawler(bp)
    c._home = _fresh_home(c)
    old = C.OUT
    C.OUT = pathlib.Path(tempfile.mkdtemp()) / "out"
    (C.OUT / "raw").mkdir(parents=True)
    try:
        seq = build_sequence(discover_sidebar(page, wait_s=2), {})
        _no_create(seq)       # sirf page chalane hain, create form nahi
        master = next(m for m in seq["menus"] if m["name"] == "Master")
        top = {"name": "Master", "id": master["id"], "sel": master["sel"]}
        c._trail = [top]
        assert c._open_trail([top])
        c._crawl_nodes("Master", master["submenus"], [], [top], set())

        visited = {p["id"] for p in c.pages}
        assert visited == {"Master/Inventory Master/Item",
                           "Master/Inventory Master/Store",
                           "Master/Inventory Master/Deep Group > Deep Page".replace(" > ", "/"),
                           "Master/Currency"}, visited
        clicked = c._clicks + bp.page.evaluate("() => window.__clicked")
        assert "menu-1-0-0-777" in clicked and "menu-1-1-222" in clicked
        assert "menu-1-0-2-0-901" in clicked, "3 parat neeche ka page nahi khula"
        # har cheez ka haal -- koi chupchaap nahi chhooti
        assert all(x["status"] == C.PASS for x in c.status if x["type"] == "page"), c.status
    finally:
        C.OUT = old


def test_chhupa_item_crawl_me_SKIPPED_dikhta_hai(bp, page):
    import framework.crawler as C
    from framework.crawler import discover_sidebar, build_sequence
    c = _crawler(bp)
    c._home = _fresh_home(c)
    old = C.OUT
    C.OUT = pathlib.Path(tempfile.mkdtemp()) / "out"
    (C.OUT / "raw").mkdir(parents=True)
    try:
        seq = build_sequence(discover_sidebar(page, wait_s=2), {})
        sale = next(m for m in seq["menus"] if m["name"] == "Sale")
        top = {"name": "Sale", "id": sale["id"], "sel": sale["sel"]}
        c._trail = [top]
        c._open_trail([top])
        c._crawl_nodes("Sale", sale["submenus"], [], [top], set())
        sk = [x for x in c.status if x["status"] == C.SKIPPED]
        assert len(sk) == 1 and "Secret Thing" in sk[0]["name"], c.status
        assert {p["id"] for p in c.pages} == {"Sale/Bill", "Sale/Draft"}
    finally:
        C.OUT = old


def test_resume_pehle_ho_chuka_patta_dobara_nahi_karta(bp, page):
    import framework.crawler as C
    from framework.crawler import discover_sidebar, build_sequence
    c = _crawler(bp)
    c._home = _fresh_home(c)
    old = C.OUT
    C.OUT = pathlib.Path(tempfile.mkdtemp()) / "out"
    (C.OUT / "raw").mkdir(parents=True)
    try:
        seq = build_sequence(discover_sidebar(page, wait_s=2), {})
        bank = next(m for m in seq["menus"] if m["name"] == "Banking")
        top = {"name": "Banking", "id": bank["id"], "sel": bank["sel"]}
        c._trail = [top]
        c._open_trail([top])
        c._crawl_nodes("Banking", bank["submenus"], [], [top],
                       {"Banking/Bank Statement"})
        assert c.pages == [], "pehle ho chuka page dobara kiya gaya"
    finally:
        C.OUT = old


# ---------- khali crawl achhe data ko nahi mitata ----------

def test_khali_crawl_purana_achha_data_nahi_mitata(tmp_path, monkeypatch):
    import framework.crawler as C
    monkeypatch.setattr(C.logbook, "write", lambda *a, **k: None)   # asli log na chhedo
    old = C.OUT
    C.OUT = tmp_path
    try:
        (tmp_path / "pages.json").write_text(json.dumps([{"id": "x"}] * 20))
        (tmp_path / "metadata.json").write_text(json.dumps({"pages": [1] * 50}))
        c = C.Crawler.__new__(C.Crawler)
        c.pages, c.menus, c.status, c.control_room = [], [], [], {}
        c.seq, c.discover, c.sidebar_info = {"menus": []}, True, {}
        c.say = lambda *_a, **_k: None
        c._finish(1.0)
        assert len(json.loads((tmp_path / "pages.json").read_text())) == 20, \
            "khali crawl ne pichhla data mita diya"
        assert (tmp_path / "pages.last-failed.json").exists()
        assert (tmp_path / "crawl-summary.json").exists()
    finally:
        C.OUT = old


# ---------- jode gaye niyam ----------

def test_home_sign_in_page_par_chupchaap_aage_nahi_badhta():
    import inspect
    from framework.crawler import Crawler
    src = inspect.getsource(Crawler._home)
    assert "_on_login_page" in src and "_revive" in src


def test_sign_in_page_pehchana_jata_hai(bp):
    c = _crawler(bp)
    bp.page.set_content('<input id="userid"><button>SIGN IN</button>')
    assert c._on_login_page()
    bp.page.set_content(SIDEBAR)
    assert not c._on_login_page()


def test_discovery_band_karne_ka_raasta_hai():
    import inspect
    from framework.crawler import Crawler
    assert inspect.signature(Crawler.__init__).parameters["discover"].default is True
    from framework import run_crawler
    assert "--no-discover" in inspect.getsource(run_crawler.main)
