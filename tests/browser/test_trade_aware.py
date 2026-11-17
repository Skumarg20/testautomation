"""
Teen alag trade ke Sale Bill pe test -- yahi is tool ka asli imtihan hai.

Sale Bill har trade me alag hota hai:
    Pharma    -> Patient, Doctor, MR, Batch
    General   -> Customer Name
    Wholesale -> sirf Ledger

Main ek FIXED script likh raha tha (party -> patient -> doctor -> item), jo
sirf pharma pe aur wahi tab chalta jab saari settings on hon. General trade
pe wo hamesha fail hota. Isliye saare sale test red the.

Ab form pehle PADHA jata hai, phir sirf maujood field bhare jate hain.
Ye test teeno trade ka nakli form bana kar wahi jaanchta hai.
"""
import pytest
from playwright.sync_api import sync_playwright

HEAD = """
<style>.f{margin:6px}input,select{padding:4px}</style>
<div style="padding:12px">
  <span class="f">Party Name</span>
  <input class="f" id="txtLedgerName27" formcontrolname="ledgerName">
  <span class="f">Bill No.</span><input class="f" id="txtentryNo27" value="0000001">
  <span class="f">Date</span><input class="f" id="txtbillDate27" value="23-08-2026">
"""

PHARMA = HEAD + """
  <span class="f">Patient Mob.</span><input class="f" id="txtptmobile27">
  <span class="f">Patient Name</span><input class="f" formcontrolname="PatientName">
  <span class="f">Doctor Mob.</span><input class="f" formcontrolname="doctorMobileNo">
  <span class="f">Doctor Name</span><input class="f" formcontrolname="DoctorName">
  <span class="f">MR</span><input class="f" formcontrolname="mrName">
</div>
"""

GENERAL = HEAD + """
  <span class="f">Customer Name</span><input class="f" formcontrolname="customerName">
</div>
"""

WHOLESALE = HEAD + "</div>"

# ag-Grid ka dhaancha -- div, table nahi
def grid(cols, rows=2, extra_inputs=""):
    heads = "".join(
        f'<div role="columnheader" col-id="{c}">{c}</div>' for c in cols)
    body = ""
    for i in range(rows):
        cells = "".join(f'<div col-id="{c}"></div>' for c in cols)
        body += f'<div role="row" row-index="{i}">{cells}</div>'
    inputs = (f'<input id="txt-tmp_barcode-0"><input id="txt-itemLinkID-0">'
              f'<input id="txt-unitToEnteredValue-0">'
              f'<input id="txt-salePurchaseRate-0">'
              f'<input id="txt-discount1-0">{extra_inputs}')
    return f'<div>{heads}{body}</div>{inputs}'


@pytest.fixture(scope="module")
def make():
    with sync_playwright() as pw:
        b = pw.chromium.launch(headless=True)
        pg = b.new_page(viewport={"width": 1280, "height": 720})
        from framework.base_page import BasePage

        def build(html):
            pg.set_content(html)
            return BasePage(pg)
        yield build
        b.close()


# ---------- trade pehchan ----------

@pytest.mark.parametrize("html,expected", [
    (PHARMA, "pharma"), (GENERAL, "general"), (WHOLESALE, "wholesale"),
], ids=["pharma", "general", "wholesale"])
def test_trade_form_dekh_kar_pehchana_jata_hai(make, html, expected):
    from pages import form_profile
    bp = make(html + grid(["Product", "unitToEnteredValue"]))
    assert form_profile.read(bp).trade == expected


def test_pharma_me_patient_hai_general_me_nahi(make):
    from pages import form_profile
    ph = form_profile.read(make(PHARMA + grid(["Product"])))
    gn = form_profile.read(make(GENERAL + grid(["Product"])))
    assert ph.has("patient_name") and ph.has("mr")
    assert not gn.has("patient_name") and not gn.has("mr")
    assert gn.has("customer_name")
    assert ph.has("party") and gn.has("party")     # party dono me


def test_wholesale_me_sirf_ledger_hai(make):
    from pages import form_profile
    prof = form_profile.read(make(WHOLESALE + grid(["Product"])))
    assert prof.has("party")
    for f in ("patient_name", "doctor_name", "mr", "customer_name"):
        assert not prof.has(f), f"wholesale me {f} nahi hona chahiye"


# ---------- ag-Grid ----------

def test_ag_grid_rows_padhi_jati_hain(make):
    """Ye grid <table> nahi hai -- pehle main table dhoondh raha tha."""
    from pages import ag_grid
    bp = make(HEAD + "</div>" + grid(["Product", "batchName"], rows=3))
    assert len(ag_grid.rows(bp.page)) == 3
    assert ag_grid.line_count(bp.page) == 0        # sab khali


def test_bhari_hui_line_ginti_me_aati_hai(make):
    from pages import ag_grid
    bp = make(HEAD + "</div>" + """
      <div role="row" row-index="0">
        <div col-id="Product">Paracetamol</div><div col-id="batchName">A1</div></div>
      <div role="row" row-index="1">
        <div col-id="Product"></div><div col-id="batchName"></div></div>
    """)
    assert ag_grid.line_count(bp.page) == 1
    assert ag_grid.filled_rows(bp.page)[0]["cells"]["Product"] == "Paracetamol"


def test_grid_cell_ka_id_ROW_ke_hisaab_se_banta_hai():
    """Grid me -0/-1 row ka number hai, tab ka nahi."""
    from pages import ag_grid
    assert ag_grid.cell_id("qty", 0) == "#txt-unitToEnteredValue-0"
    assert ag_grid.cell_id("qty", 2) == "#txt-unitToEnteredValue-2"
    assert ag_grid.cell_id("barcode", 1) == "#txt-tmp_barcode-1"


def test_jo_column_nahi_hai_uspe_atakta_nahi(make):
    """
    Kuch trade me discount2 / volume discount hote hi nahi. Unhe bharne ki
    koshish me atakna nahi chahiye.
    """
    from pages import ag_grid
    bp = make(HEAD + "</div>" + grid(["Product"]))
    assert ag_grid.cell_exists(bp.page, "qty", 0)
    assert not ag_grid.cell_exists(bp.page, "vol_disc", 0)
    fields = ag_grid.available_fields(bp.page, 0)
    assert "qty" in fields and "vol_disc" not in fields


def test_batch_wale_trade_me_batch_column_dikhta_hai(make):
    from pages import form_profile
    ph = form_profile.read(make(PHARMA + grid(["Product", "batchName", "expiryDate"])))
    gn = form_profile.read(make(GENERAL + grid(["Product"])))
    assert ph.needs_batch
    assert not gn.needs_batch


# ---------- lookup ka asli flow ----------

def test_lookup_SPACE_dabata_hai_type_nahi(make):
    """
    Party field me seedha type karna galat tha. Asli tareeka:
    click -> Space -> #SearchBox popup -> naam -> option pe click.
    """
    bp = make("""
      <input id="txtLedgerName27" formcontrolname="ledgerName" placeholder="Press SpaceBar">
      <div id="pop" style="display:none">
        <input id="SearchBox">
        <div role="row"><div col-id="LedgerName">Cash Account</div></div>
        <div role="row"><div col-id="LedgerName">Aman Traders</div></div>
      </div>
      <script>
        document.querySelector('#txtLedgerName27').addEventListener('keydown', e => {
          if (e.key === ' ') document.getElementById('pop').style.display = 'block';
        });
        document.querySelectorAll('[col-id="LedgerName"]').forEach(d =>
          d.addEventListener('click', () => {
            document.querySelector('#txtLedgerName27').value = d.innerText;
            document.getElementById('pop').style.display = 'none';
          }));
      </script>
    """)
    from pages import lookup, form_profile
    el = form_profile.field_locator(bp, "party")
    chosen = lookup.pick(bp, el, "Aman", what="party")
    assert "Aman" in chosen
    assert bp.page.locator("#txtLedgerName27").input_value() == "Aman Traders"


def test_lookup_me_na_mile_to_saaf_batata_hai(make):
    from pages import lookup, form_profile
    bp = make("""
      <input id="txtLedgerName27" formcontrolname="ledgerName">
      <div id="pop"><input id="SearchBox">
        <div role="row"><div col-id="LedgerName">Cash Account</div></div></div>
      <script>
        document.querySelector('#txtLedgerName27').addEventListener('keydown', e => {});
      </script>
    """)
    el = form_profile.field_locator(bp, "party")
    with pytest.raises(lookup.LookupFailed):
        lookup.pick(bp, el, "Aisa Koi Party Nahi", what="party")
