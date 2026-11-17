"""
AI self-healing ka test -- asli browser me, par AI ko nakli banakar.

Asli Gemini call nahi karte: wo dheemi hai, paise/quota leti hai, aur har
baar bilkul ek jaisa jawab nahi degi -- yaani test hi anishchit ho jayega.
Isliye AI ka jawab hum tay karte hain aur dekhte hain ki uske BAAD ka
hissa (jaanch aur registry me likhna) sahi chalta hai ya nahi.
"""
import pytest
from playwright.sync_api import sync_playwright

PAGE = """
<div style="padding:16px">
  <label>Party Name</label>
  <input type="text" id="txtLedgerName99" formcontrolname="ledgerName">
  <label>Item Name</label>
  <input type="text" id="txtItemName">
  <button id="btnSave7">F10 Save</button>
  <button class="del" id="Griddeletetbtn9">Delete</button>
  <select id="ddlUnit"><option>PCS</option></select>
</div>
"""


@pytest.fixture
def page(tmp_path):
    import framework.catalogue as cat
    cat.FILE = tmp_path / "locators_registry.json"
    cat._OLD_FILE = tmp_path / "nope.json"
    with sync_playwright() as pw:
        b = pw.chromium.launch(headless=True)
        pg = b.new_page(viewport={"width": 1280, "height": 720})
        pg.set_content(PAGE)
        yield pg
        b.close()


def _fake_ai(monkeypatch, index, why="matched label"):
    """AI ka jawab tay kar do."""
    from framework import ai
    monkeypatch.setattr(ai, "available", lambda: {"active": "gemini"})
    monkeypatch.setattr(ai, "ask_json",
                        lambda *a, **k: {"index": index, "why": why})


def _index_of(page, want, el_id):
    from framework.heal import SLIM_DOM_JS
    els = page.evaluate(SLIM_DOM_JS, want)
    hit = next((e for e in els if e["id"] == el_id), None)
    assert hit, f"{el_id} slim DOM me hai hi nahi"
    return hit["i"]


def test_AI_ka_bataya_field_mil_jata_hai(page, monkeypatch):
    from framework import heal
    _fake_ai(monkeypatch, _index_of(page, "type", "txtItemName"))
    got = heal.heal(page, "item.name", want="type", verbose=False)
    assert got and "txtItemName" in got["selector"], got


def test_theek_kiya_hua_locator_registry_me_likha_jata_hai(page, monkeypatch):
    """Agli baar AI ki zaroorat na pade -- warna wo har run me lagega."""
    from framework import heal, catalogue
    _fake_ai(monkeypatch, _index_of(page, "type", "txtItemName"))
    heal.heal(page, "item.name", want="type", verbose=False)
    saved = str(catalogue.load())
    assert "txtItemName" in saved, "registry me gaya hi nahi"
    assert "healed_for" in saved


def test_delete_wale_element_AI_ko_DIKHTE_HI_NAHI(page):
    """
    Pehli rok: jo cheez list me hai hi nahi, AI use chun hi nahi sakta.
    Rokna, baad me pakadne se behtar hai.
    """
    from framework.heal import SLIM_DOM_JS
    els = page.evaluate(SLIM_DOM_JS, "click")
    ids = [e["id"] for e in els]
    assert "Griddeletetbtn9" not in ids, f"delete button AI ko bheja ja raha hai: {ids}"
    assert "btnSave7" in ids, "sahi button bhi gayab ho gaya"


def test_delete_phir_bhi_aa_jaye_to_jaanch_rok_deti_hai(page, monkeypatch):
    """
    Doosri rok. Pehli rok DOM me hai; agar wo kabhi chhoot jaye (naya class
    naam, alag shabd), to ye wali rokegi.

    DHYAAN: ye jaanch ALLOW_DESTRUCTIVE par nirbhar NAHI hai. Wo setting
    jaan-boojh kar likhe delete test ke liye hai -- par AI ka delete button
    CHUN lena alag baat hai. Wo locator ki galti hai, ijazat ki nahi.
    """
    from framework import heal
    from config.settings import settings
    monkeypatch.setattr(settings, "ALLOW_DESTRUCTIVE", True)
    ok, why = heal._verify(page, "button#Griddeletetbtn9", "click")
    assert not ok, "writes ON hone par delete button pass ho gaya"
    assert "delete" in why.lower()


def test_sahi_button_pass_ho_jata_hai(page, monkeypatch):
    from framework import heal
    ok, why = heal._verify(page, "button#btnSave7", "click")
    assert ok, why


def test_likhne_ke_liye_dropdown_bataye_to_nahi_lete(page, monkeypatch):
    from framework import heal
    els = page.evaluate(heal.SLIM_DOM_JS, "any")
    sel_idx = next((e["i"] for e in els if e["id"] == "ddlUnit"), None)
    if sel_idx is None:
        pytest.skip("select slim DOM me nahi aaya")
    _fake_ai(monkeypatch, sel_idx)
    assert heal.heal(page, "item.name", want="type", verbose=False) is None


def test_AI_mana_kar_de_to_kuch_nahi_hota(page, monkeypatch):
    """Andaza lagane se behtar hai saaf mana karna."""
    from framework import heal
    _fake_ai(monkeypatch, -1, why="nothing matches")
    assert heal.heal(page, "kuch.bhi", want="type", verbose=False) is None


def test_AI_key_na_ho_to_chupchaap_chhod_deta_hai(page, monkeypatch):
    from framework import ai, heal
    monkeypatch.setattr(ai, "available", lambda: {"active": None})
    assert heal.heal(page, "item.name", want="type", verbose=False) is None


def test_slim_DOM_me_koi_VALUE_nahi_jati(page):
    """Password, GSTIN, party ka data -- kuch bahar nahi jana chahiye."""
    from framework.heal import SLIM_DOM_JS
    page.fill("#txtLedgerName99", "SUPER SECRET PARTY")
    els = page.evaluate(SLIM_DOM_JS, "type")
    assert not any("SUPER SECRET" in str(e) for e in els), \
        f"field ki value AI ko ja rahi hai: {els}"
