"""
Har click ko uske ASLI source ke saath record karta hai.

Python-taraf ka audit sirf wahi clicks dekh sakta hai jo humne kiye. Agar app
khud, ya keyboard shortcut, ya koi JS timer delete chala de -- to wo audit me
dikhega hi nahi. Isliye ye recorder browser ke andar baithta hai aur HAR click
pakadta hai, chahe wo kahin se bhi aaye.

isTrusted=false ka matlab: click asli mouse se nahi, code se hua.
"""
RECORDER_JS = r"""
(() => {
  if (window.__mbRec) return;
  window.__mbRec = true;
  window.__mbEvents = [];

  const desc = (el) => {
    if (!el || !el.tagName) return null;
    return {
      tag: el.tagName.toLowerCase(),
      id: el.id || '',
      cls: (typeof el.className === 'string' ? el.className : '').slice(0, 60),
      text: (el.innerText || el.value || '').trim().slice(0, 40),
      title: el.getAttribute('title') || '',
    };
  };

  const DANGER = /(del(ete)?|trash|remove|discard|destroy)/i;
  const looksDanger = (el) => {
    if (!el) return false;
    const bag = [el.className, el.id, el.getAttribute?.('title') || ''].join(' ');
    return DANGER.test(bag);
  };

  // capture phase -- app ke apne handler se PEHLE
  document.addEventListener('click', (e) => {
    const path = (e.composedPath ? e.composedPath() : [e.target]).slice(0, 5);
    const danger = path.some(looksDanger);
    let stack = '';
    if (danger) { try { throw new Error('trace'); } catch (err) { stack = err.stack || ''; } }
    window.__mbEvents.push({
      type: 'click',
      at: Date.now(),
      trusted: e.isTrusted,       // false = code ne kiya, asli mouse nahi
      danger,
      target: desc(e.target),
      chain: path.map(desc).filter(Boolean).slice(0, 4),
      stack: stack.split('\n').slice(1, 6).join(' | '),
    });
  }, true);

  document.addEventListener('keydown', (e) => {
    if (['Escape', 'Delete', 'Backspace', 'F2', 'F10', 'Enter'].includes(e.key)) {
      window.__mbEvents.push({
        type: 'key', at: Date.now(), key: e.key, trusted: e.isTrusted,
        target: desc(document.activeElement),
      });
    }
  }, true);
})();
"""


def arm(context):
    context.add_init_script(RECORDER_JS)


def dump(page) -> list[dict]:
    try:
        return page.evaluate("() => window.__mbEvents || []")
    except Exception:  # noqa: BLE001
        return []


def report(page, path):
    ev = dump(page)
    if not ev:
        return None
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["BROWSER EVENT RECORDER", "trusted=False matlab click code se hua, mouse se nahi", ""]
    for e in ev:
        if e.get("type") == "key":
            lines.append(f"{e['at']}  KEY {e['key']:<10} trusted={e['trusted']} "
                         f"on={e.get('target')}")
        else:
            flag = "  *** DANGER ***" if e.get("danger") else ""
            lines.append(f"{e['at']}  CLICK trusted={e['trusted']}{flag}")
            lines.append(f"        target: {e.get('target')}")
            if e.get("danger"):
                lines.append(f"        chain : {e.get('chain')}")
                lines.append(f"        stack : {e.get('stack')}")
    path.write_text("\n".join(lines), encoding="utf-8")
    return path
