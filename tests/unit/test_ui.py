"""
UI ka test -- browser aur MargBooks dono ke bina.

Server stdlib ka hai, isliye use seedha uthakar HTTP call kar sakte hain.
Ye teen cheezein pakadta hai jo aksar toot ti hain:
  - save hua test list me aata hai ya nahi (ek baar nahi aa raha tha)
  - Excel import ki galtiyan saaf batayi ja rahi hain ya nahi
  - khali/galat input par saaf error milta hai ya chupchaap pass ho jata hai
"""
import json
import threading
import time
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

PORT = 8798
BASE = f"http://127.0.0.1:{PORT}"


@pytest.fixture(scope="module")
def server():
    from ui.server import Handler
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    time.sleep(0.4)
    yield srv
    srv.shutdown()


def _get(path):
    try:
        return urllib.request.urlopen(BASE + path).read()
    except urllib.error.HTTPError as e:
        return e.read()


def _post(path, obj):
    req = urllib.request.Request(BASE + path, data=json.dumps(obj).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        return json.loads(urllib.request.urlopen(req).read())
    except urllib.error.HTTPError as e:
        return json.loads(e.read())


# ---------- page ----------

def test_page_khulta_hai(server):
    html = _get("/").decode()
    assert "MargBooks QA" in html
    assert len(html) > 8000, "page adhoora lag raha hai"


# ---------- meta (dropdown ka data) ----------

def test_meta_me_screens_aur_fields_hain(server):
    m = json.loads(_get("/api/meta"))
    assert len(m["screens"]) > 40, "screens ki list chhoti hai"
    assert len(m["fields"]) > 50, "locators ki list chhoti hai"
    assert "open_screen" in m["actions"]


# ---------- test library ----------

def test_library_load_hoti_hai(server):
    """Library ab khali shuru hoti hai -- sirf login ke case bundled hain."""
    tests = json.loads(_get("/api/tests"))["tests"]
    assert tests, "ek bhi test load nahi hua"
    assert any(t["id"].startswith("TC_AUTH_") for t in tests)


def test_save_kiya_test_LIST_ME_AATA_HAI(server):
    """
    Ye asli bug tha: save ho jata tha par list me dikhta hi nahi tha, kyunki
    loader sirf testcases/*.yaml padhta tha, testcases/saved/ nahi.
    """
    res = _post("/api/save", {
        "name": "Pytest ka banaya test", "description": "check",
        "module": "masters", "author": "pytest",
        "steps": [{"action": "open_screen", "target": "item"},
                  {"action": "assert_text", "value": "Item List"}]})
    assert "id" in res, res
    cid = res["id"]
    try:
        listed = json.loads(_get("/api/tests"))["tests"]
        assert any(t["id"] == cid for t in listed), "save ke baad list me nahi aaya"
        one = json.loads(_get("/api/test?id=" + cid))
        assert len(one["steps"]) == 2
    finally:
        assert _post("/api/delete", {"id": cid})["deleted"]


@pytest.mark.parametrize("payload,why", [
    ({"name": "", "steps": [{"action": "goto"}]}, "naam khali"),
    ({"name": "x", "steps": []}, "koi step nahi"),
])
def test_adhoora_test_save_nahi_hota(server, payload, why):
    assert "error" in _post("/api/save", payload), why


def test_bina_test_chune_run_nahi_hota(server):
    assert "error" in _post("/api/run", {"ids": []})


# ---------- Excel / CSV import ----------

def test_khali_sheet_khud_import_ho_jati_hai(server):
    """Jo template hum de rahe hain, wo bina warning ke import hona chahiye --
    warna tester pehli hi koshish me atak jayega."""
    tmpl = _get("/api/template.csv").decode()
    assert "Test Name" in tmpl
    res = _post("/api/import", {"csv": tmpl})
    assert len(res["tests"]) >= 2, res
    assert not res["warnings"], res["warnings"]
    # Sale bill wala example bhi hona chahiye -- wahi sabse mushkil hai
    names = [t["name"].lower() for t in res["tests"]]
    assert any("sale bill" in n for n in names), names


def test_hinglish_shabd_samajh_aate_hain(server):
    """Tester 'kholo' likhe to bhi chale -- 'open_screen' yaad rakhna zaroori na ho."""
    res = _post("/api/import", {"csv":
        "Test Name,Description,Module,Action,Screen/Field,Value,Expected\n"
        "T1,x,masters,kholo,item,,\n"
        ",,,bharo,item.search,Sample,\n"})
    steps = res["tests"][0]["steps"]
    assert steps[0]["action"] == "open_screen"
    assert steps[1]["action"] == "fill"


def test_galat_action_pe_saaf_warning_milti_hai(server):
    res = _post("/api/import", {"csv":
        "Test Name,Description,Module,Action,Screen/Field,Value,Expected\n"
        "T1,x,masters,udna,chand,,\n"})
    assert any("udna" in w for w in res["warnings"]), res["warnings"]


def test_galat_screen_pe_milta_julta_naam_suggest_hota_hai(server):
    res = _post("/api/import", {"csv":
        "Test Name,Description,Module,Action,Screen/Field,Value,Expected\n"
        "T1,x,sales,open_screen,sale_bil,,\n"})
    joined = " ".join(res["warnings"])
    assert "sale_bill" in joined, f"suggestion nahi mili: {res['warnings']}"


def test_step_bina_test_name_ke_warning_deta_hai(server):
    res = _post("/api/import", {"csv":
        "Test Name,Description,Module,Action,Screen/Field,Value,Expected\n"
        ",,,click,item.new_btn,,\n"})
    assert res["warnings"], "bina naam ke step chupchaap nahi jana chahiye"


# ---------- UI ki bhasha ----------

HINGLISH = ["chalao", "chuno", "dabao", "karo", "kahan", "naya", "purane",
            "tumhara", "padho", "pehle", "likho", "jaake", "nahi hua",
            "koi nahi", "milta", "dikhega"]


def test_ui_ka_text_english_me_hai(server):
    """
    Dashboard English me hona chahiye (user ne yahi manga). Code ke comments
    Hinglish me theek hain -- wo screen pe nahi dikhte.
    """
    import re
    html = _get("/").decode()
    body = html[html.index("<body>"):]
    body = re.sub(r"<style.*?</style>|<script.*?</script>", "", body, flags=re.S)
    visible = re.sub(r"<[^>]+>", " ", body)
    found = sorted({w for w in HINGLISH
                    if re.search(rf"\b{re.escape(w)}\b", visible, re.I)})
    assert not found, f"UI me Hinglish shabd bache hain: {found}"


def test_import_ki_warning_english_me_hai(server):
    res = _post("/api/import", {"csv":
        "Test Name,Description,Module,Action,Screen/Field,Value,Expected\n"
        "T1,x,sales,open_screen,sale_bil,,\n"})
    joined = " ".join(res["warnings"]).lower()
    assert "did you mean" in joined, res["warnings"]


def test_save_ki_error_english_me_hai(server):
    assert "required" in _post("/api/save", {"name": "", "steps": []})["error"].lower()


# ---------- saadhi bhasha -> steps ----------

def test_plain_english_se_steps_bante_hain(server):
    r = _post("/api/parse", {"text":
        'Open item list\nType "Sample Item" in search\nWait 2 seconds\n'
        'Should see "Sample Item"'})
    acts = [(s["action"], s.get("target"), s.get("value")) for s in r["steps"]]
    assert acts == [
        ("open_screen", "item", None),
        ("fill", "item.search", "Sample Item"),
        ("sleep", None, "2"),
        ("assert_text", None, "Sample Item"),
    ], acts
    assert not r["issues"]
    assert r["module"] == "masters"


def test_hinglish_se_bhi_steps_bante_hain(server):
    r = _post("/api/parse", {"text":
        'Item list kholo\nSearch me "Paracetamol" likho\n"Paracetamol" dikhna chahiye'})
    assert [s["action"] for s in r["steps"]] == ["open_screen", "fill", "assert_text"]
    assert not r["issues"]


def test_field_screen_ke_hisaab_se_chunta_hai(server):
    """
    'search me likho' ka matlab kis screen pe ho -- ye us waqt khuli screen se
    tay hota hai. Item pe item.search, Ledger pe party.search.
    """
    a = _post("/api/parse", {"text": 'Open item list\nType "x" in search'})
    b = _post("/api/parse", {"text": 'Open ledger master\nType "x" in search'})
    assert a["steps"][1]["target"] == "item.search"
    assert b["steps"][1]["target"] == "party.search"


def test_nahi_dikhna_chahiye_alag_action_banta_hai(server):
    r = _post("/api/parse", {"text": '"Sample Item" nahi dikhna chahiye'})
    assert r["steps"][0]["action"] == "assert_no_text", r["steps"]


def test_samajh_na_aane_par_ANDAZA_NAHI_lagata(server):
    """
    Sabse zaroori niyam: jo line samajh na aaye uspe chupchaap koi step mat
    banao. Galat step chupke se save ho jana, kuch na banne se kahin bura hai.
    """
    r = _post("/api/parse", {"text": "Open item list\nudan bhari lekar chand par jao"})
    assert len(r["steps"]) == 1, "samajh na aane wali line se bhi step ban gaya"
    assert r["issues"] and r["issues"][0]["line"] == 2


@pytest.mark.parametrize("text,why", [
    ('Type in search', "value nahi di"),
    ('Kuch kholo', "screen nahi bataya"),
    ('Click on the flying button', "aisa koi field nahi"),
])
def test_adhoori_line_par_saaf_wajah_milti_hai(server, text, why):
    r = _post("/api/parse", {"text": text})
    assert r["issues"], why
    i = r["issues"][0]
    assert i["why"] and i["hint"], "wajah aur hint dono chahiye"


def test_issue_message_english_me_hai(server):
    r = _post("/api/parse", {"text": "Kuch kholo"})
    joined = (r["issues"][0]["why"] + r["issues"][0]["hint"]).lower()
    assert "did you mean" in joined or "could not" in joined, joined


def test_parse_kiye_steps_seedha_save_ho_jate_hain(server):
    """Parser ka output aur save ka format ek hi hona chahiye."""
    r = _post("/api/parse", {"text":
        'Open ledger master\nType "Cash Account" in search\nShould see "Cash Account"'})
    res = _post("/api/save", {"name": "parsed roundtrip", "description": "x",
                              "module": r["module"], "steps": r["steps"],
                              "author": "pytest"})
    assert "id" in res, res
    try:
        one = json.loads(_get("/api/test?id=" + res["id"]))
        assert len(one["steps"]) == 3
    finally:
        _post("/api/delete", {"id": res["id"]})


# ---------- environments (UAT / prod switch) ----------

@pytest.fixture
def clean_envs(tmp_path):
    """
    Har environment test apni alag file pe chale.

    Pehle sab ek hi config/environments.json share karte the -- ek test ki
    chhodi hui haalat agle test ko gira deti thi. Akele chalane par pass,
    saath me fail: aisa bug dhoondhna sabse mushkil hota hai.
    """
    from ui import envs
    old = envs.FILE
    envs.FILE = tmp_path / "environments.json"
    envs.save(envs._blank())
    yield
    envs.FILE = old


def test_environment_add_aur_switch_hota_hai(server, clean_envs):
    """
    Tester UI se hi UAT ka URL aur login daal sake -- .env file kholni na pade.
    """
    r = _post("/api/env/save", {
        "name": "uat-test", "login_url": "https://accounts.margbooks.com",
        "app_url": "https://uat.margbooks.com", "user": "u@x.com",
        "password": "secret", "company": "UAT CO", "allow_writes": True})
    assert "name" in r, r
    try:
        d = json.loads(_get("/api/envs"))
        e = [x for x in d["envs"] if x["name"] == "uat-test"][0]
        assert e["app_url"] == "https://uat.margbooks.com"
        assert e["has_password"] is True
        assert "password" not in e, "password UI ko wapas nahi bhejna chahiye"

        assert _post("/api/env/use", {"name": "uat-test"})["active"] == "uat-test"
        from config.settings import settings
        assert settings.BASE_URL == "https://uat.margbooks.com"
        assert settings.ALLOW_DESTRUCTIVE is True
    finally:
        _post("/api/env/use", {"name": "default"})
        _post("/api/env/delete", {"name": "uat-test"})


def test_galat_url_reject_hota_hai(server, clean_envs):
    r = _post("/api/env/save", {"name": "bad", "login_url": "accounts.margbooks.com",
                                "app_url": "https://x.com"})
    assert "error" in r and "http" in r["error"].lower()


def test_password_khali_chhodne_par_purana_rehta_hai(server, clean_envs):
    _post("/api/env/save", {"name": "keep-pw", "login_url": "https://a.com",
                            "app_url": "https://b.com", "password": "first"})
    _post("/api/env/save", {"name": "keep-pw", "login_url": "https://a.com",
                            "app_url": "https://b.com", "password": ""})
    try:
        from ui import envs
        assert envs.load()["envs"]["keep-pw"]["password"] == "first"
    finally:
        _post("/api/env/delete", {"name": "keep-pw"})


# ---------- transaction form ke unche star ke kaam ----------

def test_sale_bill_ka_poora_test_plain_language_se_banta_hai(server):
    """
    Grid me seedha 'fill' kaam nahi karta. Isliye tester ko bhi wahi shabd
    milne chahiye jo POM use karta hai: party set karo, item jodo, band karo.
    """
    r = _post("/api/parse", {"text":
        'Sale bill kholo\n'
        'Party set karo "Cash Account"\n'
        'Add item "Sample Item | 2"\n'
        '1 line honi chahiye\n'
        'Bill band karo'})
    acts = [s["action"] for s in r["steps"]]
    assert acts == ["open_screen", "set_party", "add_item",
                    "expect_lines", "close_form"], (acts, r["issues"])
    assert not r["issues"]
    assert r["steps"][2]["value"] == "Sample Item | 2"
    assert r["module"] == "sales"


def test_grid_me_seedha_fill_karne_wala_koi_test_nahi_bacha(server):
    """
    Grid cell tab tak <input> banta hi nahi jab tak focus na ho. 'fill
    sale.qty_cell' isi wajah se hamesha fail hota tha.
    """
    from framework.case_loader import load_all
    bad = []
    for c in load_all():
        for s in c.steps:
            if s.get("action") == "fill" and str(s.get("target", "")).startswith(
                    ("sale.qty", "sale.mrp", "sale.product", "sale.amount")):
                bad.append(f"{c.id}: {s['target']}")
    assert not bad, ("ye tests grid me seedha fill kar rahe hain, jo kaam nahi "
                     f"karta -- add_item use karo: {bad}")


# ---------- menu tree (MargBooks ke sidebar jaisa) ----------

def test_menu_tree_api_deta_hai(server):
    d = json.loads(_get("/api/menu"))
    labels = [n["label"] for n in d["tree"]]
    for must in ("Master", "Sale", "Purchase", "Accounting Trans.",
                 "Stock Management"):
        assert must in labels, f"'{must}' menu me nahi hai. Mile: {labels}"


def test_menu_ka_dhaancha_asli_app_jaisa_hai(server):
    """Master > Inventory Master > Item -- jaisa MargBooks me hai."""
    from framework import menu_tree
    assert menu_tree.label_path("master.inventory.item") == \
        "Master > Inventory Master > Item"
    assert menu_tree.label_path("sale.bill") == "Sale > Bill"
    assert menu_tree.label_path("accounting.payment") == \
        "Accounting Trans. > Payment"


def test_har_menu_leaf_ka_POM_hai(server):
    """
    Tester ko ye nahi sochna chahiye ki "Salt ke liye kaunsi class hai".
    Har menu item ke peeche kuch na kuch hona chahiye.
    """
    from pages.registry import describe
    rows = describe()
    assert len(rows) >= 40, f"sirf {len(rows)} menu items ka POM hai"
    assert all(r["pom"] for r in rows)
    # jinke liye humne khaas kaam kiya, unke liye khaas class honi chahiye
    special = {r["screen"]: r["pom"] for r in rows}
    assert "ItemPage" in special.get("item", "")
    assert "PartyPage" in special.get("party", "")


def test_har_test_ke_saath_menu_ka_khaana_aata_hai(server):
    """
    Test list menu ke hisaab se group hoti hai, isliye har test ke saath
    ye do khaane aane chahiye -- chahe wo kisi menu se juda ho ya na ho.
    (Login ke case kisi menu ke neeche nahi aate: wo app me ghusne se
    PEHLE hote hain.)
    """
    tests = json.loads(_get("/api/tests"))["tests"]
    for t in tests:
        assert "menu" in t and "menu_id" in t, t["id"]


def test_menu_node_se_POM_mil_jata_hai(server):
    """page_for_menu('sale.bill', prefer_create=True) -> naya Sale Bill form."""
    import inspect
    from pages import registry
    src = inspect.getsource(registry.page_for_menu)
    assert "prefer_create" in src
    from framework import menu_tree
    node = menu_tree.by_id("sale.bill")
    assert node["screen"] == "sale_list" and node["create"] == "sale_bill"


def test_purane_environments_json_ke_khali_khaane_bhar_jate_hain(server, tmp_path):
    """
    ASLI BUG: environments.json purane version me bana tha jisme user aur
    company likhe hi nahi jate the. UI me hamesha 'user —' dikhta raha,
    jabki .env me dono bhare the -- aur file ek baar ban jaye to us purani
    haalat me atki reh jati.
    """
    from ui import envs
    from config.settings import settings
    old_file = envs.FILE
    envs.FILE = tmp_path / "old.json"
    envs.FILE.write_text(json.dumps({"active": "default", "envs": {"default": {
        "name": "default", "login_url": "https://accounts.margbooks.com",
        "app_url": "https://books5.margbooks.com",
        "user": "", "password": "", "company": ""}}}))
    settings.USER = settings.USER or "ajay@x.com"
    settings.COMPANY = settings.COMPANY or "TEST CO"
    try:
        e = envs.listing()["envs"][0]
        assert e["user"], "user khali reh gaya"
        assert e["company"], "company khali reh gayi"
    finally:
        envs.FILE = old_file


def test_bhari_hui_value_kabhi_nahi_badalti(server, tmp_path):
    """User ne jaan-boojh kar jo value daali hai, .env usse na dabaye."""
    from ui import envs
    from config.settings import settings
    old_file = envs.FILE
    envs.FILE = tmp_path / "mine.json"
    envs.FILE.write_text(json.dumps({"active": "uat", "envs": {"uat": {
        "name": "uat", "login_url": "https://accounts.margbooks.com",
        "app_url": "https://uat.margbooks.com",
        "user": "mera@uat.com", "password": "p", "company": "UAT CO"}}}))
    settings.USER = "koi.aur@x.com"
    try:
        assert envs.listing()["envs"][0]["user"] == "mera@uat.com"
    finally:
        envs.FILE = old_file


# ---------- test edit / delete ----------

def test_built_in_test_delete_nahi_hota(server):
    """
    Built-in test agle update me wapas aa jayega. Use mitane ka option dena
    jhooth hoga -- tester ko lagega mit gaya, phir wapas aa jayega.
    """
    from ui import store
    built_in = next((c for c in store.list_all()
                     if not c.source_file.startswith("saved")), None)
    assert built_in, "koi built-in test hai hi nahi"
    r = _post("/api/delete", {"id": built_in.id})
    assert "error" in r and "built-in" in r["error"].lower()
    assert store.get(built_in.id), "built-in test mit gaya!"


def test_tester_ka_test_delete_hota_hai(server):
    from ui import store
    cid = store.save(name="Delete hone wala", description="x", module="masters",
                     steps=[{"action": "open_screen", "target": "item"}])["id"]
    assert _post("/api/delete", {"id": cid})["deleted"]
    assert not store.get(cid)


def test_na_maujood_test_delete_karne_par_saaf_error(server):
    r = _post("/api/delete", {"id": "TC_AISA_KOI_NAHI"})
    assert "error" in r and "not found" in r["error"].lower()


def test_edit_karne_par_wahi_id_update_hoti_hai_nayi_nahi(server):
    """
    Edit me nayi id ban jaye to library me do copy ho jayengi -- purani aur
    nayi -- aur tester ko samajh nahi aayega kaunsi chal rahi hai.
    """
    from ui import store
    cid = store.save(name="Update hone wala", description="pehla",
                     module="masters",
                     steps=[{"action": "open_screen", "target": "item"}])["id"]
    try:
        before = len(store.list_all())
        r = _post("/api/save", {"id": cid, "name": "Update hone wala",
                                "description": "doosra", "module": "masters",
                                "steps": [{"action": "open_screen", "target": "party"},
                                          {"action": "assert_text", "value": "Ledger"}]})
        assert r["id"] == cid, f"nayi id ban gayi: {r['id']}"
        assert len(store.list_all()) == before, "duplicate test ban gaya"
        d = store.detail(cid)
        assert d["description"] == "doosra" and len(d["steps"]) == 2
    finally:
        store.delete(cid)


def test_detail_me_wahi_wapas_aata_hai_jo_bhara_tha(server):
    """Edit form bharne ke liye poora record chahiye -- aadha nahi."""
    from ui import store
    cid = store.save(name="Poora record", description="kya check karta hai",
                     module="sales", author="ajay",
                     steps=[{"action": "open_screen", "target": "sale_bill"}])["id"]
    try:
        d = json.loads(_get("/api/test?id=" + cid))
        assert d["title"] == "Poora record"
        assert d["description"] == "kya check karta hai"
        assert d["author"] == "ajay"
        assert d["module"] == "sales"
        assert d["editable"] is True
        assert len(d["steps"]) == 1
    finally:
        store.delete(cid)


# ---------- allow writes ----------

def test_naya_environment_writes_ON_ke_saath_banta_hai(server, tmp_path):
    """
    Writes band rakhne se aadhe test SKIP ho jate the aur suite adhoori
    lagti thi. Ye QA ka tool hai aur demo company par chalta hai.
    """
    from ui import envs
    old = envs.FILE
    envs.FILE = tmp_path / "new.json"
    try:
        envs.save(envs._blank())
        assert envs.listing()["envs"][0]["allow_writes"] is True
    finally:
        envs.FILE = old


def test_writes_ek_click_me_badal_jata_hai(server, tmp_path):
    """
    Sirf writes on/off karne ke liye poora modal kholna zyada hai --
    ye sabse zyada badli jaane wali setting hai.
    """
    from ui import envs
    old = envs.FILE
    envs.FILE = tmp_path / "t.json"
    try:
        envs.save(envs._blank())
        r = _post("/api/env/writes", {"name": "default", "on": False})
        assert r["allow_writes"] is False
        assert envs.listing()["envs"][0]["allow_writes"] is False

        r = _post("/api/env/writes", {"name": "default", "on": True})
        assert r["allow_writes"] is True

        from config.settings import settings
        assert settings.ALLOW_DESTRUCTIVE is True, \
            "toggle ke baad settings me nahi laga -- run par asar nahi hoga"
    finally:
        envs.FILE = old


def test_galat_naam_par_saaf_error(server):
    assert "error" in _post("/api/env/writes", {"name": "aisa-koi-nahi", "on": True})


def test_edit_modal_SAVED_value_hi_dikhata_hai(server, tmp_path):
    """
    Edit me hamesha 'checked' dikhana jhooth hoga: band setting khuli dikhti,
    aur Save dabate hi chup-chaap ON ho jati. Modal wahi dikhata hai jo
    file me hai -- badalne ke liye list wala toggle hai.
    """
    from ui import envs
    old = envs.FILE
    envs.FILE = tmp_path / "e.json"
    try:
        envs.save(envs._blank())
        _post("/api/env/writes", {"name": "default", "on": False})
        assert envs.listing()["envs"][0]["allow_writes"] is False
    finally:
        envs.FILE = old
