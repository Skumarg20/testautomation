"""
"Not found" pehchan ka test -- MargBooks jaisa HTML bana kar.

Asli message: "ZZQQ_NOPE_999 Not Found!" -- search bar ke neeche <p> me.
Pehle element-by-element scan tha jo kabhi chalta kabhi nahi.
"""
import pytest
from playwright.sync_api import sync_playwright

PAGE = """
<input id="searchItems" type="search" placeholder="Search here..">
<p>{msg}</p>
<table><tr><th>Description</th><th>Stock</th></tr>{rows}</table>
"""

CASES = [
    ("MargBooks ka asli message", "ZZQQ_NOPE_999 Not Found!", "", True),
    ("No Record Found", "No Record Found", "", True),
    ("no data available", "No Data Available", "", True),
    ("normal list, koi message nahi", "", "<tr><td>Paracetamol</td><td>3</td></tr>", False),
    ("khali list par message bhi nahi", "", "", False),
]


@pytest.mark.parametrize("name,msg,rows,expected", CASES,
                         ids=[c[0] for c in CASES])
def test_not_found_pehchana_jata_hai(name, msg, rows, expected):
    from pages.grid import has_not_found_alert
    with sync_playwright() as pw:
        b = pw.chromium.launch(headless=True)
        pg = b.new_page()
        pg.set_content(PAGE.format(msg=msg, rows=rows))
        found, _ = has_not_found_alert(pg)
        b.close()
    assert found is expected, f"{name}: found={found}, expected={expected}"


def test_safe_clear_delete_key_nahi_dabata():
    """
    Asli imtihan: input clear karo aur dekho ki koi Delete keydown fire hua
    ya nahi. Yahi wo bug tha jisse MargBooks me row delete ho jati thi.
    """
    from framework.safety import safe_clear
    with sync_playwright() as pw:
        b = pw.chromium.launch(headless=True)
        pg = b.new_page()
        pg.set_content("""
          <input id="x" value="kuch text">
          <script>
            window.keys = [];
            document.addEventListener('keydown', e => window.keys.push(e.key), true);
            document.addEventListener('keyup', e => window.keys.push('up:'+e.key), true);
          </script>
        """)
        el = pg.locator("#x")
        safe_clear(el, pg)
        keys = pg.evaluate("() => window.keys")
        value = el.input_value()
        b.close()

    assert value == "", "input clear nahi hua"
    assert "Delete" not in keys, f"DELETE key dabayi gayi! keys={keys}"
    assert "Backspace" not in keys, f"BACKSPACE dabayi gayi! keys={keys}"


def test_playwright_ka_fill_khali_DELETE_dabata_hai():
    """
    Ye test saabit karta hai ki bug asli tha -- aur isliye safe_clear zaroori hai.
    Agar kabhi Playwright ka vyavhaar badle to ye test bata dega.
    """
    with sync_playwright() as pw:
        b = pw.chromium.launch(headless=True)
        pg = b.new_page()
        pg.set_content("""
          <input id="x" value="kuch text">
          <script>
            window.keys = [];
            document.addEventListener('keydown', e => window.keys.push(e.key), true);
          </script>
        """)
        pg.locator("#x").fill("")
        keys = pg.evaluate("() => window.keys")
        b.close()
    # Playwright ka fill("") select-all + Delete karta hai
    assert "Delete" in keys or "Backspace" in keys, (
        f"Playwright ab Delete nahi dabata? keys={keys} -- safe_clear ki "
        f"zaroorat dobara jaanchni chahiye")
