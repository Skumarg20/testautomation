"""
Code review ko test me badla gaya.

Niyam: har .click() guard se hokar jaye. Aaj maine haath se dhoondh ke theek
kiya tha -- ye test us mehnat ko pakka kar deta hai, taaki kal koi naya
unguarded click chupke se na aa jaye.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent   # tests/unit/ -> project root
# in files me raw click chalta hai kyunki yahi guard khud implement karti hain
EXEMPT = {"framework/safety.py", "framework/browser.py"}
# bp.click() andar se guarded_click use karta hai
OK_PATTERNS = (
    "guarded_click", "bp.click(", "self.p.click(", "self.click(",
    "def click", "# noqa: raw-click",
)


def _sources():
    for folder in ("framework", "pages", "agent"):
        for f in (ROOT / folder).glob("*.py"):
            rel = f"{folder}/{f.name}"
            if rel in EXEMPT:
                continue
            yield rel, f.read_text(encoding="utf-8")


def _code_lines(src: str):
    """
    Sirf ASLI CODE ki lines -- comment aur docstring chhod kar.

    Pehle ye test comment ko bhi code samajh leta tha. Ek comment jisme
    likha tha "pehle ye el.click() se hota tha" -- usi par test fail ho
    gaya, jabki wo line samjhane ke liye thi. Test ko code aur baat me
    farak karna aana chahiye, warna log comment likhna hi band kar denge.
    """
    import io
    import tokenize
    skip = set()
    try:
        for tok in tokenize.generate_tokens(io.StringIO(src).readline):
            if tok.type == tokenize.COMMENT:
                skip.add(tok.start[0])
            elif tok.type == tokenize.STRING and "\n" in tok.string:
                skip.update(range(tok.start[0], tok.end[0] + 1))
    except Exception:  # noqa: BLE001
        pass
    for i, line in enumerate(src.split("\n"), 1):
        if i not in skip:
            yield i, line


def test_koi_bhi_click_bina_guard_ke_nahi_hai():
    bad = []
    for rel, src in _sources():
        for i, line in _code_lines(src):
            if ".click(" not in line:
                continue
            if any(p in line for p in OK_PATTERNS):
                continue
            bad.append(f"{rel}:{i}  {line.strip()[:80]}")
    assert not bad, (
        "Ye clicks guard se nahi guzar rahe. safety.guarded_click() use karo:\n  "
        + "\n  ".join(bad))


def test_netguard_har_browser_launch_pe_lagta_hai():
    src = (ROOT / "framework" / "browser.py").read_text()
    assert "netguard.arm(ctx)" in src, "browser.launch me netguard nahi laga"
    assert "safety.arm_context(ctx)" in src, "browser.launch me click-guard nahi laga"


def test_koi_seedha_playwright_launch_nahi_kar_raha():
    """Sab framework.browser.launch se hi chalein -- warna guard chhoot jayega."""
    bad = []
    for rel, src in _sources():
        if rel == "framework/browser.py":
            continue
        # doctor sirf ye check karta hai ki Chromium install hai ya nahi --
        # uske liye guard ki zaroorat nahi.
        if rel == "framework/doctor.py":
            continue
        if "chromium.launch(" in src and "detect_screen" not in src:
            bad.append(rel)
    assert not bad, f"Ye files seedha browser launch kar rahi hain (guard chhoot jayega): {bad}"


def test_kisi_file_me_chhupe_hue_control_characters_nahi_hain():
    """
    Ek baar patch lagate waqt regex ka \\b Python ne BACKSPACE bana diya tha,
    aur guard ka regex chupchaap galat ho gaya -- code bilkul theek dikhta tha.
    Aise chhupe characters dobara na aayein.
    """
    bad = []
    for folder in ("framework", "pages", "agent", "config"):
        for f in (ROOT / folder).glob("*.py"):
            data = f.read_bytes()
            for ch, name in ((b"\x08", "BACKSPACE"), (b"\x0c", "FORMFEED"),
                             (b"\x0b", "VTAB"), (b"\x00", "NULL")):
                if ch in data:
                    bad.append(f"{folder}/{f.name}: {name}")
    assert not bad, f"chhupe control characters mile: {bad}"


def test_guard_js_valid_dikhta_hai():
    """Guard ka JS adhoora ya toota hua na ho."""
    from framework.safety import GUARD_JS
    assert GUARD_JS.count("{") == GUARD_JS.count("}"), "JS ke braces match nahi kar rahe"
    assert GUARD_JS.count("(") == GUARD_JS.count(")"), "JS ke brackets match nahi kar rahe"
    for must in ("answerNo", "disarm", "MutationObserver", "__mbQaGuard"):
        assert must in GUARD_JS, f"guard JS me '{must}' missing"


# ---------- .bat files ----------

def test_har_bat_setup_ki_jaanch_karta_hai():
    """
    Pehle bat files seedha .venv activate karti thin. Na mile to Windows
    chupchaap aage badh jata tha aur error kuch aur aata tha:
        ModuleNotFoundError: No module named 'dotenv'
    Usse ye pata hi nahi chalta ki asli baat "setup.bat nahi chalaya" hai.
    """
    bad = []
    for f in sorted(ROOT.glob("*.bat")):
        if f.name in ("setup.bat", "_start.bat"):
            continue
        src = f.read_text(encoding="utf-8", errors="ignore")
        if "_start.bat" not in src:
            bad.append(f"{f.name}: setup ki jaanch nahi karta")
        elif "errorlevel 1" not in src:
            bad.append(f"{f.name}: jaanch fail hone par ruk nahi raha")
    assert not bad, bad


def test_start_bat_saaf_message_deta_hai():
    src = (ROOT / "_start.bat").read_text(encoding="utf-8", errors="ignore")
    assert "setup.bat chalao" in src, "aadmi ko batata nahi ki karna kya hai"
    assert "import dotenv" in src, "libraries ki jaanch nahi karta"


def test_setup_bat_python_ki_jaanch_karta_hai():
    src = (ROOT / "setup.bat").read_text(encoding="utf-8", errors="ignore")
    assert "where python" in src, "Python hai ya nahi, ye nahi dekhta"
    assert "openpyxl" in src, "Excel import ke liye openpyxl chahiye"


def test_kisi_function_me_shadowed_import_nahi_hai():
    """
    doctor.py me main() ke beech me 'from config.settings import settings'
    tha, aur upar bare 'settings' use ho raha tha. Python ka niyam: naam
    kahin bhi assign ho to wo POORE function me local ban jata hai --
    isliye upar wala use UnboundLocalError de deta tha.

    Code padh kar ye pakadna mushkil hai (dikhta bilkul theek hai), isliye
    test se pakadte hain.
    """
    import ast
    bad = []
    for folder in ("framework", "pages", "ui", "config"):
        for f in (ROOT / folder).glob("*.py"):
            try:
                tree = ast.parse(f.read_text(encoding="utf-8"))
            except SyntaxError:
                continue
            for fn in ast.walk(tree):
                if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                # is function ke andar jo naam import hue
                imported = set()
                for n in ast.walk(fn):
                    if isinstance(n, (ast.Import, ast.ImportFrom)):
                        for a in n.names:
                            imported.add(a.asname or a.name.split(".")[0])
                if not imported:
                    continue
                # wahi naam import se PEHLE use hua?
                first_import_line = min(
                    n.lineno for n in ast.walk(fn)
                    if isinstance(n, (ast.Import, ast.ImportFrom)))
                for n in ast.walk(fn):
                    if (isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)
                            and n.id in imported and n.lineno < first_import_line):
                        bad.append(f"{folder}/{f.name}:{n.lineno} "
                                   f"'{n.id}' import se pehle use hua "
                                   f"(function {fn.name})")
    assert not bad, "UnboundLocalError aa sakta hai:\n  " + "\n  ".join(bad)


def test_doctor_sirf_maujood_files_ki_jaanch_karta_hai():
    """
    Doctor ne 'testcases/06_search.yaml (latest)' ko PROBLEM bataya, jabki
    wo file jaan-boojh kar _examples/ me daali gayi thi. Doctor ki list
    purani reh gayi thi.

    Aisa problem sabse bura hota hai: aadmi use theek karne baithta hai,
    jabki theek karne ko kuch hai hi nahi.
    """
    import inspect
    import re
    from framework import doctor
    src = inspect.getsource(doctor.main)
    block = src[src.index("-- Project files"):src.index("-- Config")]
    missing = [f for f in re.findall(r'"([\w/]+\.(?:py|yaml|json|html))"', block)
               if not (ROOT / f).exists()]
    assert not missing, f"doctor in files ki jaanch karta hai jo hain hi nahi: {missing}"


def test_har_bat_file_CRLF_me_hai():
    """
    Windows ka cmd LF-only file me multi-line `if (...)` block par toot
    jata hai -- aur error kuch batata nahi, bas window band ho jati hai.

    Chhe bat files LF-only reh gayi thin (jo heredoc se likhi thin), aur
    run-margbooks-crawler.bat chal hi nahi rahi thi. Ye galti dikhti nahi,
    isliye test se pakadte hain.
    """
    bad = []
    for f in sorted(ROOT.glob("*.bat")):
        raw = f.read_bytes()
        if b"\n" in raw and b"\r\n" not in raw:
            bad.append(f.name)
    assert not bad, f"ye bat files LF-only hain (Windows pe tootengi): {bad}"


def test_kisi_bat_me_IF_block_ke_ANDAR_goto_nahi_hai():
    """
    `goto` ko `if (...)` block ke andar rakhna batch me tootne ki jaani-mani
    wajah hai: goto block se bahar kood jata hai aur bacha hua `)` parser
    ko gira deta hai.
    """
    bad = []
    for f in sorted(ROOT.glob("*.bat")):
        depth = 0
        for i, line in enumerate(f.read_text(encoding="utf-8",
                                             errors="ignore").split("\n"), 1):
            low = line.strip().lower()
            if low.startswith("rem") or low.startswith("::"):
                continue
            if depth > 0 and low.startswith("goto"):
                bad.append(f"{f.name}:{i}")
            depth += line.count("(") - line.count(")")
            depth = max(depth, 0)
    assert not bad, f"IF block ke andar goto hai: {bad}"


def test_har_bat_python_ko_bulati_hai():
    """Koi bat aisi na ho jo kuch karti hi na ho."""
    skip = {"_start.bat"}
    for f in sorted(ROOT.glob("*.bat")):
        if f.name in skip:
            continue
        src = f.read_text(encoding="utf-8", errors="ignore").lower()
        assert "python" in src or "pytest" in src, f"{f.name} kuch chalati hi nahi"
