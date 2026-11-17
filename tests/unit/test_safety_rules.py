"""
Suraksha ke niyamon ke offline test -- browser ke bina chalte hain.

Ye asli QA hai: guard ke niyam khud test hone chahiye. Warna pata hi nahi
chalega ki kab koi badlaav suraksha me chhed kar gaya.
"""
import pytest

from framework import safety, netguard


# ---------- khatarnak element pehchan ----------

DANGEROUS = [
    {"tag": "button", "id": "Griddeletetbtn714", "cls": "mksBtn del", "text": ""},
    {"tag": "button", "id": "", "cls": "btn-trash", "text": ""},
    {"tag": "a", "id": "", "cls": "", "text": "Delete"},
    {"tag": "a", "id": "", "cls": "", "text": "Remove"},
    {"tag": "i", "id": "removeRow", "cls": "", "text": ""},
    {"tag": "button", "id": "", "cls": "destroy-btn", "text": ""},
]

SAFE = [
    {"tag": "input", "id": "searchItems", "cls": "form-control searchFilter", "text": ""},
    {"tag": "button", "id": "SIGNin", "cls": "blue-btn", "text": "SIGN IN"},
    {"tag": "button", "id": "btnSave27", "cls": "btn blue-btn", "text": "F10 / End Save"},
    {"tag": "a", "id": "menu112725066", "cls": "dropdown-toggle", "text": "Sale"},
    {"tag": "button", "id": "", "cls": "btn blue-btn", "text": "Create/F2"},
    {"tag": "button", "id": "", "cls": "btn default-btn", "text": "Esc Close"},
]


class FakeLoc:
    """assert_safe ko sirf .evaluate() chahiye -- browser nahi."""
    def __init__(self, d):
        self.d = dict(d)
        self.d.setdefault("title", "")
        self.d.setdefault("aria", "")
        self.d.setdefault("disarmed", False)

    def evaluate(self, _js):
        return self.d


@pytest.mark.parametrize("el", DANGEROUS, ids=[d["cls"] or d["id"] or d["text"] for d in DANGEROUS])
def test_khatarnak_element_block_hota_hai(el, monkeypatch):
    monkeypatch.setattr(safety.settings, "ALLOW_DESTRUCTIVE", False)
    with pytest.raises(safety.UnsafeClick):
        safety.assert_safe(FakeLoc(el), "test")


@pytest.mark.parametrize("el", SAFE, ids=[d["id"] or d["text"] for d in SAFE])
def test_surakshit_element_pass_hota_hai(el, monkeypatch):
    monkeypatch.setattr(safety.settings, "ALLOW_DESTRUCTIVE", False)
    safety.assert_safe(FakeLoc(el), "test")      # exception nahi aana chahiye


def test_allow_destructive_true_pe_guard_hat_jata_hai(monkeypatch):
    """Jaan-boojh kar off kiya ja sakta hai -- par tabhi jab user kahe."""
    monkeypatch.setattr(safety.settings, "ALLOW_DESTRUCTIVE", True)
    safety.assert_safe(FakeLoc(DANGEROUS[0]), "test")


def test_disarmed_element_bhi_block_hota_hai(monkeypatch):
    """Browser-side guard ne jise band kiya, Python bhi usse mana kare."""
    monkeypatch.setattr(safety.settings, "ALLOW_DESTRUCTIVE", False)
    el = {"tag": "button", "id": "x", "cls": "btn", "text": "OK", "disarmed": True}
    with pytest.raises(safety.UnsafeClick):
        safety.assert_safe(FakeLoc(el), "test")


# ---------- modal ka faisla ----------

class FakeReq:
    def __init__(self, method, url):
        self.method = method
        self.url = url


@pytest.mark.parametrize("method,url,blocked", [
    ("DELETE", "https://books5.margbooks.com/api/ledger/12", True),
    ("POST",   "https://books5.margbooks.com/api/ledger/delete", True),
    ("POST",   "https://books5.margbooks.com/api/item/removeRow", True),
    ("PUT",    "https://books5.margbooks.com/api/x/destroy", True),
    ("GET",    "https://books5.margbooks.com/api/ledger/delete", False),   # GET padhta hai
    ("POST",   "https://books5.margbooks.com/api/ledger/save", False),
    ("GET",    "https://books5.margbooks.com/item-master/list", False),
    ("POST",   "https://books5.margbooks.com/api/sale/create", False),
])
def test_netguard_kaunsi_request_rokta_hai(method, url, blocked):
    assert netguard._is_delete(FakeReq(method, url)) is blocked


# ---------- delete confirmation auto-answer ----------

def _guard_js():
    from framework.safety import GUARD_JS
    return GUARD_JS


def test_guard_js_delete_popup_pe_No_dabata_hai():
    js = _guard_js()
    assert "answerNo" in js, "delete confirmation ka auto-answer nahi hai"
    assert "__mbDeleteLog" in js, "delete popup ka record nahi rakha ja raha"
    # No/Cancel dabana chahiye, Yes nahi
    assert "no|cancel" in js.lower()


def test_guard_js_exit_popup_ko_haath_nahi_lagata():
    """
    'Transaction data will be loss, are you sure you want to close' wale popup
    pe Yes chahiye hota hai. Usse auto-No nahi dabana chahiye warna form kabhi
    band hi nahi hoga.
    """
    js = _guard_js()
    import re
    m = re.search(r"DEL_CONFIRM = /([^/]+)/", js)
    assert m, "DEL_CONFIRM regex nahi mila"
    pattern = re.compile(m.group(1).replace(r"\b", r"\b"), re.I)
    assert not pattern.search("Transaction data will be loss, "
                              "Are you sure you want to close?")
    assert pattern.search("Are you sure you want to delete the selected Record?")


def test_guarded_click_modal_pehle_hatata_hai():
    import inspect
    from framework import safety
    src = inspect.getsource(safety.guarded_click)
    assert "read_modal" in src, "click se pehle modal check nahi ho raha"


# ---------- Delete key wala asli bug ----------

def test_kahin_bhi_fill_khali_string_use_nahi_ho_raha():
    """
    ASLI KAARAN KA TEST.

    Playwright ka el.fill("") andar-andar select-all + DELETE key dabata hai.
    MargBooks ke list page pe Delete key = "selected row delete karo", chahe
    cursor search box me ho. Isi se har search par delete-confirmation popup
    aa raha tha.

    Isliye khali karne ke liye hamesha safety.safe_clear() -- jo JS se value
    khali karta hai, koi key nahi dabata.
    """
    import io, re, tokenize
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent.parent
    pattern = re.compile(r"""\.fill\(\s*["']{2}\s*\)""")
    bad = []
    for folder in ("framework", "pages", "agent"):
        for f in (root / folder).glob("*.py"):
            src = f.read_text(encoding="utf-8")
            # comment aur docstring hata do -- unme zikr hona theek hai
            code_lines = {}
            try:
                for tok in tokenize.generate_tokens(io.StringIO(src).readline):
                    if tok.type in (tokenize.COMMENT, tokenize.STRING):
                        continue
                    code_lines.setdefault(tok.start[0], "")
                    code_lines[tok.start[0]] += tok.string
            except Exception:                       # noqa: BLE001
                code_lines = dict(enumerate(src.split("\n"), 1))
            for i, line in code_lines.items():
                if pattern.search(line):
                    bad.append(f"{folder}/{f.name}:{i}  {line.strip()[:70]}")
    assert not bad, (
        'fill("") Delete key dabata hai -> MargBooks me row delete ka popup aata hai.\n'
        "safety.safe_clear(el, page) use karo:\n  " + "\n  ".join(bad))


def test_safe_clear_khatarnak_key_nahi_bhejta():
    """
    safe_clear KeyboardEvent bhej sakta hai (Angular ke keyup handler ke liye),
    par uski key harmless honi chahiye. Delete/Backspace bhejna wahi bug wapas
    le aayega jisse MargBooks me row delete ho jati thi.

    (Asli imtihan tests/browser/test_search_detection.py me hai -- wahan sach
    me browser me clear karke dekha jata hai ki koi Delete fire hui ya nahi.)
    """
    import re
    import inspect
    from framework.safety import safe_clear
    src = inspect.getsource(safe_clear)

    # KeyboardEvent me jo key di gayi hai, wo nikaalo
    keys = re.findall(r"""key:\s*['"]([^'"]+)['"]""", src)
    dangerous = {"Delete", "Backspace", "Del"}
    bad = [k for k in keys if k in dangerous]
    assert not bad, f"safe_clear khatarnak key bhej raha hai: {bad}"

    # aur Playwright ke apne key-press API se door raho
    assert ".press(" not in src, "safe_clear .press() use kar raha hai"
    assert "keyboard.press" not in src
    assert "dispatchEvent" in src, "Angular ke liye event bhejna zaroori hai"


# ---------- netguard ka allowlist ----------

@pytest.mark.parametrize("url,blocked", [
    # asli data mitane wali -> BLOCK
    ("https://gateway5.margbooks.com/v4.2/Ledger/Delete", True),
    ("https://gateway5.margbooks.com/v4.2/Item/Remove", True),
    # session ka apna temporary draft -> ALLOW (warna held-bill jama hote hain)
    ("https://gateway5.margbooks.com/v4.2/TempBillHold/Delete?isShowLoader=false", False),
    ("https://gateway5.margbooks.com/v4.2/TempHold/Delete", False),
])
def test_netguard_temp_cleanup_ko_jaane_deta_hai(url, blocked):
    class R:
        method = "POST"
    r = R()
    r.url = url
    assert netguard._is_delete(r) is blocked
