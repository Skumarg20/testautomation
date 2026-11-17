"""
Create form ke locators ka test -- MargBooks jaisa HTML bana kar.

Ye test isliye hai kyunki item/party ke CREATE form kabhi dump nahi hue the,
aur mere locators (input[name="description"]) sirf andaza the. Asli run me
saare create test isi wajah se fail hue.

Ab 'nearlabel=' wala tareeka hai: label ka text dhoondho, phir usi dabbe ka
input uthao. Angular ke form aksar <label for=...> use nahi karte, isliye
Playwright ka get_by_label wahan kaam nahi karta.
"""
import pytest
from playwright.sync_api import sync_playwright

# Teen tarah ke form -- teeno asli apps me milte hain
FORMS = {
    "label_for": """
        <label for="d1">Description</label><input id="d1" type="text">
        <label for="m1">M.R.P</label><input id="m1" type="text">
    """,
    "bootstrap_row": """
        <div class="row"><div class="col-3"><label>Description</label></div>
          <div class="col-9"><input type="text" class="form-control"></div></div>
        <div class="row"><div class="col-3"><label>M.R.P</label></div>
          <div class="col-9"><input type="text" class="form-control"></div></div>
    """,
    "table_form": """
        <table><tr><td>Description</td><td><input type="text"></td></tr>
               <tr><td>M.R.P</td><td><input type="text"></td></tr></table>
    """,
}


@pytest.fixture(scope="module")
def bp_factory():
    with sync_playwright() as pw:
        b = pw.chromium.launch(headless=True)
        pg = b.new_page(viewport={"width": 1280, "height": 720})

        from framework.base_page import BasePage

        def make(html):
            pg.set_content(f"<div style='padding:20px'>{html}</div>")
            return BasePage(pg)

        yield make
        b.close()


@pytest.mark.parametrize("kind", list(FORMS), ids=list(FORMS))
def test_label_ke_paas_wala_input_mil_jata_hai(bp_factory, kind):
    bp = bp_factory(FORMS[kind])
    el = bp._near_label("Description")
    el.fill("Paracetamol 500")
    assert el.input_value() == "Paracetamol 500"


def test_do_alag_label_alag_input_dete_hain(bp_factory):
    """'Description' aur 'M.R.P' ko aapas me nahi mila dena chahiye."""
    bp = bp_factory(FORMS["bootstrap_row"])
    bp._near_label("Description").fill("Item A")
    bp._near_label("M.R.P").fill("250")
    assert bp._near_label("Description").input_value() == "Item A"
    assert bp._near_label("M.R.P").input_value() == "250"


def test_label_na_ho_to_saaf_fail_hota_hai(bp_factory):
    """Galat locator chupke se chalne se behtar hai saaf fail."""
    bp = bp_factory(FORMS["table_form"])
    el = bp._near_label("Aisa Koi Field Nahi")
    assert el.count() == 0


def test_checkbox_aur_hidden_ko_nahi_uthata(bp_factory):
    """Label ke paas checkbox ho to text field hi chahiye."""
    bp = bp_factory("""
        <div class="row"><label>GSTIN</label>
          <input type="hidden" value="x">
          <input type="checkbox">
          <input type="text" id="real"></div>
    """)
    bp._near_label("GSTIN").fill("07ABCDE1234F1Z5")
    assert bp.page.locator("#real").input_value() == "07ABCDE1234F1Z5"


# ---------- Settings panel ka element nahi uthana ----------

TRAP = """
<div style="padding:20px">
  <label>Ledger Name</label>
  <input type="text" id="txtlegername" formcontrolname="ledgerName">
</div>
<!-- Neeche Settings panel -- screen se bahar. Ismein wahi formcontrolname hai. -->
<div style="position:absolute; top:3000px">
  <label>Ledger Name</label>
  <select id="name" formcontrolname="ledgerName" class="form-control mr-3 w-80">
    <option>No</option><option>Yes</option></select>
</div>
"""


def test_screen_se_bahar_ka_settings_dropdown_nahi_uthata(bp_factory):
    """
    ASLI BUG: nearlabel ne Settings panel ka <select id="name"> utha liya tha,
    jo page me 3000px neeche chhupa tha. Playwright 15 second atak gaya
    ("element is outside of the viewport").

    Wahi galti autolearn me pehle ho chuki thi -- wahan viewport check lagaya
    tha, yahan lagana bhool gaya.
    """
    bp = bp_factory(TRAP)
    el = bp._near_label("Ledger Name")
    el.fill("QA Party")
    assert bp.page.locator("#txtlegername").input_value() == "QA Party"
    assert bp.page.locator("#name").input_value() != "QA Party"


def test_likhne_ke_liye_input_chunta_hai_select_nahi(bp_factory):
    """Ek hi dabbe me input aur select dono hon to input chahiye."""
    bp = bp_factory("""
      <div class="row"><label>State</label>
        <select><option>Delhi</option></select>
        <input type="text" id="real"></div>
    """)
    bp._near_label("State").fill("Haryana")
    assert bp.page.locator("#real").input_value() == "Haryana"


# ---------- failure khud bata de ki page pe kya hai ----------

def test_locator_na_mile_to_error_me_ASLI_FIELD_dikhte_hain(bp_factory):
    """
    Pehle error sirf "nahi mila" kehta tha aur mujhe har baar alag se dump
    maangna padta tha. Ab error khud bata deta hai ki page pe kya hai --
    ek hi run me locator theek ho jata hai.
    """
    from framework.locator_store import store, LocatorNotFound
    bp = bp_factory("""
      <label>Ledger Name</label>
      <input type="text" id="txtlegername" formcontrolname="ledgerName">
      <label>GSTIN</label><input type="text" id="txtgstin">
    """)
    store.add("zz.nahi_hai", ["#kuch-bhi-nahi"])
    with pytest.raises(LocatorNotFound) as e:
        bp.find("zz.nahi_hai", probe_ms=300)
    msg = str(e.value)
    assert "txtlegername" in msg, "error me asli field nahi dikhe"
    assert "Ledger Name" in msg, "paas ka label bhi dikhna chahiye"
    assert "txtgstin" in msg
