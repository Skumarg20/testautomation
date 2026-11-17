"""
Search karne par screen pe ASLI ME kya hota hai -- ye dekhta hai, badalta kuch nahi.

Do baar maine galat andaza lagaya:
  - socha "not found" toast hota hai; asal me wo search bar ke NEECHE inline hai
  - socha Item search 3 se 0 rows kar deta hai; user ke hisaab se aisa nahi hota

Isliye ab dekhte hain: search se pehle aur baad me page pe kya-kya hai.

    python -m framework.search_probe      (ya search-probe.bat)
"""
from playwright.sync_api import sync_playwright

from config.settings import settings
from framework import safety
from framework.auth import login
from framework.browser import launch, describe_window
from framework.screens_check import ensure_neutral
from pages import ItemPage, PartyPage

SNAPSHOT_JS = r"""
() => {
  const norm = t => (t || '').replace(/\s+/g, ' ').trim();
  // har wo element jiska apna text ho (nested nahi) -- taaki inline message bhi mile
  const leaves = [...document.querySelectorAll('div,span,p,td,th,label,h1,h2,h3,li')]
    .filter(e => e.offsetHeight > 0 && e.children.length === 0);
  const texts = [];
  const seen = new Set();
  for (const e of leaves) {
    const t = norm(e.innerText);
    if (!t || t.length > 120 || seen.has(t)) continue;
    seen.add(t);
    const r = e.getBoundingClientRect();
    texts.push({t, tag: e.tagName.toLowerCase(),
                cls: (typeof e.className === 'string' ? e.className : '').slice(0, 45),
                y: Math.round(r.top)});
  }
  texts.sort((a, b) => a.y - b.y);
  return {
    url: location.href,
    window: {vw: window.innerWidth, vh: window.innerHeight,
             ow: window.outerWidth, oh: window.outerHeight,
             sw: screen.width, sh: screen.height,
             aw: screen.availWidth, ah: screen.availHeight,
             dpr: window.devicePixelRatio,
             docW: document.documentElement.scrollWidth,
             docH: document.documentElement.scrollHeight},
    texts: texts.slice(0, 120),
  };
}
"""


def snap(page):
    return page.evaluate(SNAPSHOT_JS)


def diff_texts(a, b):
    """Search ke baad kaunsa text NAYA aaya."""
    old = {x["t"] for x in a["texts"]}
    return [x for x in b["texts"] if x["t"] not in old]


def probe(bp, PageCls, name, term, out):
    print(f"\n===== {name} =====")
    ensure_neutral(bp)
    p = PageCls.open(bp)
    bp.page.wait_for_timeout(1500)

    before = snap(bp.page)
    rows_before = p.names()
    print(f"  pehle : {len(rows_before)} rows  {rows_before[:3]}")

    p.search(term)
    bp.page.wait_for_timeout(2500)
    after = snap(bp.page)
    rows_after = p.names()
    print(f"  baad  : {len(rows_after)} rows  {rows_after[:3]}")

    new_text = diff_texts(before, after)
    print(f"  NAYA text screen pe ({len(new_text)}):")
    for x in new_text[:12]:
        print(f"     y={x['y']:<5} <{x['tag']}> {x['cls']!r}  {x['t']!r}")

    lines = [f"===== {name} =====",
             f"URL: {after['url']}",
             f"search term: {term!r}",
             f"rows pehle: {len(rows_before)}  {rows_before[:5]}",
             f"rows baad : {len(rows_after)}  {rows_after[:5]}",
             "",
             "--- search ke BAAD jo NAYA text aaya (inline message yahin milega) ---"]
    for x in new_text:
        lines.append(f"  y={x['y']:<5} <{x['tag']}> class={x['cls']!r}  {x['t']!r}")
    lines += ["", "--- screen ke saare text (upar se neeche) ---"]
    for x in after["texts"][:80]:
        lines.append(f"  y={x['y']:<5} <{x['tag']}> {x['t']!r}")

    (out / f"searchprobe_{name}.txt").write_text("\n".join(lines), encoding="utf-8")
    bp.screenshot(f"searchprobe_{name}")
    return after["window"]


def main():
    settings.validate()
    run = settings.init_run("search + window probe")

    with sync_playwright() as pw:
        browser, ctx = launch(pw)
        bp = login(ctx.new_page(), verbose=True)

        w = snap(bp.page)["window"]
        print("\n===== WINDOW =====")
        print(f"  viewport (page ka andar) : {w['vw']} x {w['vh']}")
        print(f"  outer window (poori)     : {w['ow']} x {w['oh']}")
        print(f"  screen                   : {w['sw']} x {w['sh']}")
        print(f"  screen available         : {w['aw']} x {w['ah']}  (taskbar ke bina)")
        print(f"  zoom (devicePixelRatio)  : {w['dpr']}")
        print(f"  page ka asli size        : {w['docW']} x {w['docH']}")
        if w["docW"] > w["vw"] + 5:
            print(f"  !! Page {w['docW'] - w['vw']}px CHAUDA hai window se -> "
                  f"horizontal scroll aayega")
        if w["ow"] > w["aw"] + 5:
            print(f"  !! Window screen se {w['ow'] - w['aw']}px BADI hai -> kategi")

        probe(bp, ItemPage, "item", "ZZQQ_NOPE_999", run)
        probe(bp, PartyPage, "party", "ZZQQ_NOPE_999", run)

        (run / "window_info.txt").write_text(
            "\n".join(f"{k}: {v}" for k, v in w.items()), encoding="utf-8")
        ensure_neutral(bp)
        browser.close()

    print(f"\n{'='*55}")
    print(f"  searchprobe_*.txt aur window_info.txt bhej do")
    print(f"  {run}")
    print(f"{'='*55}")


if __name__ == "__main__":
    main()
