"""
Autolearn ka test -- MargBooks jaisa HTML bana kar, asli browser me.

Ye test isliye likha gaya kyunki autolearn ne ek baar GALAT element seekh
liya tha aur locators file me SAVE bhi kar diya tha:

    fill sale.party  ->  select#txtaskpartyinretailbilling

Wo Party Name ka field nahi tha, Settings panel ka dropdown tha -- jo screen
par dikh bhi nahi raha tha. Autolearn ne bas id me "party" shabd dekha.

Yahan wahi jaal dobara bichhaya gaya hai.
"""
import pytest
from playwright.sync_api import sync_playwright

TRAP_HTML = """
<div style="height:100vh">
  <label>Party Name</label>
  <input type="text" id="txtLedgerName27" name="txtLedgerName27">
  <button id="btnSave27">F10 / End Save</button>
  <a id="dropdownMenuButton" class="pro-pic dropdown-toggle">Profile</a>
  <input type="search" id="searchItems" placeholder="Search here..">
</div>
<div style="position:absolute;top:3000px">
  <select id="txtaskpartyinretailbilling" name="askpartyinretailbilling">
    <option>Don't Ask</option></select>
  <button class="mksBtn del" id="Griddeletetbtn714"></button>
</div>
"""


@pytest.fixture(scope="module")
def page():
    with sync_playwright() as pw:
        b = pw.chromium.launch(headless=True)
        pg = b.new_page(viewport={"width": 1280, "height": 720})
        pg.set_content(TRAP_HTML)
        yield pg
        b.close()


def _learn(page, key, want="any"):
    from framework import autolearn
    from framework.locator_store import store
    store.add(key, [])            # key maujood par khali -- asli haalat
    return autolearn.learn(page, key, want=want, verbose=False)


def test_settings_ka_dropdown_party_field_samajh_kar_nahi_seekhta(page):
    """ASLI BUG: id 'txtaskpartyinretailbilling' me 'party' hai, par wo
    Party Name field nahi hai -- aur screen pe dikh bhi nahi raha."""
    r = _learn(page, "t.party", want="type")
    assert not r or "askparty" not in r["selector"], \
        f"phir wahi galat element seekh liya: {r}"


def test_camelCase_id_me_asli_shabd_pehchanta_hai(page):
    """'btnSave27' me 'Save' asli shabd hai -- ise seekhna chahiye."""
    r = _learn(page, "t.save_btn", want="click")
    assert r and "btnSave27" in r["selector"], r


def test_delete_button_kabhi_nahi_seekhta(page):
    r = _learn(page, "t.delete", want="click")
    assert not r, f"delete button seekh liya: {r}"


def test_screen_se_bahar_ka_element_nahi_seekhta(page):
    r = _learn(page, "t.askpartyinretailbilling", want="any")
    assert not r, f"viewport ke bahar ka element seekh liya: {r}"


def test_likhne_ke_liye_dropdown_nahi_chunta(page):
    """want='type' ka matlab input chahiye -- <select> me type nahi hota."""
    from framework import autolearn
    hits = page.evaluate(autolearn.FIND_JS,
                         {"words": ["party"], "want": "type"})
    assert all("select" not in h["tag"] for h in hits), hits


def test_profile_icon_seekh_leta_hai(page):
    """Jo cheez sach me chahiye thi -- wo mil jaani chahiye."""
    r = _learn(page, "t.profile", want="click")
    assert r and "dropdownMenuButton" in r["selector"], r
