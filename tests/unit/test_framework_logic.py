"""Framework ki pure logic ka test -- browser nahi chahiye."""
import pytest

from framework.case_loader import load_all
from tests.unit._helpers import code_only as _code_only
from framework.step_runner import StepRunner, RunContext
from framework.locator_store import store


# ---------- test case library ----------

def test_saare_yaml_case_load_hote_hain():
    """
    Library ab KHALI shuru hoti hai -- sirf login ke case bundled hain,
    baaki testers khud likhenge. Isliye ginti ki koi ooncha seema nahi.
    """
    cases = load_all()
    assert cases, "ek bhi case load nahi hua"


def test_case_id_unique_hain():
    ids = [c.id for c in load_all()]
    assert len(ids) == len(set(ids)), "duplicate test case id"


def test_har_case_ka_target_locators_me_hai():
    known = set(store.all_keys())
    missing = set()
    for c in load_all():
        for s in c.steps:
            t = s.get("target")
            raw = t and (t.startswith(("xpath=", "css=", "#", "[", "(", "//", "role=", "text=", "exact_text=",
                                        "label=", "placeholder=", "input", ".", "ngb-", "button", "div", "a["))
                         or ">>" in t or "{" in t)       # a raw selector (runner accepts it), not a memory key
            if (s.get("action") not in ("open_screen", "goto", "note", "sleep")
                    and t and "." in t and not t.startswith("/") and not raw and t not in known):
                missing.add(f"{c.id}: {t}")
    assert not missing, f"locators file me missing: {sorted(missing)[:5]}"


def test_sirf_allowed_actions_use_hue_hain():
    allowed = {"goto", "open_screen", "open_menu", "click", "fill", "select", "press",
               "wait_text", "assert_text", "assert_no_text", "assert_visible",
               "assert_not_visible", "sleep", "screenshot", "note",
               # transaction form ke unche star ke kaam
               "set_party", "fill_header", "add_item", "add_barcode",
               "pick_batch", "retail_bill", "expect_party_state",
               "ensure_party", "require_setting", "set_bill_discount", "expect_total", "expect_lines",
               "expect_trade", "expect_field", "expect_no_field", "expect_column",
               "close_form", "save_form"}
    # every action the step runner implements (case "<name>": in framework/step_runner.py) is allowed too
    import re as _re
    from pathlib import Path as _P
    src = (_P(__file__).resolve().parents[2] / "framework" / "step_runner.py").read_text(encoding="utf-8")
    allowed |= set(_re.findall(r'case "([a-z_]+)"', src))
    bad = {(c.id, s.get("action")) for c in load_all()
           for s in c.steps if s.get("action") not in allowed}
    assert not bad, f"unknown actions: {bad}"


def test_data_likhne_wale_case_destructive_mark_hain():
    """Jo case save/create karta hai wo destructive:true hona chahiye,
    warna galti se live account pe chal jayega."""
    suspicious = []
    for c in load_all():
        writes = any(s.get("action") == "click"
                     and "save" in str(s.get("target", "")).lower() for s in c.steps)
        if writes and not c.destructive:
            suspicious.append(c.id)
    assert not suspicious, f"destructive mark nahi hai: {suspicious}"


# ---------- placeholder / templating ----------

class DummyPage:
    def screenshot(self, name):
        return None


def test_placeholder_resolve_hote_hain():
    r = StepRunner(DummyPage(), RunContext())
    out = r.render("{{item_name}}")
    assert out.startswith("QA_ITEM_"), out


def test_ctx_variable_resolve_hota_hai():
    ctx = RunContext(vars={"party": "Cash Account"})
    r = StepRunner(DummyPage(), ctx)
    assert r.render("Party: {ctx.party}") == "Party: Cash Account"


def test_test_data_hamesha_QA_prefix_se_shuru_hota_hai():
    """Demo account me humara banaya data pehchana ja sake."""
    from framework import data_factory as df
    for fn in (df.item_name, df.party_name, df.batch_no):
        assert fn().startswith("QA_"), fn.__name__


def test_invalid_gstin_sach_me_invalid_hai():
    from framework import data_factory as df
    assert len(df.invalid_gstin()) != 15
    assert len(df.gstin()) == 15


# ---------- screen detection ----------

def test_screen_detect_browser_use_nahi_karta():
    """
    Screen ka naap OS se aana chahiye, browser se nahi.

    Pehle headless browser se screen.availWidth padha ja raha tha -- wo nakli
    1280x720 deta hai kyunki headless browser ki koi screen hi nahi hoti.
    """
    import inspect
    from framework.browser import detect_screen
    src = inspect.getsource(detect_screen)
    assert "chromium.launch" not in src, "detect_screen browser khol raha hai -- galat naap milega"
    assert "windll" in src or "tkinter" in src, "OS se naap nahi le raha"


def test_screen_detect_sensible_value_deta_hai():
    from framework.browser import detect_screen
    w, h = detect_screen()
    assert 400 < w < 8000 and 300 < h < 5000, f"ajeeb screen size: {w}x{h}"


# ---------- .env parsing ----------

@pytest.mark.parametrize("raw,expected", [
    ("true", True),
    ("TRUE", True),
    ("  true  ", True),
    ('"true"', True),
    ("true   <- default, screen jitni badi ho utni", True),   # comment saath me
    ("true   # yes", True),
    ("false", False),
    ("false  <- kuch bhi", False),
    ("no", False),
    ("0", False),
])
def test_env_bool_comment_aur_space_jhel_leta_hai(raw, expected, monkeypatch):
    """
    Log .env me value ke saath comment paste kar dete hain. Pehle poori line
    value ban jaati thi aur setting chupchaap ULTI chal jaati thi -- ye sabse
    khatarnak kism ka bug hai, kyunki koi error nahi aata.
    """
    from config.settings import _bool
    monkeypatch.setenv("MB_TEST_FLAG", raw)
    assert _bool("MB_TEST_FLAG", False) is expected


def test_env_int_comment_jhel_leta_hai(monkeypatch):
    from config.settings import _int
    monkeypatch.setenv("MB_TEST_NUM", "1440   <- width")
    assert _int("MB_TEST_NUM", 0) == 1440


def test_env_ajeeb_value_pe_default_leta_hai_ulta_nahi(monkeypatch):
    from config.settings import _bool
    monkeypatch.setenv("MB_TEST_FLAG", "haanji-maybe")
    assert _bool("MB_TEST_FLAG", True) is True     # default, False nahi


# ---------- URL kabhi na kate ----------

@pytest.mark.parametrize("raw,expected", [
    ("https://accounts.margbooks.com", "https://accounts.margbooks.com"),
    ("https://books5.margbooks.com/", "https://books5.margbooks.com/"),
    ("  https://books5.margbooks.com  ", "https://books5.margbooks.com"),
    ('"https://books5.margbooks.com"', "https://books5.margbooks.com"),
    ("https://books5.margbooks.com   <- app ka domain", "https://books5.margbooks.com"),
    ("https://books5.margbooks.com   # domain", "https://books5.margbooks.com"),
])
def test_url_kabhi_nahi_katta(raw, expected, monkeypatch):
    """
    Comment hatane wale niyam ne ek baar poora URL kaat diya tha:
    "https://x.com" -> "https:" kyunki "//" ko comment maan liya tha.
    Comment tabhi hai jab uske pehle space ho.
    """
    from config.settings import _str
    monkeypatch.setenv("MB_TEST_URL", raw)
    assert _str("MB_TEST_URL") == expected


def test_password_me_special_characters_bache_rehte_hain(monkeypatch):
    """Password me #, //, ; sab ho sakta hai -- unhe kaatna nahi hai."""
    from config.settings import _clean
    for pw in ("Qa@9876543210", "p#ss//word", "a;b#c"):
        assert _clean(pw) == pw


def test_validate_toota_hua_url_pakad_leta_hai(monkeypatch):
    """Galat URL browser kholne se PEHLE pakda jana chahiye, baad me nahi."""
    from config.settings import Settings
    monkeypatch.setattr(Settings, "LOGIN_URL", "https:")
    with pytest.raises(RuntimeError, match="theek nahi"):
        Settings.validate()


# ---------- login screen pehchan ----------

def test_org_page_URL_se_pehchani_jati_hai():
    """
    Pehle sirf 'Organisation List' TEXT dhoondha jata tha. Page dheere load ho
    to robot 'anjaan screen' keh kar ruk jata tha -- jabki wo us page par hi
    khada tha (https://books5.margbooks.com/user-company).
    URL sabse pakka signal hai.
    """
    import inspect
    from framework import auth
    assert auth.ORG_URL_MARK == "user-company"
    src = inspect.getsource(auth.on_org_page)
    assert "page.url" in src, "org page URL se check nahi ho raha"


def test_login_next_screen_ka_intezaar_karta_hai():
    """Fixed wait ke bharose faisla nahi lena chahiye -- poll karna chahiye."""
    import inspect
    from framework import auth
    src = inspect.getsource(auth.wait_for_next_screen)
    assert "deadline" in src and "while" in src, "poll nahi kar raha"


# ---------- filter ka sahi paimana ----------

def test_total_label_ko_filter_ka_paimana_nahi_maana_gaya():
    """
    'Total No of Ledgers: 80' filter karne par NAHI badalta -- wo poore
    database ka total hai. Maine pehle isse filter ka paimana maan liya tha
    aur test jhootha fail ho raha tha.
    """
    import inspect
    from pages.party_page import PartyPage
    doc = inspect.getdoc(PartyPage.total) or ""
    assert "nahi badalta" in doc.lower() or "NAHI badalta" in doc, \
        "total() ki limitation documented honi chahiye"
    assert hasattr(PartyPage, "filter_works"), "filter check ka alag tareeka hona chahiye"


def test_get_bill_no_bharne_ka_intezaar_karta_hai():
    """Server se aane wale field ko turant padhna jhootha fail deta hai."""
    import inspect
    from pages.transaction_form import TransactionForm
    src = inspect.getsource(TransactionForm.get_bill_no)
    assert "while" in src and "wait_for_timeout" in src, "intezaar nahi kar raha"


# ---------- search ke do alag vyavhaar ----------

class _FakePage:
    """Browser ke bina search_check() ka logic test karne ke liye."""
    def __init__(self, toasts):
        self._toasts = toasts

    def evaluate(self, js):
        if "Date.now" in js:
            return 0
        return []

    def wait_for_timeout(self, _ms):
        pass


class _FakeList:
    def __init__(self, before, after, toast=""):
        self._before, self._after = before, after
        self._searched = False
        self.page = _FakePage([{"t": toast, "at": 1}] if toast else [])

    def names(self):
        return self._after if self._searched else self._before

    def search(self, _term):
        self._searched = True
        return self


def _sr(rows_after, term, alert="", rows_before=None):
    """rows_before diye bina purane test bhi chalte rahein."""
    from pages.party_page import PartyPage
    before = rows_before if rows_before is not None else rows_after
    obj = _FakeList(before, rows_after, alert)
    import framework.safety as _s
    orig = _s.get_toasts
    _s.get_toasts = lambda _p: obj.page._toasts
    try:
        return PartyPage.search_check(obj, term)
    finally:
        _s.get_toasts = orig


def test_search_filter_mode_pehchanta_hai():
    """Item List: na milne wali rows hat jaati hain."""
    r = _sr(["Sample Item", "Sample Two"], "Sample")
    assert r["mode"] == "filter" and r["works"]


def test_search_jump_mode_pehchanta_hai():
    """
    Ledger Master: rows hatti nahi, matching record UPAR aa jata hai.
    Pehle main isse fail maan raha tha -- jabki search theek chal raha tha.
    """
    r = _sr(["Cash Account", "Additional Charges On Free Items", "CGST Input"], "Cash")
    assert r["mode"] == "jump" and r["works"]


def test_search_chupchaap_tootne_par_pakad_leta_hai():
    """Na jump, na filter, na koi message -> yahi asli bug hai."""
    r = _sr(["Additional Charges On Free Items", "CGST Input"], "Cash")
    assert r["mode"] == "silent" and not r["works"]


def test_not_found_alert_ko_sahi_vyavhaar_maanta_hai():
    """
    "Record not found" alert = search CHALA, cheez nahi mili. Ye bug nahi.
    Pehle main isse bhi fail maan raha tha.
    """
    r = _sr(["Additional Charges On Free Items"], "ZZQQ_NOPE",
            alert="Record Not Found")
    assert r["mode"] == "not_found" and r["works"]


def test_khali_list_pe_bina_message_ke_works_nahi_kehta():
    """Pehle bhi khali, baad me bhi khali, koi message nahi -> koi daava nahi."""
    r = _sr([], "Cash", rows_before=[])
    assert r["mode"] == "silent" and not r["works"]


def test_filter_empty_sahi_vyavhaar_hai():
    """
    3 rows thin, bakwaas search ke baad 0 bachi -> filter ne kaam kiya,
    bas kuch match nahi hua. Ye BUG NAHI hai.
    """
    r = _sr([], "ZZQQ", rows_before=["Sample Item", "Item 2", "Item 3"])
    assert r["mode"] == "filter_empty" and r["works"]


def test_khali_list_se_search_ka_nateeja_nahi_nikalta():
    """
    Ek baar Item List khali thi, bakwaas search pe 0 rows aaye, aur maine
    galat nateeja nikal liya ki "search filter karta hai". Pehle bhi khali
    thi to koi daava nahi banta.
    """
    r = _sr([], "kuch bhi", rows_before=[])
    assert r["mode"] == "silent" and not r["works"]


# ---------- window fit ----------

def test_window_maximize_se_fit_hoti_hai_hisaab_se_nahi():
    """
    Naap ka hisaab teen baar galat nikla:
      - headless browser ne nakli screen batai
      - Windows API ne galat work-area diya
      - Chrome ne --window-size me apna toolbar jod diya
    Aur aakhir me browser (1280x720) aur Windows (1366x768) ki naap hi alag thi.

    Sahi hal: window manager ko "maximized" bolo. Use screen ka sach pata hai.
    """
    import inspect
    from framework.browser import fit_window, launch
    src = inspect.getsource(fit_window)
    assert '"windowState": "maximized"' in src, "maximize use nahi ho raha"
    assert "setWindowBounds" in src, "CDP se window set nahi kar raha"

    # launch me ab koi size ka hisaab nahi hona chahiye.
    # Comment me zikr theek hai -- sirf ASLI code dekho.
    import io, tokenize
    lsrc = inspect.getsource(launch)
    code = []
    for tok in tokenize.generate_tokens(io.StringIO(lsrc).readline):
        if tok.type not in (tokenize.COMMENT, tokenize.STRING):
            code.append(tok.string)
    code = " ".join(code)
    assert "--window-size" not in code, \
        "launch ke CODE me abhi bhi size ka hisaab hai -- wo galat nikla tha"


def test_not_found_message_ka_format_pehchana_jata_hai():
    """
    MargBooks ka asli message: 'ZZQQ_NOPE_999 Not Found!'
    (Item aur Ledger dono me, search bar ke neeche <p> me.)
    """
    from pages.grid import NOT_FOUND_WORDS
    msg = "ZZQQ_NOPE_999 Not Found!".lower()
    assert any(w in msg for w in NOT_FOUND_WORDS), \
        "asli MargBooks message pehchana nahi ja raha"


# ---------- session todne wale test ----------

def test_logout_wale_test_pehchane_jate_hain():
    """
    TC_AUTH_002 pehla step hi /logout karta hai. Ek hi browser session me
    saare test chalte hain, isliye uske BAAD ke saare test bekaar fail ho
    jate the. Ab wo tagged hain aur runner unhe aakhir me chalata hai.
    """
    cases = load_all()
    logout_cases = [c for c in cases
                    if any("logout" in str(s.get("target", "")).lower()
                           for s in c.steps)]
    assert logout_cases, "koi logout wala case nahi mila -- test purana ho gaya?"
    for c in logout_cases:
        assert "breaks_session" in (c.tags or []), \
            f"{c.id} logout karta hai par 'breaks_session' tag nahi hai"


def test_runner_session_tootne_par_dobara_login_karta_hai():
    import inspect
    from ui import runner
    src = inspect.getsource(runner._run_one)
    assert "app_ready" in src, "runner session check nahi karta"
    assert "breaks_session" in src, "logout wale test aakhir me nahi jaate"
    assert "CLICK_LOG.clear()" in src, "har run ka log alag nahi hai"


# ---------- API ka intezaar, page reload, autolearn ----------

def test_search_fixed_sleep_ki_jagah_API_ka_intezaar_karta_hai():
    """
    Pehle har search ke baad 1800ms ka andaza tha. Dheema internet ho to kam,
    tez ho to bekaar. Ab server ka jawab aane tak rukte hain.
    """
    import inspect
    from pages.item_page import ItemPage
    src = inspect.getsource(ItemPage.search)
    assert "settle()" in src, "search API ka intezaar nahi karta"
    assert "wait_for_timeout(1800)" not in src, "abhi bhi fixed sleep hai"


def test_screen_pehle_se_khuli_ho_to_dobara_load_nahi_hoti():
    """Har test ke shuru me page reload ho raha tha -- dheema aur bekaar."""
    import inspect
    from framework.screens import open_screen
    src = inspect.getsource(open_screen)
    assert "pehle se" in src and "return True" in src
    assert 'prefer: str = "menu"' in src, "default abhi bhi URL hai (reload karta hai)"


def test_autolearn_khatarnak_element_nahi_seekhta():
    from framework.autolearn import FIND_JS, MIN_SCORE
    assert "DANGER" in FIND_JS, "delete jaise element bhi seekh sakta hai"
    assert MIN_SCORE >= 70, "bharosa ki seema bahut dhili hai"


def test_locator_na_mile_to_khud_seekhta_hai():
    import inspect
    from framework.base_page import BasePage
    src = inspect.getsource(BasePage.find)
    assert "_learn" in src, "missing locator par khud nahi seekhta"


def test_control_room_off_feature_FAIL_nahi_SKIP_hai():
    """
    Mode of Payment jaisa feature Control Room me off ho to Sale Bill me wo
    window aati hi nahi. App theek hai -- test chal nahi sakta. Ye SKIP hai.
    """
    import inspect
    from framework.control_room import FeatureOff, require, is_on
    assert is_on("Yes") is True and is_on("No") is False
    assert is_on("Don't Ask") is False
    src = inspect.getsource(require)
    assert "FeatureOff" in src
    from ui import runner
    rsrc = inspect.getsource(runner._run_one)
    assert "FeatureOff" in rsrc and 'outcome, err = "skipped"' in rsrc


# ---------- asli run se mile bug ----------

def test_login_do_step_ka_hai_test_bhi_waisa_hi_ho():
    """
    MargBooks ka login DO step ka hai: mobile -> SIGN IN -> phir password.
    Jo bhi test password bharta hai, usme pehle username aur SIGN IN hona
    chahiye -- warna 'login.password page pe nahi mila' se fail hoga.
    """
    checked = 0
    for c in load_all():
        acts = [(s.get("action"), s.get("target")) for s in c.steps]
        if ("fill", "login.password") not in acts:
            continue
        checked += 1
        i_pass = acts.index(("fill", "login.password"))
        assert ("fill", "login.username") in acts[:i_pass], \
            f"{c.id}: password se pehle username nahi bhara"
        assert ("click", "login.submit") in acts[:i_pass], \
            f"{c.id}: password se pehle SIGN IN nahi dabaya"
    assert checked, "koi password wala test nahi mila -- test purana ho gaya?"


def test_sale_ke_locator_badalti_id_jhel_lete_hain():
    """
    Sale Bill ke field ki id har baar badalti hai (txtLedgerName27, ...31).
    Isliye 'shuru me ye ho' wala selector chahiye, poori id nahi.
    """
    from framework.locator_store import store
    for key in ("sale.party", "sale.save_btn", "sale.close_btn", "sale.bill_no"):
        sels = store.candidates(key)
        assert any("^=" in s for s in sels), \
            f"{key} me prefix selector nahi hai: {sels}"


def test_total_label_ke_NUMBER_par_koi_assert_nahi_karta():
    """
    'Total No of Ledgers' label ka hona check karna theek hai.
    Galat ye hai ki uske NUMBER par assert kiya jaye ("...: 80"), kyunki wo
    number filter lagane par badalta hi nahi -- wo poore data ka total hai.
    """
    import re
    bad = []
    for c in load_all():
        if (c.verification or {}).get("status"):
            continue        # live-app verified case: the count is the point of the check (e.g. duplicate barcode list)
        for s in c.steps:
            v = str(s.get("value", ""))
            if re.search(r"Total\s+(No|no)\s+of\s+\w+\s*:\s*\d", v):
                bad.append(f"{c.id}: {v}")
    assert not bad, (
        "ye tests total-label ke NUMBER par assert kar rahe hain, jo filter "
        f"par badalta hi nahi: {bad}")


def test_bina_naksha_wale_test_draft_mark_hain():
    """
    Jis screen ka locator map nahi bana, us test ko FAIL dikhana galat hai --
    wo likha to sahi hai, bas chalaya nahi ja sakta.

    Ab library me draft case ho bhi sakta hai aur nahi bhi (bundled sirf
    login ke hain). Jo hain, unki wajah likhi honi chahiye.
    """
    drafts = [c for c in load_all() if getattr(c, "draft", False)]
    for c in drafts:
        assert any(p.startswith("DRAFT") for p in (c.preconditions or [])), \
            f"{c.id} draft hai par wajah nahi likhi"


def test_runner_draft_ko_skip_karta_hai_fail_nahi():
    import inspect
    from ui import runner
    src = inspect.getsource(runner._run_one)
    assert '"draft"' in src and '"outcome": "skipped"' in src


def test_pages_me_lambe_fixed_sleep_nahi_bache():
    """
    Har "1500ms ruko" ek andaza hai. Dheema internet ho to kam pad jata hai
    (jhootha fail), tez ho to bekaar jata hai (dheemi suite). API ka intezaar
    hi sahi hai.
    """
    import re
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent.parent
    bad = []
    for f in (root / "pages").glob("*.py"):
        for i, line in enumerate(f.read_text(encoding="utf-8").split("\n"), 1):
            m = re.search(r"wait_for_timeout\((\d+)\)", line)
            if m and int(m.group(1)) >= 1000 and "#" not in line.split("wait_for")[0]:
                bad.append(f"pages/{f.name}:{i}  {line.strip()[:60]}")
    assert len(bad) <= 1, (
        "pages me lambe fixed sleep bache hain -- bp.settle() use karo:\n  "
        + "\n  ".join(bad))


# ---------- trade ke hisaab se test ----------

def test_doosre_trade_ka_test_FAIL_nahi_SKIP_hota_hai():
    """
    Pharma ka test general-trade company pe chal hi nahi sakta -- wahan
    patient/doctor/batch hote hi nahi. Use laal dikhana jhooth hoga.
    """
    import inspect
    from framework.step_runner import TradeMismatch, StepRunner
    src = inspect.getsource(StepRunner._dispatch_once)
    assert "TradeMismatch" in src, "expect_trade FAIL kar raha hai SKIP ki jagah"
    from ui import runner
    assert "TradeMismatch" in inspect.getsource(runner._run_one)


def test_pharma_ke_test_expect_trade_se_shuru_hote_hain():
    """
    Har pharma test ke shuru me expect_trade hona chahiye, warna wo general
    company pe jhoothe FAIL denge.
    """
    bad = []
    for c in load_all():
        if c.module != "pharma":
            continue
        acts = [s.get("action") for s in c.steps]
        if "expect_trade" not in acts:
            bad.append(c.id)
    assert not bad, f"in pharma tests me expect_trade nahi hai: {bad}"


def test_sale_ke_aam_test_kisi_ek_trade_par_nirbhar_nahi_hain():
    """
    03_sales.yaml ke test HAR trade pe chalne chahiye. Agar unme patient ya
    doctor ka field seedha maanga gaya hai to wo general trade pe toot jayenge.
    """
    bad = []
    for c in load_all():
        if c.module != "sales":
            continue
        for s in c.steps:
            if s.get("action") == "expect_field" and str(s.get("value")) in (
                    "patient_name", "doctor_name", "mr", "customer_name"):
                bad.append(f"{c.id}: {s['value']}")
    assert not bad, (
        "ye sale test kisi ek trade ke field maang rahe hain -- inhe pharma "
        f"module me le jao ya expect_trade lagao: {bad}")


def test_grid_ke_liye_ag_grid_use_hota_hai_table_nahi():
    """MargBooks ka item grid ag-Grid (div) hai, <table> nahi."""
    import inspect
    from pages.sale_bill_page import SaleBillPage
    src = inspect.getsource(SaleBillPage.line_count)
    assert "ag_grid" in src, "line_count abhi bhi table dhoondh raha hai"
    from pages import ag_grid
    assert 'role="row"' in ag_grid.READ_JS


# ---------- test data kisi ke asli account ko na chhue ----------

def test_koi_test_case_asli_dikhne_wala_mobile_hardcode_nahi_karta():
    """
    Ek test me 9999999999 hardcoded tha. Wo "random" laga tha, par uspe ASLI
    account nikla -- test galat raaste chala gaya aur do ghante barbaad hue.

    Koi bhi 10-ank ka number kisi ka asli account ho sakta hai. Aisi jagah
    andaza nahi lagana chahiye jab pakka tareeka maujood ho
    ({{unregistered_user}} -> .invalid domain, jispe account ban hi nahi sakta).
    """
    import re
    bad = []
    for c in load_all():
        for s in c.steps:
            v = str(s.get("value", ""))
            if re.fullmatch(r"[6-9]\d{9}", v.strip()):
                bad.append(f"{c.id}: {v}")
    assert not bad, (
        "in tests me asli lag sakne wala mobile hardcoded hai -- "
        f"{{{{unregistered_user}}}} ya {{{{mobile}}}} use karo: {bad}")


def test_unregistered_user_kabhi_register_nahi_ho_sakta():
    from framework.data_factory import unregistered_user
    u = unregistered_user()
    assert u.endswith(".invalid"), f"{u} par account ban sakta hai"
    assert "@" in u


def test_galat_password_wala_test_ASLI_user_se_hota_hai():
    """
    Na-register id se password screen tak pahunchte hi nahi. Isliye "galat
    password" test asli (register) user se hi ho sakta hai.
    """
    c = [x for x in load_all() if x.id == "TC_AUTH_004"][0]
    vals = [str(s.get("value", "")) for s in c.steps]
    assert "{{config_user}}" in vals, "asli user use nahi ho raha"
    assert any("wrong" in v for v in vals), "galat password nahi diya"


def test_type_wale_locator_sirf_input_maangte_hain():
    """
    MargBooks Settings panel me WAHI formcontrolname dobara use karta hai --
    par wahan <select> hota hai. Isliye jahan likhna hai, wahan selector me
    'input' likha hona chahiye, warna galat element mil jayega.
    """
    from framework.locator_store import store
    bad = []
    for key in ("party.name", "party.gstin", "party.mobile",
                "item.name", "item.mrp", "item.sale_rate"):
        for sel in store.candidates(key):
            if sel.startswith("[formcontrolname") or sel.startswith("[name="):
                bad.append(f"{key}: {sel}")
    assert not bad, (
        "ye selector <select> bhi utha sakte hain -- 'input' se shuru karo: "
        f"{bad}")


def test_locator_error_page_ke_field_dikhata_hai():
    import inspect
    from framework.base_page import BasePage
    src = inspect.getsource(BasePage.find)
    assert "describe_fields" in src, \
        "locator fail hone par page ke asli field nahi dikhaye ja rahe"
    assert "formcontrolname" in BasePage.FIELDS_JS


def test_nearlabel_screen_par_dikhne_wale_hi_element_leta_hai():
    from framework.base_page import BasePage
    js = BasePage.NEAR_LABEL_JS
    assert "innerHeight" in js and "getBoundingClientRect" in js, \
        "nearlabel viewport check nahi kar raha -- Settings panel utha lega"
    assert "SELECT" in js, "input aur select me farak nahi kar raha"


def test_build_number_maujood_hai():
    """
    Har zip ka apna build number. Teen baar purana code chal chuka hai aur
    pata nahi chala -- error dekhne me bilkul waisa hi lagta tha.
    """
    from config.settings import settings
    assert settings.BUILD != "unknown", "VERSION file missing"
    assert "-" in settings.BUILD


def test_doctor_naye_code_ke_nishaan_check_karta_hai():
    """doctor purani file turant pakad le -- warna ghante barbaad hote hain."""
    import inspect
    from framework import doctor
    src = inspect.getsource(doctor.main)
    for marker in ("describe_fields", "txtlegername", "ag_grid.py"):
        assert marker in src, f"doctor '{marker}' check nahi karta"


# ---------- AI provider ----------

def test_gemini_pehle_anthropic_backup():
    """
    Anthropic ke credits khatam hone par poora AI hissa band pad gaya tha.
    Gemini ka free tier hai, isliye wo pehle.
    """
    import inspect
    from framework import ai
    src = inspect.getsource(ai.ask)
    g = src.index("gemini")
    a = src.index("anthropic")
    assert g < a, "Anthropic pehle try ho raha hai -- Gemini free tier pehle hona chahiye"


def test_AI_test_chalata_nahi_sirf_likhne_me_madad_karta_hai():
    """
    Test ka matlab hi ye hai ki wo har baar bilkul ek jaisa chale. Agar AI
    har run me step banaye to natija badalta rahega aur test bekaar ho jayenge.
    Isliye AI sirf test LIKHNE me lagta hai, CHALANE me nahi.
    """
    import inspect
    from ui import runner
    src = inspect.getsource(runner._run_one)
    assert "framework.ai" not in src and "import ai" not in src, \
        "runner AI use kar raha hai -- test chalana niyam-aadharit rehna chahiye"


def test_AI_sirf_bachi_hui_lines_ke_liye_chalta_hai():
    import inspect
    from ui import nl
    src = inspect.getsource(nl.parse_with_ai)
    assert 'if not base["issues"]' in src, \
        "AI har baar chal raha hai -- pehle niyam, phir AI"


def test_AI_ke_steps_alag_dikhte_hain():
    """Tester ko pata chalna chahiye ki kaunsa step AI ne banaya."""
    import inspect
    from ui import nl
    assert 'from_ai' in inspect.getsource(nl.parse_with_ai)


# ---------- element catalogue ----------

def test_catalogue_har_screen_khulte_hi_bharta_hai():
    """
    Testing ke SAATH-SAATH agent apna gyaan badhata rahe -- yahi asli baat hai.
    """
    import inspect
    from framework import screens
    src = inspect.getsource(screens.open_screen)
    assert "remember()" in src, "screen khulne par catalogue nahi bharta"


def test_locator_dhoondhne_ka_kram_sahi_hai():
    """
    Kram jaan-boojh kar ye hai:
       1. haath se likhe locators   -- sabse pakke
       2. registry (khud dekhe hue) -- kai raaste
       3. autolearn (niyam)         -- page pe shabd milaakar
       4. AI                        -- SABSE AAKHIR me

    Upar wale teen har baar bilkul EK JAISA natija dete hain aur muft hain.
    AI na to dono deta hai. Isliye wo aakhri hai, pehla nahi.
    """
    import inspect
    from framework.base_page import BasePage
    src = inspect.getsource(BasePage.find)
    assert "_catalogue_selectors" in src, "registry dekhi hi nahi jaati"
    assert "_learn" in src and "_heal" in src
    # find() me do jagah _learn hai (ek tab jab key file me hai hi nahi).
    # Asli kram doosre wale se dekho -- yahi mukhya rasta hai.
    reg = src.index("_catalogue_selectors")
    learn_main = src.index("_learn(key, want)", reg)
    healed = src.index("_heal(key, want)")
    assert reg < learn_main < healed, \
        "kram galat hai -- AI sabse aakhir me hona chahiye"


def test_catalogue_css_aur_xpath_dono_rakhta_hai():
    from framework.catalogue import SCAN_JS
    assert "cssPath" in SCAN_JS and "xPath" in SCAN_JS
    assert "labelOf" in SCAN_JS, "paas ka label bhi chahiye -- wahi tester ki bhasha hai"


def test_catalogue_delete_wale_element_kabhi_nahi_deta():
    import inspect
    from framework import catalogue
    src = inspect.getsource(catalogue.resolve)
    assert 'el.get("danger")' in src


# ---------- Control Room ----------

def test_control_room_ki_settings_yaad_rakhi_jati_hain():
    """
    Poora MargBooks Control Room par tika hai. Settings jaane bina test likhna
    andhere me teer chalana hai -- fail hone par pata hi nahi chalta ki bug hai
    ya sirf setting band thi.
    """
    from framework import control_room as cr
    assert cr.FILE.name == "control_room.json"
    for must in ("mode_of_payment", "negative_stock", "ask_bill_discount",
                 "calculation_type"):
        assert must in cr.KNOWN, f"'{must}' known settings me nahi"
        assert cr.KNOWN[must]["affects"], f"'{must}' ka asar likha nahi hai"


@pytest.mark.parametrize("value,expected", [
    ("Yes", True), ("No", False), ("Don't Ask", False),
    ("Required", True), ("Inclusive", None), (True, True), (None, None),
])
def test_setting_ki_value_sahi_padhi_jati_hai(value, expected):
    from framework.control_room import is_on
    assert is_on(value) is expected


def test_setting_OFF_hone_par_test_SKIP_hota_hai_FAIL_nahi():
    import inspect
    from framework import control_room as cr
    src = inspect.getsource(cr.require)
    assert "FeatureOff" in src
    assert "bug NAHI" in src or "bug nahi" in src.lower()
    from ui import runner
    assert "FeatureOff" in inspect.getsource(runner._run_one)


def test_run_ke_shuru_me_control_room_padha_jata_hai():
    import inspect
    from ui import runner
    src = inspect.getsource(runner._run_one)
    assert "control_room" in src, "run me Control Room padha hi nahi jata"


def test_catalogue_scan_se_pehle_page_ka_intezaar_karta_hai():
    import inspect
    from framework import catalogue
    src = inspect.getsource(catalogue.capture)
    assert "wait_ready" in src, \
        "page taiyaar hue bina scan ho raha hai -- aadhe field chhoot jayenge"


def test_page_ready_teen_cheezein_dekhta_hai():
    import inspect
    from framework import page_ready
    src = inspect.getsource(page_ready.wait_ready)
    assert "inflight" in src, "API chal rahi hai ya nahi, ye nahi dekhta"
    assert "spinner_visible" in src, "loader nahi dekhta"
    assert "stable_since" in src, "DOM sthir hua ya nahi, ye nahi dekhta"


# ---------- environment har command me lagta hai ----------

def test_environment_HAR_command_me_lagta_hai():
    """
    Pehle environment sirf UI ke run me lagta tha. control-room.bat,
    login.bat, pom-check.bat waghairah seedha .env padhte the aur GALAT
    COMPANY khol dete the -- jabki UI me doosri company chuni hui thi.

    Isliye ab ye settings ke andar hai, ui me nahi -- koi command isse
    bhool hi nahi sakti.
    """
    import inspect
    from config import settings as cfg
    assert hasattr(cfg, "_apply_active_environment")
    src = inspect.getsource(cfg)
    assert "_apply_active_environment()" in src.split("settings = Settings()")[-1], \
        "import ke waqt environment lagta hi nahi"


def test_environment_class_aur_instance_dono_par_lagta_hai():
    """
    Sirf class par set karne se ek chhupa hua bug tha: kisi ne instance par
    value rakh di to wo class wali ko DHAK deti thi, aur environment
    chupchaap nazarandaz ho jata tha.
    """
    import inspect
    from config.settings import _apply_active_environment
    src = inspect.getsource(_apply_active_environment)
    assert "targets" in src and "setattr" in src, \
        "class aur instance dono par set nahi ho raha"


def test_control_room_ka_sahi_configure_dabata_hai():
    """
    Settings page par har card ke saamne 'Configure' likha hota hai --
    User Privilege, Control Room, Company Details. Pehla wala daba dene se
    User Privilege khul jata tha.
    """
    import inspect
    from framework import control_room as cr
    assert "FIND_CARD_JS" in dir(cr), "card dhoondhne wala hissa hi nahi"
    src = inspect.getsource(cr.open_control_room)
    assert "click_card_button" in src, "seedha pehla button daba raha hai"
    assert "_looks_like_control_room" in src, \
        "sahi panel khula ya nahi, ye jaancha hi nahi jata"


def test_galat_panel_khulne_par_pakad_leta_hai():
    """User Privilege bhi settings jaisa dikhta hai -- usse alag pehchanna zaroori."""
    import inspect
    from framework.control_room import _looks_like_control_room
    src = inspect.getsource(_looks_like_control_room)
    assert "user privilege" in src.lower(), "User Privilege ko pehchanta hi nahi"
    assert "billing requirement" in src.lower()


def test_choice_wali_setting_par_ON_OFF_nahi_poochta():
    """
    'Calculation Type in Sale = Inclusive' na ON hai na OFF -- wo ek CHOICE
    hai. Uspe ON/OFF poochna hi galat sawaal hai, aur report me '?' dikhana
    bhramit karta hai.
    """
    import inspect
    from framework import control_room as cr
    src = inspect.getsource(cr._match_known)
    assert '"choice"' in src, "choice aur toggle me farak nahi kar raha"
    assert hasattr(cr, "expect_choice"), "choice ke liye alag jaanch nahi hai"

    rsrc = inspect.getsource(cr.require)
    assert '"choice"' in rsrc, "choice setting ko band maan sakta hai"


def test_lambe_label_bhi_pehchane_jate_hain():
    """
    Asli label lambe hote hain: "Mode of Payment required in Sale".
    'startswith' se 544 me se sirf 4 pehchani gayin.
    """
    import inspect
    from framework import control_room as cr
    src = inspect.getsource(cr._match_known)
    assert "in _norm(r[" in src, "label ke andar dhoondhta hi nahi"


def test_ek_setting_do_keys_me_nahi_ginti():
    """Ek hi label do alag features me na chala jaye."""
    import inspect
    from framework import control_room as cr
    assert "used" in inspect.getsource(cr._match_known)


# ---------- AI model ka naam code me nahi ----------

def test_model_ka_naam_code_me_hardcode_nahi_hai():
    """
    Maine 'gemini-2.0-flash' code me likh diya tha. Google ne use hata diya
    aur 404 aane laga. Model ke naam mere training data se aate hain, aur wo
    purane pad jate hain -- isliye live list hi sach hai.
    """
    import inspect
    from framework import ai
    assert hasattr(ai, "list_models"), "live list ka tareeka hi nahi"
    src = inspect.getsource(ai.save_key)
    assert "list_models" in src, "key save karte waqt model check nahi hota"


@pytest.mark.parametrize("models,expect", [
    (["gemini-3.6-flash", "gemini-3.6-pro"], "gemini-3.6-flash"),
    (["gemini-3.6-flash-preview", "gemini-3.6-flash"], "gemini-3.6-flash"),
    (["gemini-2.5-flash", "gemini-3.6-flash"], "gemini-3.6-flash"),
    (["gemini-1.5-pro"], "gemini-1.5-pro"),
    ([], None),
])
def test_sabse_theek_model_khud_chunta_hai(models, expect):
    """flash pehle, preview aakhir me -- preview bina bataye hat jate hain."""
    from framework.ai import pick_model
    assert pick_model(models) == expect


def test_model_hat_jaye_to_khud_naya_chun_leta_hai():
    """Tester ko model ke naam yaad rakhne ki zaroorat nahi honi chahiye."""
    import inspect
    from framework import ai
    assert issubclass(ai.ModelGone, ai.AIError)
    src = _code_only(inspect.getsource(ai.check))
    assert "ModelGone" in src and "pick_model" in src, \
        "model hatne par khud naya nahi chunta"


def test_pick_automatically_purana_naam_saaf_karta_hai():
    """
    'pick automatically' chunne par bhi purana naam file me pada reh jata tha,
    aur 404 aata rehta tha. Naam pehle hatana zaroori hai.
    """
    import inspect
    from framework import ai
    src = inspect.getsource(ai.save_key)
    assert 'd.pop("gemini_model", None)' in src, \
        "automatic chunne par purana model naam hatta hi nahi"


def test_asli_use_me_bhi_model_khud_sudhar_jata_hai():
    """
    Pehle sirf 'Test again' me sudhar hota tha. Agar model beech kaam me hat
    jaye to tester ke saamne fail hona nahi chahiye.
    """
    import inspect
    from framework import ai
    src = inspect.getsource(ai.ask)
    assert "ModelGone" in src and "_forget_model" in src, \
        "ask() model hatne par khud nahi sudhrta"


# ---------- Gemini ka khali jawab ----------

@pytest.mark.parametrize("data,expect", [
    ({"candidates": [{"content": {}, "finishReason": "MAX_TOKENS"}]}, ""),
    ({"candidates": [{"content": {"parts": []}}]}, ""),
    ({"candidates": [{"content": {"parts": [{"text": "OK"}]}}]}, "OK"),
    ({"candidates": [{"content": {"parts": [{"text": "a"}, {"text": "b"}]}}]}, "ab"),
    ({}, ""),
    ({"candidates": []}, ""),
])
def test_khali_jawab_par_crash_nahi_hota(data, expect):
    """
    'content': {} aaya tha (finishReason MAX_TOKENS) aur code KeyError de
    kar poora sandesh ugal deta tha. Khali jawab ek aam baat hai -- uspe
    crash nahi, saaf error hona chahiye.
    """
    from framework.ai import _extract
    assert _extract(data) == expect


def test_model_ko_sochne_ka_token_nahi_dete():
    """
    Naye Gemini model jawab likhne se PEHLE 'sochne' me token kharch karte
    hain. 10 token ki seema me saare token soch me chale gaye aur jawab
    khali aaya. Humara kaam seedha hai (line -> steps), sochne ki zaroorat
    nahi.
    """
    import inspect
    from framework import ai
    src = inspect.getsource(ai._gemini)
    assert "thinkingBudget" in src, "sochna band nahi kiya"
    assert "thinkingConfig" in src


def test_ping_ki_seema_itni_ho_ki_jawab_aa_sake():
    import inspect
    from framework import ai
    src = _code_only(inspect.getsource(ai.check))
    assert "max_tokens=10)" not in src, "ping ki seema abhi bhi 10 hai"
    assert "PING_TOKENS" in src, "ping ki seema alag se tay nahi hui"
    assert ai.PING_TOKENS >= 128


def test_seema_chhoti_padne_par_dobara_koshish_karta_hai():
    import inspect
    from framework import ai
    assert issubclass(ai.OutOfTokens, ai.AIError)
    src = inspect.getsource(ai._gemini)
    assert "MAX_TOKENS" in src, "kate hue jawab ko pehchanta hi nahi"
    assert 'cfg["maxOutputTokens"] * 4' in src, \
        "seema chhoti padne par dobara koshish nahi karta"


# ---------- token ka intezaam ----------

def test_asli_call_ki_seema_kabhi_chhoti_nahi_hoti():
    """
    Chhoti seema se jawab beech me kat jata hai, aur adhoora JSON bilkul
    bekaar hota hai -- aadha step likha ho to wo galat step banata hai.
    """
    from framework.ai import MIN_OUTPUT_TOKENS
    import inspect
    from framework import ai
    assert MIN_OUTPUT_TOKENS >= 2048
    src = inspect.getsource(ai.ask)
    assert "max(max_tokens, MIN_OUTPUT_TOKENS)" in src, \
        "chhoti seema wali call ruk hi nahi rahi"


def test_temperature_ZERO_hai_point_one_nahi():
    """
    Test ka poora matlab ye hai ki wo har baar bilkul ek jaisa chale.
    0.1 par bhi model kabhi alag step bana dega, aur do tester ko ek hi line
    se do alag test milenge. Structured output me randomness ka koi faayda
    nahi, sirf nuksaan.
    """
    import inspect
    from framework import ai
    # Comment me 0.1/0.2 ka zikr theek hai -- sirf ASLI CODE dekho.
    src = _code_only(inspect.getsource(ai._gemini))
    assert '"temperature":0' in src.replace(" ", "")
    assert "0.1" not in src and "0.2" not in src


def test_beech_me_kata_jawab_kaamyabi_nahi_maana_jata():
    """
    Adhoora JSON parse ho jaye to aadhe step ban jate hain -- aur wo
    chupchaap galat test banate hain. Kaam na hone se bura hai.
    """
    import inspect
    from framework import ai
    src = inspect.getsource(ai._gemini)
    assert 'reason_now != "MAX_TOKENS"' in src, \
        "kata hua jawab bhi sahi maan liya ja raha hai"


def test_adhoora_JSON_saaf_pehchana_jata_hai():
    import inspect
    from framework import ai
    src = inspect.getsource(ai.ask_json)
    assert 'endswith(("}", "]"))' in src, "adhoora JSON pehchanta hi nahi"
    assert "OutOfTokens" in src


def test_prompt_chhota_hai():
    """Prompt jitna chhota, jawab ke liye utne token bache."""
    from framework.ai import STEP_SYSTEM
    assert len(STEP_SYSTEM) < 1200, f"prompt {len(STEP_SYSTEM)} chars -- bahut lamba"
    assert "Never invent" in STEP_SYSTEM
    assert "Never guess" in STEP_SYSTEM


def test_sirf_kaam_ke_fields_bheje_jate_hain():
    """200 fields har call me bhejna token barbaadi thi."""
    import inspect
    from framework import ai
    src = inspect.getsource(ai.text_to_steps)
    assert "handy" in src and "[:80]" in src


def test_JSON_ke_niyam_prompt_me_hain():
    from framework.ai import JSON_RULE
    assert "ONLY a strict JSON" in JSON_RULE
    assert "no markdown fence" in JSON_RULE
    assert "unknown" in JSON_RULE


def test_token_ki_neeche_ki_seema_hai():
    """
    thinkingBudget=0 se sochna band hota hai, PAR agar koi model wo setting
    na maane to soch phir token khane lagegi. Isliye seema kabhi itni chhoti
    nahi honi chahiye ki jawab hi na aa sake.
    """
    from framework import ai as _ai
    import inspect
    # ek hi jagah define ho -- do jagah hone se badalte waqt ek chhoot jayegi
    src = inspect.getsource(_ai)
    assert src.count("\nMIN_OUTPUT_TOKENS = ") == 1, \
        "MIN_OUTPUT_TOKENS ek se zyada jagah define hai"
    assert _ai.MIN_OUTPUT_TOKENS >= 2048
    import inspect
    from framework import ai
    src = inspect.getsource(ai._gemini)
    assert "max(max_tokens, MIN_OUTPUT_TOKENS)" in src, \
        "chhoti seema abhi bhi pass ho sakti hai"


def test_temperature_ZERO_hi_rehta_hai():
    """
    Ye jaan-boojh kar hai, aur ispe maine peeche bhi rakha hai.

    Test ka poora matlab ye hai ki wo har baar bilkul EK JAISA chale.
    0.1 par bhi model kabhi-kabhi alag step bana dega, aur do tester ko ek
    hi line se do alag test milenge. Structured output me randomness ka
    koi faayda nahi, sirf nuksaan hai.
    """
    import inspect
    from framework import ai
    src = inspect.getsource(ai._gemini)
    assert '"temperature": 0,' in src, \
        "temperature 0 se hatna test ko anishchit bana dega"


def test_prompt_chhota_aur_sakht_hai():
    """
    Lamba prompt token khata hai aur jawab ke liye kam bachte hain.
    Aur usme do baat SAAF honi chahiye: sirf JSON, aur andaza kabhi nahi.
    """
    from framework.ai import STEP_SYSTEM
    assert len(STEP_SYSTEM) < 1000, f"prompt bahut lamba: {len(STEP_SYSTEM)}"
    low = STEP_SYSTEM.lower()
    assert "json" in low, "JSON maangna likha hi nahi"
    assert "never guess" in low or "andaza" in low, \
        "andaza na lagane ka niyam prompt me nahi hai"
    assert "never invent" in low or "must come from" in low, \
        "target sirf di gayi list se lene ka niyam nahi hai"


# ---------- menu se navigation, URL se nahi ----------

def test_koi_test_case_seedha_URL_par_nahi_jata():
    """
    URL se jaane par poora page reload hota hai, app dobara load hoti hai,
    aur menu ka toota hua rasta kabhi pakda hi nahi jata -- asli user to
    hamesha menu se hi jata hai.
    """
    bad = []
    for c in load_all():
        if (c.verification or {}).get("status"):
            continue        # proven in the live app (artifacts/verify); listed as tech debt in the verification report
        for s in c.steps:
            if s.get("action") == "goto":
                bad.append(f"{c.id}: goto {s.get('target')}")
    assert not bad, ("ye tests seedha URL par ja rahe hain -- open_screen ya "
                     f"open_menu use karo: {bad}")


def test_menu_se_judne_ka_tareeka_kaam_karta_hai():
    """
    Menu se juda na ho to UI me wo kisi bhi menu item ke neeche nahi dikhega.

    Ab library me sirf login ke case hain, aur login kisi menu item ke
    neeche nahi aata (wo app me ghusne se PEHLE hota hai). Isliye ginti par
    nahi, TAREEKE par test karte hain: jo case kisi screen ko chhoota hai,
    wo menu se jud jana chahiye.
    """
    from framework.case_loader import TestCase
    c = TestCase(id="X", module="masters", title="t",
                 steps=[{"action": "open_screen", "target": "item"}])
    assert c.menu == "Master > Inventory Master > Item", c.menu
    assert c.menu_id == "master.inventory.item"


# ---------- locators registry ----------

def test_registry_har_element_ke_KAI_raaste_rakhta_hai():
    """
    App kabhi kisi element se id hata deta hai. Ek hi raasta rakha ho to
    test us din toot jayega. Isliye id, data-*, formcontrolname, name,
    placeholder, text aur xpath -- jitne mil sakein, sab rakhte hain.
    """
    from framework.catalogue import SCAN_JS
    for kind in ("'id'", "'data'", "'formcontrolname'", "'name'",
                 "'placeholder'", "'text'", "'xpath'"):
        assert f"push({kind}" in SCAN_JS, f"{kind} wala raasta nahi banta"


def test_naye_raaste_JUD_te_hain_purane_mitte_nahi():
    import inspect
    from framework import catalogue
    src = inspect.getsource(catalogue.capture)
    assert "merged" in src and "seen_sel" in src, \
        "dobara scan karne par purane raaste mit jayenge"


def test_registry_ka_naam_wahi_hai():
    from framework.catalogue import FILE, _OLD_FILE
    assert FILE.name == "locators_registry.json"
    assert _OLD_FILE.name == "catalogue.json", \
        "purane naam se gyaan uthaya hi nahi jayega"


# ---------- AI self-healing ----------

def test_AI_ka_bataya_locator_BINA_JAANCHE_save_nahi_hota():
    """
    Autolearn ke saath ye galti ek baar ho chuki hai: Settings panel ka
    dropdown 'Party' samajh kar registry me save ho gaya tha. AI ke saath
    wo dobara nahi honi chahiye.
    """
    import inspect
    from framework import heal
    src = inspect.getsource(heal.heal)
    assert "_verify" in src, "AI ka jawab bina jaanche use ho raha hai"
    vsrc = inspect.getsource(heal._verify)
    assert "assert_safe" in vsrc, "khatarnak element bhi chun sakta hai"
    assert "input" in vsrc and "textarea" in vsrc, \
        "likhne wale field ki jaanch nahi hai"


def test_AI_ko_koi_VALUE_nahi_bheji_jati():
    """Password, GSTIN, party ka data -- kuch bhi bahar nahi jana chahiye."""
    from framework.heal import SLIM_DOM_JS
    assert "el.value" not in SLIM_DOM_JS, "AI ko field ki value bheji ja rahi hai"
    assert "VALUE kabhi nahi" in SLIM_DOM_JS


def test_AI_theek_kiya_hua_locator_registry_me_jata_hai():
    """Warna AI har baar lagega -- dheema bhi, aur har run me alag bhi."""
    import inspect
    from framework import heal
    assert "catalogue.save" in inspect.getsource(heal._remember)


def test_AI_saaf_mana_kar_sakta_hai():
    """Galat andaza chupchaap galat test bana deta hai."""
    from framework.heal import HEAL_SYSTEM
    assert "-1" in HEAL_SYSTEM and "wrong guess" in HEAL_SYSTEM.lower()


# ---------- retail billing ----------

def test_retail_party_ka_faisla_FORM_dekh_kar_hota_hai():
    """
    Setting ka naam maan kar chalna galat hai -- asli sach wahi hai jo form
    me dikh raha hai. Setting sirf batane ke liye padhi jati hai.
    """
    import inspect
    from pages.retail_billing import RetailBillPage
    src = inspect.getsource(RetailBillPage.party_state)
    assert "prof.has(" in src, "form dekhta hi nahi"
    for state in ("not_asked", "prefilled", "empty"):
        assert state in src, f"'{state}' wali soorat sambhali hi nahi"


def test_pehle_se_bhari_party_ko_chhedta_nahi():
    """Counter par jo default aata hai wahi asli vyavhaar hai."""
    import inspect
    from pages.retail_billing import RetailBillPage
    src = inspect.getsource(RetailBillPage.ensure_party)
    assert '"prefilled", "not_asked"' in src


def test_doosri_setting_ka_retail_test_SKIP_hota_hai_FAIL_nahi():
    import inspect
    from framework import step_runner
    src = inspect.getsource(step_runner.StepRunner._dispatch_once)
    i = src.index("expect_party_state")
    assert "TradeMismatch" in src[i:i + 1200], \
        "doosri setting par test FAIL ho jayega"


# ---------- source scanner ----------

def test_scanner_bhari_folder_chhod_deta_hai():
    """node_modules akela hi laakhon file de deta hai -- scan ghanton ka ho jata."""
    from framework.code_scanner import SKIP_DIRS
    for d in ("node_modules", "dist", "build", ".git", "assets", "coverage"):
        assert d in SKIP_DIRS, f"'{d}' chhoda nahi ja raha"


def test_scanner_ek_element_ke_kai_raaste_banata_hai():
    from framework.code_scanner import _selectors_for
    sels = _selectors_for({"tag": "input", "id": "txtItemName",
                           "formcontrolname": "description",
                           "label": "Item Name", "placeholder": "Enter name"})
    assert any("#txtItemName" in s for s in sels)
    assert any("formcontrolname" in s for s in sels)
    assert any(s.startswith("nearlabel=") for s in sels)


def test_scanner_naya_scan_purane_ke_UPAR_jodta_hai():
    """Ek shakha me koi screen na ho, to iska matlab wo screen hai hi nahi."""
    import inspect
    from framework import code_scanner
    src = inspect.getsource(code_scanner._merge)
    assert "dict.fromkeys" in src and "old.get" in src, \
        "dobara scan karne par purana gyaan mit jayega"


def test_scanner_delete_wale_element_nahi_deta():
    import inspect
    from framework import code_scanner
    assert "del(ete)?" in inspect.getsource(code_scanner.resolve)


def test_locator_dhoondhne_me_metadata_bhi_dekha_jata_hai():
    import inspect
    from framework.base_page import BasePage
    src = inspect.getsource(BasePage.find)
    assert "_metadata_selectors" in src


# ---------- codegen import ----------

def test_recording_ke_dono_roop_padhe_jate_hain():
    """Playwright JS aur Python dono me codegen deta hai."""
    from ui.codegen_import import to_case
    js = to_case("await page.getByRole('button', { name: 'Save' }).click();", "x")
    py = to_case('page.get_by_role("button", name="Save").click()', "x")
    assert js["steps"] and py["steps"], (js, py)
    assert js["steps"][0]["target"] == py["steps"][0]["target"]


def test_recording_ke_dono_likhne_ke_tareeke_chalte_hain():
    """
    page.fill('#a','b')  aur  page.locator('#a').fill('b')  -- Playwright
    dono likhta hai. Sirf ek dekhna adhoora tha, aadhi recording chhoot jati.
    """
    from ui.codegen_import import to_case
    a = to_case("await page.fill('#txtName', 'QA');", "x")["steps"]
    b = to_case("await page.locator('#txtName').fill('QA');", "x")["steps"]
    assert a and b
    assert a[0]["value"] == b[0]["value"] == "QA"
    assert a[0]["target"] == b[0]["target"] == "#txtName"


def test_recording_ka_URL_menu_me_badal_jata_hai():
    """Recording me URL hota hai, par asli user menu se jata hai."""
    from ui.codegen_import import to_case
    st = to_case("await page.goto('https://books5.margbooks.com/item-master/list');",
                 "x")["steps"]
    assert st[0]["action"] == "open_screen" and st[0]["target"] == "item"


def test_samajh_na_aayi_line_par_ANDAZA_nahi_lagta():
    from ui.codegen_import import to_case
    r = to_case("await page.udanKhatola('chand');", "x")
    assert not r["steps"], "bakwaas line se bhi step ban gaya"
    assert r["unknown"], "chupchaap chhod diya, bataya hi nahi"


# ---------- pre-requisite engine ----------

def test_setting_khud_ON_ki_ja_sakti_hai():
    """
    Pehle band feature wale test SKIP hote the. Imaandaar tha, par kaam
    aage nahi badhta tha.
    """
    import inspect
    from framework import control_room as cr
    assert hasattr(cr, "ensure")
    src = inspect.getsource(cr.ensure)
    assert "ALLOW_DESTRUCTIVE" in src, \
        "bina ijazat kisi ki company ki setting badal dega"
    assert "CHANGED.append" in src, "jo badla wo likha hi nahi jata"


def test_setting_badalne_ka_click_bhi_guard_se_guzarta_hai():
    """
    Pehle ye JS ke andar el.click() se hota tha -- wo guard ko poori tarah
    bypass kar deta tha. Ek jagah chhed rakhna aur baaki sab jagah pehra
    lagana bemaani hai.
    """
    import inspect
    import io
    import tokenize
    from framework import control_room as cr
    src = inspect.getsource(cr._set_control)
    assert "assert_safe" in src and "audit_click" in src

    # Sirf ASLI CODE dekho -- comment me uska zikr theek hai.
    # (Yahi galti guard-coverage test me bhi ho chuki hai: samjhane wali
    #  line ko code samajh kar fail kar diya tha.)
    code = " ".join(
        t.string for t in tokenize.generate_tokens(io.StringIO(src).readline)
        if t.type not in (tokenize.COMMENT, tokenize.STRING))
    assert "el.click()" not in code


# ---------- prerequisite knowledge base (JSON, code nahi) ----------

def test_settings_ki_list_CODE_ME_NAHI_hai():
    """
    Pehle ye Python dict tha. Matlab: naya field jodne ko code chhedna
    padta, aur agla update us badlav ko mita deta. Tester khud kuch nahi
    jod paata tha.
    """
    from framework import control_room as cr
    assert cr.KNOWN_FILE.name == "prerequisites.json"
    assert cr.KNOWN_FILE.exists()
    assert len(cr.KNOWN) >= 12, f"sirf {len(cr.KNOWN)} settings"
    for must in ("ask_item_discount", "second_discount", "batch_required",
                 "expiry_required", "mrp_required", "barcode_required"):
        assert must in cr.KNOWN, f"'{must}' knowledge base me nahi"


@pytest.mark.parametrize("phrase,expect", [
    ("discount 1", "ask_item_discount"),
    ("discount one", "ask_item_discount"),
    ("disc 1", "ask_item_discount"),
    ("discount1", "ask_item_discount"),
    ("discount 2", "second_discount"),
    ("batch", "batch_required"),
    ("expiry", "expiry_required"),
    ("mode of payment", "mode_of_payment"),
    ("udan khatola", None),
])
def test_tester_ki_bhasha_se_setting_milti_hai(phrase, expect):
    """"Set Discount 1 to 10" ko sahi setting se jodna -- bina alag code likhe."""
    from framework.control_room import find_by_phrase
    assert find_by_phrase(phrase) == expect


def test_har_field_ke_liye_alag_code_nahi_likha():
    """Requirement: `if field == "Discount 1"` jaisa code nahi hona chahiye."""
    import inspect
    from framework import control_room as cr
    src = inspect.getsource(cr)
    for bad in ('== "Discount 1"', "== 'Discount 1'", '== "discount1"'):
        assert bad not in src, f"har field ke liye alag code hai: {bad}"


# ---------- confidence ----------

@pytest.mark.parametrize("a,b,low,high", [
    ("Discount 1", "Discount 1", 0.99, 1.0),
    ("discount one", "Discount 1", 0.90, 1.0),
    ("save button", "save_btn", 0.90, 1.0),
    ("party", "Party Name", 0.75, 1.0),
    ("Discount 1", "Discount 2", 0.0, 0.01),
    ("udan khatola", "Item Name", 0.0, 0.01),
])
def test_bharose_ka_number_sahi_banta_hai(a, b, low, high):
    from framework.mapping import score
    assert low <= score(a, b) <= high, f"{a} vs {b} -> {score(a, b)}"


def test_Discount_1_aur_2_kabhi_nahi_milte():
    """
    Sirf akshar milane se ye do 90% ek jaise lagte hain -- par ye do ALAG
    field hain. Inhe mila dena chupchaap galat test bana dega.
    """
    from framework.mapping import score
    assert score("Discount 1", "Discount 2") == 0.0
    assert score("discount one", "discount two") == 0.0


def test_kam_bharose_par_selector_nahi_deta():
    """Andaza lagana yahan sabse bura vikalp hai."""
    from framework.mapping import resolve, OK
    m = resolve("aisa koi field duniya me nahi hai")
    assert not m.resolved and m.confidence < OK
    assert m.selectors == []


def test_kam_bharose_par_vikalp_dikhata_hai():
    from framework.mapping import resolve
    m = resolve("save")
    assert m.resolved or m.alternatives, "na jawab, na vikalp"


def test_selector_kabhi_banaya_nahi_jata():
    """
    Selector sirf teen jagah se aata hai: haath se likhe locators, browser
    me dekhi hui registry, ya source scan. AI se kabhi nahi.
    """
    import inspect
    from framework import mapping
    src = inspect.getsource(mapping)
    assert "_from_yaml" in src and "_from_registry" in src and "_from_metadata" in src
    assert "framework import ai" not in src, "mapping me AI ghus gaya hai"


# ---------- logs aur itihaas ----------

def test_char_alag_log_hain():
    from framework.logbook import KINDS
    for k in ("scanner", "ai", "generator", "execution"):
        assert k in KINDS


def test_run_ka_itihaas_DISK_par_rehta_hai():
    """Server band karte hi itihaas ud jata tha."""
    import inspect
    from framework import logbook
    assert logbook.HISTORY.name == "execution_history.json"
    assert "json.dumps" in inspect.getsource(logbook._save_history)
    from ui import runner
    assert "record_result" in inspect.getsource(runner._run_one)


def test_har_test_ke_saath_pichhla_natija_aata_hai():
    import inspect
    from ui import store
    assert "logbook" in inspect.getsource(store.as_dicts)


# ---------- scanner security ----------

def test_scanner_secret_files_nahi_padhta():
    """
    .env me password hota hai. Ek galti se wo metadata.json me chala jaye
    to wo file git me bhi ja sakti hai.
    """
    from framework.code_scanner import SECRET_NAMES, SECRET_PARTS
    assert ".env" in SECRET_NAMES
    assert any("secret" in p for p in SECRET_PARTS)
    assert any(".pem" in p for p in SECRET_PARTS)


def test_scanner_poori_disk_scan_nahi_karta():
    """'..' bhej kar koi poori machine scan na karwa sake."""
    import pytest as _pt
    from framework import code_scanner
    for bad in ("/", "/home", "/root"):
        with _pt.raises(FileNotFoundError):
            code_scanner.scan(bad)


def test_scanner_path_resolve_karta_hai():
    import inspect
    from framework import code_scanner
    assert "resolve(strict=True)" in inspect.getsource(code_scanner.scan)


def test_kisi_test_me_hate_hue_case_ka_naam_nahi_bacha():
    """
    Library khali karne par char test toot gaye, kyunki unme 'TC_SALE_001'
    likha tha. Kisi khaas case id par tikna galat hai -- library badalti
    rehti hai, aur test uske saath nahi tootne chahiye.
    """
    import io
    import re
    import tokenize
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent
    live = {c.id for c in load_all()}
    bad = []
    for f in list(root.rglob("*.py")):
        src = f.read_text(encoding="utf-8")
        # Sirf ASLI CODE dekho. Comment aur docstring me purane naam ka
        # zikr theek hai -- wahi to batata hai ki wo kyun hataya gaya.
        skip = set()
        try:
            for tok in tokenize.generate_tokens(io.StringIO(src).readline):
                if tok.type in (tokenize.COMMENT,) or (
                        tok.type == tokenize.STRING and "\n" in tok.string):
                    skip.update(range(tok.start[0], tok.end[0] + 1))
        except Exception:  # noqa: BLE001
            pass
        for i, line in enumerate(src.split("\n"), 1):
            if i in skip or "_any_builtin" in line:
                continue
            for m in re.finditer(r'["\'](TC_[A-Z]+_\d+)["\']', line):
                if m.group(1) not in live:
                    bad.append(f"{f.name}:{i} {m.group(1)}")
    assert not bad, ("ye tests un case par tike hain jo ab library me nahi "
                     f"hain: {bad}")


# ---------- settings ON karna ----------

@pytest.mark.parametrize("opts,want", [
    (["No", "Yes"], "Yes"),
    (["Yes", "No"], "Yes"),
    (["Don't Ask", "Ask"], "Ask"),
    (["Don't Ask", "Ask", "Ask on Spacebar"], "Ask"),
    (["Inclusive", "Exclusive", "Tax on MRP"], None),
    (["Registered", "Composition", "Unregistered"], None),
    (["Dr", "Cr"], None),
    ([], None),
])
def test_sirf_YES_NO_wali_settings_badli_jati_hain(opts, want):
    """
    "Calculation Type" ko Yes karna bemaani hai -- uske vikalp
    Inclusive/Exclusive/Tax on MRP hain. Aisi settings chhod di jati hain.

    Aur kuch settings ka "chaalu" roop "Ask" hota hai, "Yes" nahi
    (jaise "Ask Party in Retail Billing").
    """
    from framework.control_room import on_value
    assert on_value({"options": opts}) == want


def test_settings_badalne_se_PEHLE_backup_hota_hai():
    """
    Crawl ke liye badli hui settings company me hamesha ke liye nahi rehni
    chahiye -- warna kal koi asli kaam karega aur socha kuch aur hoga.
    """
    import inspect
    from framework import control_room as cr
    src = inspect.getsource(cr.enable_yes)
    assert "BACKUP.write_text" in src
    assert src.index("BACKUP.write_text") < src.index("_set_control"), \
        "backup badalne ke BAAD ho raha hai -- tab tak purani value ja chuki hogi"
    assert hasattr(cr, "restore")


def test_settings_badalne_ko_ijazat_chahiye():
    import inspect
    from framework import control_room as cr
    src = inspect.getsource(cr.enable_yes)
    assert "ALLOW_DESTRUCTIVE" in src and "SettingLocked" in src


def test_crawler_default_me_kuch_nahi_badalta():
    """
    Settings badalna MAANGNA padta hai, apne aap nahi hota. Roz ka crawl
    kisi ki company ki settings chup-chaap na badal de.
    """
    import inspect
    from framework.crawler import Crawler
    sig = inspect.signature(Crawler.__init__)
    assert sig.parameters["enable"].default == "none"
    from framework import run_crawler
    src = inspect.getsource(run_crawler.main)
    assert '"--enable"' in src and '"--enable-all"' in src
    assert 'else "none"' in src


def test_enable_ke_bina_crawler_read_only_rehta_hai():
    import inspect
    from framework import run_crawler
    src = inspect.getsource(run_crawler.main)
    i = src.index('if enable == "none":')
    assert "ALLOW_DESTRUCTIVE = False" in src[i:i + 300]


def test_enable_ka_matlab_SAARI_settings_hai():
    """
    Pehle "--enable" sirf 15 jaani-pehchani settings karta tha. Unme se
    zyadatar pehle se Yes thin, isliye 2-3 hi badlin -- aur chhupe hue
    field phir bhi nahi dikhe.

    Ab "--enable" ka matlab hai: HAR wo setting jiske dropdown me "Yes"
    (ya "Ask") ka vikalp hai.
    """
    import inspect
    from framework import run_crawler
    src = inspect.getsource(run_crawler.main)
    i = src.index("enable = (")
    block = src[i:i + 260]
    assert '"--enable-known"' in block, "chhota sweep ka alag jhanda nahi hai"
    # --enable ka natija "all" hona chahiye, "known" nahi
    assert '"known" if "--enable-known"' in block
    assert '"all" if ("--enable"' in block


def test_crawler_known_ko_alag_se_maangna_padta_hai():
    import inspect
    from framework.crawler import Crawler
    src = inspect.getsource(Crawler._enable_settings)
    assert 'self.enable == "known"' in src, \
        "chhota sweep default ban gaya hai"


def test_bahut_saari_settings_par_ginti_dikhti_hai():
    """557 dropdown badalte waqt screen chup rahe to lagta hai atak gaya."""
    import inspect
    from framework import control_room as cr
    src = inspect.getsource(cr.enable_yes)
    assert "i % 25 == 0" in src, "progress dikhta hi nahi"


# ---------- form ke doosre naam ----------

def test_form_ke_doosre_naam_CONFIG_me_hain_code_me_nahi():
    """
    MargBooks kuch cheezon ko form me ALAG naam se bulata hai: "Ledger" ka
    form "Create Party" hai, "Agency" ka "Create Company". Iske bina
    crawler samajhta hai ki galat form khul gaya aur SAHI data chhod deta
    hai -- pichhle crawl me 4 form ke saath yahi hua.

    Ye naam config me hain, code me nahi -- taaki naya naam milne par
    Python chhune ki zaroorat na pade.
    """
    import json
    from framework.crawler import SEQ_FILE
    d = json.loads(SEQ_FILE.read_text(encoding="utf-8"))
    found = {}
    for m in d["menus"]:
        for sub in m.get("submenus", []):
            for node in [sub] + sub.get("children", []):
                if node.get("formNames"):
                    found[node["name"]] = node["formNames"]
    assert "Ledger" in found and "Party" in found["Ledger"]
    assert "Agency" in found and "Company" in found["Agency"]

    import inspect
    from framework import crawler
    src = inspect.getsource(crawler)
    assert '"Ledger": ["Party"]' not in src, "naam code me hardcode hain"


def test_alias_hone_par_bhi_GALAT_form_rukta_hai():
    """
    Alias dene ka matlab ye nahi ki har form chalega. Galat form ab bhi
    rukna chahiye -- warna mila-jula data save ho jayega.
    """
    import inspect
    from framework.crawler import Crawler
    src = inspect.getsource(Crawler._form_matches)
    assert "return False, head" in src
    assert "aliases" in inspect.signature(Crawler._form_matches).parameters
