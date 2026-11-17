"""
Page taiyaar hone ka intezaar -- asli browser me test.

MargBooks Angular hai aur dheere load hota hai. Pehle main URL badalte hi
scan kar leta tha aur aadhe field catalogue me jate hi nahi the.
"""
import pytest
from playwright.sync_api import sync_playwright


@pytest.fixture(scope="module")
def page():
    with sync_playwright() as pw:
        b = pw.chromium.launch(headless=True)
        pg = b.new_page(viewport={"width": 1280, "height": 720})
        yield pg
        b.close()


def test_dheere_bante_field_ka_intezaar_karta_hai(page):
    """Angular jaisa: field 900ms baad aate hain."""
    from framework.page_ready import wait_ready
    from framework import net_wait
    page.add_init_script(net_wait.TRACK_JS)
    page.set_content("""
      <div id="app"></div>
      <script>
        setTimeout(() => {
          document.getElementById('app').innerHTML =
            '<input id="a"><input id="b"><input id="c"><button>Save</button>';
        }, 900);
      </script>
    """)
    st = wait_ready(page, timeout_ms=8000)
    assert st["ready"], st
    assert page.locator("input").count() == 3, "field aane se pehle hi aage badh gaya"


def test_loader_dikh_raha_ho_to_rukta_hai(page):
    from framework.page_ready import wait_ready, spinner_visible
    page.set_content("""
      <div class="loader" id="sp" style="width:40px;height:40px">loading</div>
      <div id="app"></div>
      <script>
        setTimeout(() => {
          document.getElementById('sp').remove();
          document.getElementById('app').innerHTML = '<input id="x">';
        }, 800);
      </script>
    """)
    assert spinner_visible(page), "loader pehchana hi nahi gaya"
    st = wait_ready(page, timeout_ms=8000)
    assert st["ready"]
    assert not spinner_visible(page)


def test_DOM_badalta_rahe_to_taiyaar_nahi_maanta(page):
    """Jab tak field jud rahe hain, page taiyaar nahi hai."""
    from framework.page_ready import wait_ready
    page.set_content("""
      <div id="app"></div>
      <script>
        let n = 0;
        const t = setInterval(() => {
          document.getElementById('app').innerHTML += '<input>';
          if (++n >= 6) clearInterval(t);
        }, 200);
      </script>
    """)
    st = wait_ready(page, timeout_ms=9000, stable_ms=600)
    assert st["ready"]
    assert page.locator("input").count() == 6, \
        "beech me hi taiyaar maan liya -- adhoore field catalogue me jate"


def test_catalogue_dheere_bante_field_bhi_pakad_leta_hai(page, tmp_path):
    """
    Asli faayda: item-create jaisa page jo der se banta hai, uske SAARE
    field catalogue me jayein -- aadhe nahi.
    """
    import framework.catalogue as cat
    from framework import net_wait
    cat.FILE = tmp_path / "catalogue.json"
    page.add_init_script(net_wait.TRACK_JS)
    page.set_content("""
      <div id="app">loading…</div>
      <script>
        setTimeout(() => {
          document.getElementById('app').innerHTML = `
            <label>Item Name</label><input id="txtItemName">
            <label>M.R.P</label><input id="txtMRP">
            <label>HSN</label><input id="txtHSN">
            <button id="btnSave1">Save</button>`;
        }, 850);
      </script>
    """)
    res = cat.capture(page, "slow_form")
    assert res["found"] >= 4, f"sirf {res['found']} mile -- jaldi scan kar liya"
    hit = cat.resolve("slow_form", "Item Name", kind="type")
    assert hit and "txtItemName" in hit["css"]
