"""
Design ke niyam -- jo dobara toot sakte hain.

Target: manual tester, jise coding nahi aati aur jo saadhi English padhta
hai. Har niyam yahan isliye hai ki wo ek baar toot chuka hai ya toot sakta
hai, aur aankh se dikhta nahi.
"""
import re
from pathlib import Path

import pytest

APP = Path(__file__).resolve().parent.parent.parent / "ui" / "app.html"
HTML = APP.read_text(encoding="utf-8")
STYLE = HTML[HTML.index("<style>"): HTML.index("</style>")]


def test_BADE_AKSHAR_ke_label_nahi_hain():
    """
    "ALL TESTS", "RUN A JOB" jaise label padhne me atkate hain aur jaankari
    kuch nahi dete -- heading khud bata deti hai. Ye AI-generated page ki
    sabse aam pehchan bhi hai.
    """
    assert "text-transform:uppercase" not in STYLE, \
        "kahin BADE AKSHAR ka niyam wapas aa gaya"


def test_monospace_sirf_MACHINE_ke_output_ke_liye_hai():
    """
    Monospace jaankari deta hai: "ye machine ka likha hua hai". Build
    number aur company ka naam padhne ki cheez hai, code nahi -- unpe
    monospace lagana sirf sajawat hai.
    """
    # Jahan monospace SAHI hai -- ye sab machine ka likha hua data hai:
    # console ka output, selector, id. Wahan monospace jaankari deta hai,
    # sajawat nahi.
    ok = ("tape", "log", "code", "mono", "pre", "sel", ".id", "console",
          "machine")
    bad = []
    for block in re.findall(r"([^{}]+)\{([^}]*font-family:var\(--mono\)[^}]*)\}",
                            STYLE):
        sel = block[0].strip().split("\n")[-1]
        if not any(w in sel.lower() for w in ok):
            bad.append(sel[:44])
    assert not bad, f"monospace yahan bekaar hai: {bad}"


def test_ek_hi_spacing_scale():
    """Alag-alag padding aankh ko chubhti hai, chahe pata na chale kyun."""
    pads = re.findall(r"padding:\s*(\d+)px", STYLE)
    odd = sorted({int(p) for p in pads if int(p) % 1 != 0})
    assert not odd, odd
    big = sorted({int(p) for p in pads if int(p) > 30})
    assert not big, f"itna bada padding kahin nahi chahiye: {big}"


def test_type_layman_ke_liye_kaafi_bada_hai():
    """13px chhota hai. Ye tool din bhar padha jayega."""
    m = re.search(r"body\{[^}]*font-size:(\d+(?:\.\d+)?)px", STYLE, re.S)
    assert m and float(m.group(1)) >= 14, "base font 14px se kam hai"


def test_har_class_ek_hi_baar_define_hai():
    """
    Ek baar ".grp" naam ki nayi class purani par chadh gayi thi aur rail ke
    saare naam BADE AKSHAR me ho gaye. CSS me naam ki takkar chupke se hoti
    hai -- na error, na kuch dikhta hai.
    """
    plain = re.findall(r"^\.([a-zA-Z][\w-]*)\s*\{", STYLE, re.M)
    dupes = {c for c in plain if plain.count(c) > 1}
    assert not dupes, f"do baar define: {sorted(dupes)}"


def test_keyboard_se_chalane_par_dikhta_hai_kahan_hain():
    """Jo mouse use nahi karte, unke liye focus ka nishaan zaroori hai."""
    assert ":focus-visible" in STYLE


def test_chhoti_screen_par_bhi_toot_ta_nahi():
    assert "@media" in STYLE, "chhoti screen ke liye koi niyam nahi"


def test_CSS_script_ke_andar_nahi_hai():
    """
    Ek baar CSS galti se <script> me chali gayi -- poora JS mar gaya aur
    tab khali dikha. Browser ne bas "Unexpected token ." kaha.
    """
    js = HTML[HTML.index("<script>") + 8: HTML.rindex("</script>")]
    bad = [l for l in js.split("\n")
           if l.startswith(".") and l.rstrip().endswith(("{", ";"))]
    assert not bad, f"CSS script me hai: {bad[:3]}"
