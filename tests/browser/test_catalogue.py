"""
Element catalogue ka test -- MargBooks jaisa page bana kar.

Ye wo cheez hai jo agent ko khud seekhne layak banati hai: har screen ke
saare field ka id, CSS aur XPath yaad rakh lo, taaki agli baar tester saadhi
bhasha me kuch bhi maange to mil jaye.
"""
import pytest
from playwright.sync_api import sync_playwright

# Asli item-create page jaisa -- camelCase id, label alag element me
ITEM_CREATE = """
<div style="padding:16px">
  <label>Item Code</label><input type="text" id="txtItemCode" formcontrolname="itemcode">
  <label>Barcode</label><input type="text" id="txtBarcode" formcontrolname="Barcode">
  <div class="row"><span>Item Name</span>
    <input type="text" id="txtItemName" formcontrolname="itemName"></div>
  <div class="row"><span>M.R.P</span>
    <input type="text" id="txtMRP" formcontrolname="mrp"></div>
  <div class="row"><span>Unit</span>
    <select id="ddlUnit"><option>PCS</option></select></div>
  <button id="btnSave27">F10 / End Save</button>
  <button class="mksBtn del" id="Griddeletetbtn714">Delete</button>
</div>
"""


@pytest.fixture(scope="module")
def page(tmp_path_factory):
    # catalogue ko alag file me likho -- asli file kharab na ho
    import framework.catalogue as cat
    cat.FILE = tmp_path_factory.mktemp("cat") / "catalogue.json"
    with sync_playwright() as pw:
        b = pw.chromium.launch(headless=True)
        pg = b.new_page(viewport={"width": 1280, "height": 720})
        pg.set_content(ITEM_CREATE)
        yield pg
        b.close()


@pytest.fixture(scope="module")
def captured(page):
    from framework import catalogue
    return catalogue.capture(page, "item_create")


def test_screen_ke_saare_element_yaad_ho_jate_hain(captured):
    assert captured["found"] >= 6, captured
    assert captured["new"] >= 6


def test_har_element_ka_css_aur_xpath_dono_bante_hain(captured):
    from framework import catalogue
    rows = catalogue.screen_elements("item_create")
    assert rows
    for r in rows:
        assert r["css"], f"{r['key']} ka CSS nahi bana"
        assert r["xpath"], f"{r['key']} ka XPath nahi bana"


def test_paas_ka_label_bhi_yaad_rehta_hai(captured):
    """Tester 'Item Name' likhega, 'txtItemName' nahi."""
    from framework import catalogue
    labels = {r["label"] for r in catalogue.screen_elements("item_create")}
    assert "Item Name" in labels
    assert "M.R.P" in labels


@pytest.mark.parametrize("phrase,expect_id", [
    ("Item Name", "txtItemName"),
    ("item name", "txtItemName"),
    ("MRP", "txtMRP"),
    ("M.R.P", "txtMRP"),
    ("Barcode", "txtBarcode"),
    ("Item Code", "txtItemCode"),
])
def test_layman_bhasha_se_field_mil_jata_hai(captured, phrase, expect_id):
    """
    Yahi asli faayda hai: tester ki bhasha se seedha locator.
    'txtItemName' andaze se kabhi nahi milta -- maine 'txtitemname' try kiya
    tha aur fail ho gaya tha.
    """
    from framework import catalogue
    hit = catalogue.resolve("item_create", phrase, kind="type")
    assert hit, f"'{phrase}' nahi mila"
    assert expect_id in hit["css"], f"{phrase} -> {hit['css']}"


def test_likhne_ke_liye_dropdown_nahi_chunta(captured):
    from framework import catalogue
    hit = catalogue.resolve("item_create", "Item Name", kind="type")
    assert "select" not in hit["css"].lower()


def test_button_maangne_par_button_hi_milta_hai(captured):
    from framework import catalogue
    hit = catalogue.resolve("item_create", "Save", kind="click")
    assert hit and "btnSave27" in hit["css"], hit


def test_delete_wala_element_kabhi_nahi_deta(captured):
    """
    Catalogue me delete bhi rehta hai (jaankari ke liye), par resolve() use
    kabhi nahi lautata -- warna koi test galti se delete daba dega.
    """
    from framework import catalogue
    hit = catalogue.resolve("item_create", "Delete", kind="click")
    assert hit is None or "Griddelete" not in hit["css"]
    rows = catalogue.screen_elements("item_create")
    assert any(r["danger"] for r in rows), "delete catalogue me mark hona chahiye"


def test_bakwaas_maangne_par_None_deta_hai(captured):
    """Andaza lagane se behtar hai saaf mana kar dena."""
    from framework import catalogue
    assert catalogue.resolve("item_create", "udan khatola", kind="type") is None


def test_na_mile_to_milte_julte_naam_batata_hai(captured):
    from framework import catalogue
    names = catalogue.suggestions("item_create", "Item Naam")
    assert names and any("Item" in str(n) for n in names)


def test_dobara_scan_karne_pe_purana_gyaan_nahi_mitta(page):
    """
    Catalogue sirf BADHTA hai. Ek run me koi field na dikhe (popup band tha)
    to iska matlab ye nahi ki wo field hai hi nahi.
    """
    from framework import catalogue
    before = len(catalogue.screen_elements("item_create"))
    page.set_content("<div><input id='txtNewField'><label>New Field</label></div>")
    catalogue.capture(page, "item_create")
    after = catalogue.screen_elements("item_create")
    assert len(after) >= before, "purane element mit gaye"
    assert any("txtNewField" in r["css"] for r in after), "naya element nahi juda"
