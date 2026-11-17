"""
Control Room ka SAVE flow -- nakli panel bana kar.

Asli flow (user ne dekh kar bataya):
    1. Esc dabao    -> "save karein?" wala popup aata hai
    2. Save dabao   -> badlav lag jata hai
    3. Reload dabao -> app naye settings ke saath dobara load hota hai

Pehle main sirf "Save" dhoondhta tha. Wo screen par tha hi nahi -- popup
Esc ke BAAD aata hai. Isliye 205 settings badli to gayin par LAGI NAHI,
aur reload na hone se app aadhuri haalat me atak gaya: uske baad AATH
menu "nahi mila" bole aur browser band ho gaya.
"""
import pytest
from playwright.sync_api import sync_playwright

PANEL = """
<div id="nav">
  <a class="menulink" id="m1">Master</a><a class="menulink" id="m2">Sale</a>
  <a class="menulink" id="m3">Purchase</a><a class="menulink" id="m4">Report</a>
</div>
<div id="cr">
  <h2>Control Room</h2>
  <label for="s1">Ask Bill Discount</label>
  <select id="s1"><option>No</option><option>Yes</option></select>
</div>

<div id="askSave" style="display:none">
  <p>Do you want to save the changes?</p>
  <button id="btnSaveCR">Save</button><button id="btnDiscard">Discard</button>
</div>
<div id="askReload" style="display:none">
  <p>Settings changed. Reload to apply.</p>
  <button id="btnReload">Reload</button>
</div>
<div id="log">start</div>

<script>
  window.__state = {saved:false, reloaded:false};
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape') document.getElementById('askSave').style.display='block';
  });
  btnSaveCR.onclick = () => {
    window.__state.saved = true;
    askSave.style.display='none';
    askReload.style.display='block';
    // Reload se pehle menu GAYAB ho jate hain -- asli app me bhi yahi hota hai
    document.getElementById('nav').innerHTML = '';
    log.textContent = 'saved-menus-gone';
  };
  btnReload.onclick = () => {
    window.__state.reloaded = true;
    askReload.style.display='none';
    setTimeout(() => {
      document.getElementById('nav').innerHTML =
        '<a class="menulink" id="m1">Master</a><a class="menulink" id="m2">Sale</a>' +
        '<a class="menulink" id="m3">Purchase</a><a class="menulink" id="m4">Report</a>';
      log.textContent = 'reloaded';
    }, 400);
  };
</script>
"""


@pytest.fixture(scope="module")
def bp():
    with sync_playwright() as pw:
        b = pw.chromium.launch(headless=True)
        pg = b.new_page(viewport={"width": 1280, "height": 720})
        from framework.base_page import BasePage
        yield BasePage(pg)
        b.close()


@pytest.fixture
def panel(bp):
    bp.page.set_content(PANEL)
    return bp


def test_Esc_Save_Reload_teeno_kadam_hote_hain(panel):
    from framework import control_room as cr
    steps = cr._save_setting(panel, verbose=False)
    st = panel.page.evaluate("() => window.__state")
    assert steps["escape"], "Escape daba hi nahi"
    assert st["saved"], "Save nahi dabaya -- settings lagengi hi nahi"
    assert st["reloaded"], "Reload nahi dabaya -- app purane settings par rahega"


def test_reload_ke_baad_app_ke_WAPAS_aane_ka_intezaar_hota_hai(panel):
    """
    Reload ke beech me menu hote hi nahi. Us waqt crawl aage badha to har
    menu "nahi mila" kehta hai -- theek wahi hua tha, aath baar.
    """
    from framework import control_room as cr
    cr._save_setting(panel, verbose=False)
    assert cr.wait_app_back(panel, timeout_ms=8000), "app wapas nahi aaya"
    assert panel.page.locator("#nav a").count() == 4
    assert panel.page.locator("#log").inner_text() == "reloaded"


def test_app_wapas_na_aaye_to_saaf_pata_chalta_hai(bp):
    """Menu na hon to wait_app_back False de -- taaki crawl ruk sake."""
    from framework import control_room as cr
    bp.page.set_content("<div id='nav'></div><p>khali</p>")
    assert not cr.wait_app_back(bp, timeout_ms=2500)


def test_save_ka_button_popup_ke_ANDAR_se_dabta_hai():
    """
    Save popup ke andar hota hai. Bina inside_modal ke guard use band
    karne ki koshish karega aur click hi nahi hone dega -- wahi Purchase
    ke 'Start Manual Entry' ke saath ho chuka hai.
    """
    import inspect
    from framework import control_room as cr
    src = inspect.getsource(cr._save_setting)
    assert src.count("inside_modal=True") >= 2, \
        "Save/Reload popup ke andar se nahi dab rahe"


def test_crawler_app_wapas_na_aane_par_RUK_jata_hai():
    """
    Aage badhna bekaar hai: har page fail hoga aur wajah kahin aur
    dhoondhi jayegi. Jo settings badli hain wo backup me hain.
    """
    import inspect
    from framework.crawler import Crawler
    src = inspect.getsource(Crawler._enable_settings)
    assert "wait_app_back" in src and "raise RuntimeError" in src
    run = inspect.getsource(Crawler.run)
    assert "except RuntimeError" in run, "crash ho jayega, saaf ruka nahi"
