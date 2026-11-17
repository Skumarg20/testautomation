"""
Grid ka asli DOM dhaancha nikaalo.

Do baar andaza laga chuke hain aur dono baar galat nikla ("sabse zyada rows",
phir "header ka closest table"). Ab guess nahi -- asli structure dekhenge.

    python -m framework.grid_probe
"""
from playwright.sync_api import sync_playwright

from config.settings import settings
from framework import safety
from framework.auth import login
from framework.browser import launch, describe_window
from framework.screens import open_screen
from framework.screens_check import ensure_neutral

PROBE_JS = r"""
(header) => {
  const norm = t => (t || '').replace(/\s+/g, ' ').trim();
  const out = {header, steps: []};

  const all = [...document.querySelectorAll('*')];
  const hdr = all.find(e => norm(e.innerText) === header && e.offsetHeight > 0
                          && e.children.length === 0);
  if (!hdr) { out.error = `'${header}' nahi mila`; return out; }

  // header se upar 6 parent tak ka dhaancha
  let n = hdr, depth = 0;
  while (n && depth < 7) {
    out.steps.push({
      depth,
      tag: n.tagName.toLowerCase(),
      cls: (typeof n.className === 'string' ? n.className : '').slice(0, 70),
      id: n.id || '',
      children: n.children.length,
      childTags: [...n.children].slice(0, 6).map(c => c.tagName.toLowerCase()).join(','),
      rowsIfTable: n.tagName === 'TABLE'
        ? n.querySelectorAll('tr').length : null,
      text: norm(n.innerText).slice(0, 60),
    });
    n = n.parentElement; depth++;
  }

  // jo bhi ek known cell text rakhta ho uske parents -- asli data row wahi hai
  const sample = all.find(e => /Sample Item|Cash Account|CGST Input/.test(norm(e.innerText))
                             && e.children.length === 0 && e.offsetHeight > 0);
  if (sample) {
    out.sampleCell = {text: norm(sample.innerText).slice(0, 40)};
    let m = sample, d2 = 0;
    out.sampleParents = [];
    while (m && d2 < 5) {
      out.sampleParents.push({
        depth: d2, tag: m.tagName.toLowerCase(),
        cls: (typeof m.className === 'string' ? m.className : '').slice(0, 70),
        children: m.children.length,
        siblings: m.parentElement ? m.parentElement.children.length : 0,
      });
      m = m.parentElement; d2++;
    }
  }

  // saare table/tbody ka hisaab
  out.tables = [...document.querySelectorAll('table')].map(t => ({
    cls: (typeof t.className === 'string' ? t.className : '').slice(0, 50),
    trs: t.querySelectorAll('tr').length,
    tbodyTrs: t.querySelectorAll('tbody tr').length,
    visible: t.offsetHeight > 0,
  }));
  return out;
}
"""


def probe(bp, screen: str, header: str, out_dir):
    print(f"\n>> {screen}  (header: {header!r})")
    if not open_screen(bp, screen):
        print("   screen khul nahi paya")
        return
    bp.page.wait_for_timeout(2500)
    data = bp.page.evaluate(PROBE_JS, header)

    lines = [f"SCREEN: {screen}", f"HEADER: {header}", f"URL: {bp.page.url}", ""]
    if data.get("error"):
        lines.append(f"ERROR: {data['error']}")
    lines.append("--- header ke upar ka dhaancha ---")
    for s in data.get("steps", []):
        lines.append(f"  d{s['depth']} <{s['tag']}> id={s['id']!r} class={s['cls']!r} "
                     f"children={s['children']} [{s['childTags']}] "
                     f"trs={s['rowsIfTable']}")
    lines.append("")
    lines.append("--- ek asli data cell ke upar ka dhaancha ---")
    lines.append(f"  cell: {data.get('sampleCell')}")
    for s in data.get("sampleParents", []):
        lines.append(f"  d{s['depth']} <{s['tag']}> class={s['cls']!r} "
                     f"children={s['children']} siblings={s['siblings']}")
    lines.append("")
    lines.append("--- page ke saare <table> ---")
    for t in data.get("tables", []):
        lines.append(f"  class={t['cls']!r} trs={t['trs']} tbodyTrs={t['tbodyTrs']} "
                     f"visible={t['visible']}")

    f = out_dir / f"gridprobe_{screen}.txt"
    f.write_text("\n".join(lines), encoding="utf-8")
    print(f"   -> {f.name}")
    for l in lines[:22]:
        print("   " + l)


def main():
    settings.validate()
    run = settings.init_run("grid probe")

    with sync_playwright() as pw:
        browser, ctx = launch(pw)
        bp = login(ctx.new_page(), verbose=True)
        print(f"\nWindow: {describe_window(bp.page)}")

        probe(bp, "item", "Description", run)
        ensure_neutral(bp)
        probe(bp, "party", "Ledger Name", run)
        ensure_neutral(bp)
        browser.close()

    print(f"\n{'='*55}\n  gridprobe_*.txt bhej do\n  {run}\n{'='*55}")


if __name__ == "__main__":
    main()
