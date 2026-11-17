"""
Locator khud dhoondhne aur YAAD RAKHNE wala hissa.

Zaroorat kyun: saat tester saadhi bhasha me test likhenge. Wo "profile icon pe
click" likhega, aur agar locators file me 'nav.profile' nahi hai to abhi test
ruk jata hai aur developer ko manually add karna padta hai. Ye tool ka kaam
hona chahiye, aadmi ka nahi.

Kaise: key ka aakhri hissa ("profile") lekar live page pe wo element dhoondhte
hain -- id, aria-label, title, text, class, aur aam paryayvachi shabdon se.
Mil gaya to selector banate hain, locators file me LIKH dete hain, aur log me
saaf batate hain ki kya seekha.

Do niyam jo tode nahi jate:
  1. Khatarnak element (delete/remove) kabhi nahi seekhte.
  2. Bharosa kam ho to seekhte hi nahi -- galat locator chupke se save ho jana
     us se bura hai ki test fail ho jaye.
"""
from __future__ import annotations

import re

from framework import safety
from framework.locator_store import store

# key ka aakhri hissa -> page pe kaunse shabd dhoondhein
WORDS: dict[str, list[str]] = {
    "profile": ["profile", "account", "user", "avatar", "pro-pic"],
    "logout": ["logout", "log out", "sign out"],
    "search": ["search", "khoj"],
    "new_btn": ["create", "new", "add", "create/f2"],
    "save_btn": ["save", "f10"],
    "close_btn": ["close", "esc"],
    "settings": ["setting", "settings", "control room"],
    "print": ["print"],
    "export": ["export", "excel", "download"],
    "refresh": ["refresh", "reload", "sync"],
    "help": ["help"],
    "home": ["home", "dashboard"],
}

FIND_JS = r"""
(args) => {
  const words = args.words, want = args.want;
  const norm = t => (t || '').replace(/\s+/g, ' ').trim();
  const low  = t => norm(t).toLowerCase();
  const DANGER = /(del(ete)?|trash|remove|discard|destroy)/i;

  const cands = [...document.querySelectorAll(
    'a, button, input, select, textarea, [role="button"], [role="link"]')];
  const out = [];

  for (const e of cands) {
    const r = e.getBoundingClientRect();
    if (r.width === 0 && r.height === 0) continue;

    // SIRF wo element jo abhi screen pe DIKH raha hai.
    // Chhupi hui settings panel ka dropdown seekh liya gaya tha -- wo yahin
    // rukta hai, kyunki wo viewport ke bahar tha.
    if (r.bottom < 0 || r.top > innerHeight || r.right < 0 || r.left > innerWidth)
      continue;

    // Kis kaam ke liye chahiye, wahi tarah ka element lo.
    const tag = e.tagName.toLowerCase();
    if (want === "type") {
      // likhne ke liye <select> nahi chalega -- yahi galti hui thi
      if (!(tag === "input" || tag === "textarea")) continue;
      if (tag === "input" && ["checkbox","radio","button","submit","file"]
          .includes((e.getAttribute("type") || "").toLowerCase())) continue;
    } else if (want === "click") {
      if (!(tag === "button" || tag === "a" || e.getAttribute("role") === "button"
            || (tag === "input" && ["button","submit"]
                .includes((e.getAttribute("type") || "").toLowerCase())))) continue;
    }
    const id    = e.id || '';
    const cls   = (typeof e.className === 'string' ? e.className : '');
    const aria  = e.getAttribute('aria-label') || '';
    const title = e.getAttribute('title') || '';
    const ph    = e.getAttribute('placeholder') || '';
    const text  = norm(e.innerText || e.value || '');
    const bag   = low([id, cls, aria, title, ph, text].join(' '));

    if (DANGER.test(bag)) continue;              // khatarnak kabhi nahi

    let score = 0, why = '';
    // POORA SHABD milna chahiye, beech me aaya hua nahi.
    //
    // "party" ne "txtaskpartyinretailbilling" me match kar liya tha aur galat
    // element seekh liya gaya. Ab word-boundary zaroori hai.
    //
    // Par camelCase ko tod kar dekhna bhi zaroori hai: "btnSave27" me "Save"
    // asli shabd hai. Chhote akshar ki lambi string ("askpartyinretail") me
    // koi shabd-seema nahi hoti, isliye wo reject ho jati hai -- theek waise
    // hi jaise chahiye.
    const words_of = t => (t || '')
      .replace(/([a-z0-9])([A-Z])/g, '$1 $2')      // camelCase todo
      .replace(/(\d+)/g, ' $1 ')                   // number alag
      .replace(/[_\-.]+/g, ' ');
    const whole = (hay, w) => {
      const h = low(words_of(hay));
      const re = new RegExp(`(^|[^a-z])${w.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')}([^a-z]|$)`, 'i');
      return re.test(h);
    };
    for (const w of words) {
      const lw = w.toLowerCase();
      if (low(id) === lw)                  { score = Math.max(score, 100); why = 'id'; }
      else if (whole(id, lw))              { score = Math.max(score, 82);  why = 'id-word'; }
      if (low(aria) === lw)                { score = Math.max(score, 96);  why = 'aria'; }
      if (low(title) === lw)               { score = Math.max(score, 92);  why = 'title'; }
      if (low(text) === lw)                { score = Math.max(score, 90);  why = 'text'; }
      else if (text && whole(text, lw) && text.length < 30)
                                           { score = Math.max(score, 84);  why = 'text-word'; }
      if (low(ph) === lw)                  { score = Math.max(score, 88);  why = 'placeholder'; }
      else if (whole(ph, lw))              { score = Math.max(score, 80);  why = 'placeholder~'; }
      if (whole(cls, lw))                  { score = Math.max(score, 62);  why = 'class'; }
    }
    if (!score) continue;

    // selector banao -- sabse pakka pehle
    let sel = null;
    if (id && /^[A-Za-z][\w-]*$/.test(id)) sel = `${e.tagName.toLowerCase()}#${id}`;
    else if (aria) sel = `[aria-label="${aria.replace(/"/g, '')}"]`;
    else if (ph)   sel = `[placeholder="${ph.replace(/"/g, '')}"]`;
    else if (text && text.length < 30)
      sel = `${e.tagName.toLowerCase()}:has-text("${text.replace(/"/g, '')}")`;
    if (!sel) continue;

    out.push({sel, score, why, tag: e.tagName.toLowerCase(),
              id, text: text.slice(0, 40)});
  }
  out.sort((a, b) => b.score - a.score);
  return out.slice(0, 4);
}
"""

# Bharosa ki seema. Pehle 70 thi aur usme galat element seekh liya gaya tha.
MIN_SCORE = 80
# Jis key ke selectors pehle se file me hain, uske liye aur bhi zyada bharosa
# chahiye -- kyunki wahan hum kisi ke likhe hue par oopar likh rahe hain.
MIN_SCORE_OVERWRITE = 90


def words_for(key: str) -> list[str]:
    """'nav.profile' -> ['profile', 'account', ...]"""
    tail = key.split(".")[-1]
    base = WORDS.get(tail, [])
    extra = [w for w in re.split(r"[_\-]", tail) if len(w) > 2]
    return list(dict.fromkeys([tail.replace("_", " "), *base, *extra]))


def learn(page, key: str, want: str = "any", verbose: bool = True) -> dict | None:
    """
    Live page pe key dhoondho. Mil gaya to locators file me likh do.

    want = "type"  -> sirf likhne wale field (input/textarea)
           "click" -> sirf button/link
           "any"   -> kuch bhi

    None agar bharosa kam ho -- aur yahi default rawaiya hai.
    """
    try:
        hits = page.evaluate(FIND_JS, {"words": words_for(key), "want": want})
    except Exception:  # noqa: BLE001
        return None
    if not hits:
        return None

    try:
        already = bool(store.candidates(key))
    except Exception:  # noqa: BLE001
        already = False
    threshold = MIN_SCORE_OVERWRITE if already else MIN_SCORE

    best = hits[0]
    if best["score"] < threshold:
        if verbose:
            print(f"  [autolearn] '{key}' ke liye pakka element nahi mila "
                  f"(sabse behtar: {best['sel']} score {best['score']}, "
                  f"chahiye {threshold}) -- jaan-boojh kar NAHI seekha")
        return None

    # dobara jaanch: guard bhi isse surakshit maane
    try:
        loc = page.locator(best["sel"]).first
        safety.assert_safe(loc, f"autolearn:{key}")
    except safety.UnsafeClick:
        if verbose:
            print(f"  [autolearn] '{key}' -> {best['sel']} khatarnak laga, chhod diya")
        return None
    except Exception:  # noqa: BLE001
        return None

    sels = [h["sel"] for h in hits if h["score"] >= threshold][:3]
    store.add(key, sels)
    store.save()
    if verbose:
        print(f"  [autolearn] SEEKHA  {key} -> {best['sel']}  "
              f"({best['why']}, score {best['score']})")
    return {"key": key, "selector": best["sel"], "score": best["score"],
            "why": best["why"], "alternatives": sels[1:]}


LEARNED: list[dict] = []


def remember(info: dict):
    LEARNED.append(info)


def report(path) -> str | None:
    if not LEARNED:
        return None
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["Is run me ye locators KHUD SEEKHE gaye:",
             "(locators/margbooks.yaml me save ho chuke hain -- ek baar dekh lo)", ""]
    for l in LEARNED:
        lines.append(f"  {l['key']:<28} -> {l['selector']}   "
                     f"({l['why']}, score {l['score']})")
    path.write_text("\n".join(lines), encoding="utf-8")
    return str(path)
