"""
MargBooks ke SOURCE CODE se locators nikaalna.

KYUN
----
Ab tak agent locators do tarah se paata tha: browser me page kholkar scan
karna, ya haath se likhna. Dono ki apni seema hai:

  - Browser wala tareeka sirf UNHI screens ko dekh paata hai jahan agent
    pahunch sake. Jo screen permission ke peeche hai, ya jo popup kisi khaas
    haalat me hi aata hai -- wo kabhi catalogue me nahi aayega.
  - Haath se likhna dheema hai aur har release me toot ta hai.

Par MargBooks ka source code SAB kuch jaanta hai -- har route, har field ka
id, har label -- chahe wo screen kabhi khuli ho ya nahi.

Isliye ye scanner source padhta hai aur `metadata.json` banata hai. Uske
baad agent ko koi bhi field pehle hi din mil jata hai.

KYA PADHTA HAI
--------------
  .html / .htm          -- id, name, formControlName, placeholder, label
  .jsx / .tsx / .js/.ts -- routes, aur JSX me likhe id/label
  .component.ts         -- Angular ke selector aur templateUrl

BHARI FOLDER CHHOD DETA HAI
---------------------------
node_modules, dist, build, .git, coverage, assets, .angular waghairah --
inme kuch nahi milta aur scan ghanton ka ho jata hai.
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path

from config.settings import ROOT

FILE = ROOT / "locators" / "metadata.json"

# Inke andar jaana hi nahi. Ye jaan-boojh kar bade list hai --
# node_modules akela hi laakhon file de deta hai aur scan ghanton ka ho jata.
SKIP_DIRS = {
    "node_modules", "dist", "build", "out", ".git", ".svn", ".hg",
    "coverage", ".nyc_output", "assets", "images", "img", "fonts",
    ".angular", ".next", ".cache", "vendor", "bower_components",
    "__pycache__", "venv", ".venv", "env", "test-results",
    "playwright-report", "allure-results", ".idea", ".vscode",
}
SKIP_FILE_PARTS = (".min.", ".spec.", ".test.", ".bundle.", ".map")

# Ye files kabhi nahi padhi jatin -- inme UI ka kuch nahi hota, par
# password aur key hoti hain. Ek galti se wo metadata.json me chali jayein
# to wo file git me bhi ja sakti hai.
SECRET_NAMES = {
    ".env", ".env.local", ".env.production", ".env.development",
    "credentials", "credentials.json", "secrets.json", "secret.json",
    "id_rsa", "id_dsa", ".npmrc", ".netrc", "keystore.jks",
}
SECRET_PARTS = ("secret", "credential", "password", "apikey", "api_key",
                "private_key", ".pem", ".key", ".p12", ".pfx")

READ_EXT = {".html", ".htm", ".jsx", ".tsx", ".js", ".ts", ".vue"}
MAX_FILE_BYTES = 900_000        # isse badi file me UI markup nahi hota

# ---- attribute nikaalne wale patterns ----
ATTR_PATTERNS = {
    "id":               re.compile(r'\bid\s*=\s*["\']([^"\']{1,60})["\']'),
    "formcontrolname":  re.compile(r'\bformControlName\s*=\s*["\']([^"\']{1,60})["\']',
                                   re.I),
    "name":             re.compile(r'\bname\s*=\s*["\']([^"\']{1,60})["\']'),
    "placeholder":      re.compile(r'\bplaceholder\s*=\s*["\']([^"\']{1,80})["\']'),
    "aria":             re.compile(r'\baria-label\s*=\s*["\']([^"\']{1,80})["\']'),
    "data_testid":      re.compile(r'\bdata-testid\s*=\s*["\']([^"\']{1,60})["\']'),
}

TAG_RE = re.compile(
    r"<(input|select|textarea|button|a)\b([^>]*)>", re.I | re.S)
LABEL_RE = re.compile(r"<label\b([^>]*)>(.*?)</label>", re.I | re.S)
TEXT_RE = re.compile(r">\s*([^<>{}\n]{2,40})\s*<")

ROUTE_PATTERNS = (
    re.compile(r'path\s*:\s*["\']([^"\']{1,80})["\']'),          # Angular/React router
    re.compile(r'<Route[^>]*path\s*=\s*["\']([^"\']{1,80})["\']', re.I),
    re.compile(r'routerLink\s*=\s*["\']([^"\']{1,80})["\']'),
)


def _clean(t: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", t or "")).strip()


def _walk(root: Path, max_files: int) -> list[Path]:
    """Padhne layak files -- bhari folder chhod kar."""
    out: list[Path] = []
    for p in root.rglob("*"):
        if len(out) >= max_files:
            break
        if p.is_dir():
            continue
        if any(part in SKIP_DIRS for part in p.parts):
            continue
        if p.suffix.lower() not in READ_EXT:
            continue
        low = p.name.lower()
        if any(s in low for s in SKIP_FILE_PARTS):
            continue
        if low in SECRET_NAMES or any(s in low for s in SECRET_PARTS):
            continue
        try:
            if p.stat().st_size > MAX_FILE_BYTES:
                continue
        except OSError:
            continue
        out.append(p)
    return out


def _elements_in(text: str, rel: str) -> list[dict]:
    """Ek file ke saare interactive element."""
    found: list[dict] = []

    # <label for="x">Party Name</label> -> id ka label
    labels: dict[str, str] = {}
    for attrs, inner in LABEL_RE.findall(text):
        m = re.search(r'\bfor\s*=\s*["\']([^"\']+)["\']', attrs)
        if m:
            labels[m.group(1)] = _clean(inner)

    for tag, attrs in TAG_RE.findall(text):
        row: dict = {"tag": tag.lower(), "file": rel}
        for key, pat in ATTR_PATTERNS.items():
            m = pat.search(attrs)
            if m:
                row[key] = m.group(1)
        m = re.search(r'\btype\s*=\s*["\']([^"\']+)["\']', attrs)
        if m:
            row["type"] = m.group(1).lower()

        if row.get("id") and row["id"] in labels:
            row["label"] = labels[row["id"]]

        # kuch to pehchan honi chahiye, warna wo element bekaar hai
        if not any(row.get(k) for k in
                   ("id", "formcontrolname", "name", "placeholder",
                    "aria", "data_testid", "label")):
            continue

        row["selectors"] = _selectors_for(row)
        row["kind"] = ("click" if row["tag"] in ("button", "a")
                       else "select" if row["tag"] == "select" else "type")
        found.append(row)
    return found


def _selectors_for(row: dict) -> list[str]:
    """Ek element tak pahunchne ke raaste -- sabse pakka pehle."""
    tag = row.get("tag", "")
    out = []
    if row.get("id") and re.fullmatch(r"[A-Za-z][\w-]*", row["id"]):
        out.append(f"{tag}#{row['id']}")
    if row.get("data_testid"):
        out.append(f'[data-testid="{row["data_testid"]}"]')
    if row.get("formcontrolname"):
        out.append(f'{tag}[formcontrolname="{row["formcontrolname"]}"]')
    if row.get("name"):
        out.append(f'{tag}[name="{row["name"]}"]')
    if row.get("aria"):
        out.append(f'[aria-label="{row["aria"]}"]')
    if row.get("placeholder"):
        out.append(f'{tag}[placeholder="{row["placeholder"]}"]')
    if row.get("label"):
        out.append(f'nearlabel={row["label"]}')
    return out


def scan(path: str | Path, max_files: int = 6000,
         verbose: bool = False) -> dict:
    """
    Source folder scan karke metadata banao.

    Purana metadata mitate nahi -- naye elements JOD te hain. Ek shakha me
    koi screen na ho, iska matlab ye nahi ki wo screen hai hi nahi.
    """
    root = Path(path).expanduser()

    # Path ki jaanch -- ".." se koi kahin bhi na pahunch jaye.
    #
    # Ye path UI se aata hai, aur UI localhost par khula rehta hai. Bina
    # jaanche use lene ka matlab hoga ki koi bhi "../../.." bhej kar poori
    # machine scan karwa sakta hai.
    try:
        root = root.resolve(strict=True)
    except (OSError, RuntimeError) as e:
        raise FileNotFoundError(f"'{path}' tak pahunch nahi paye: {e}") from e
    if not root.exists():
        raise FileNotFoundError(f"'{root}' naam ka koi folder nahi hai")
    if root.is_file():
        root = root.parent

    # Poori disk ya home folder scan karne se kuch nahi milta, bas ghante
    # lagte hain -- aur us raste me niji files bhi aa jati hain.
    #
    # ASLI BUG: pehle yahan `root == root.anchor` tha -- Path ki barabari str se,
    # jo kabhi True nahi hoti. Windows pe "/" resolve hoke D:\ ban jata hai aur
    # poori drive scan ho jati thi (guard chupchaap bekaar tha).
    if (root == Path(root.anchor) or root == Path.home()
            or root.parent == Path(root.anchor) and root.name.lower() in
            ("users", "windows", "program files", "program files (x86)")
            or str(root) in ("/home", "/root")):
        raise FileNotFoundError(
            f"'{root}' bahut bada hai. MargBooks ke project ka folder do "
            f"(jisme src\\ ya app\\ ho).")

    t0 = time.time()
    files = _walk(root, max_files)
    if verbose:
        print(f"  {len(files)} file padhni hain...")

    elements: list[dict] = []
    routes: set[str] = set()
    read = skipped = 0

    for f in files:
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:  # noqa: BLE001
            skipped += 1
            continue
        read += 1
        rel = str(f.relative_to(root)).replace("\\", "/")
        elements.extend(_elements_in(text, rel))
        for pat in ROUTE_PATTERNS:
            for r in pat.findall(text):
                if r and not r.startswith(("http", "#", "{")) and len(r) < 60:
                    routes.add("/" + r.lstrip("/"))

    from framework import logbook
    logbook.write("scanner", "scan", "ok",
                  duration=time.time() - t0, path=str(root),
                  files=read, elements=len(elements), routes=len(routes))

    merged = _merge(elements, routes, str(root),
                    {"files_read": read, "files_skipped": skipped,
                     "seconds": round(time.time() - t0, 1)})
    if verbose:
        print(f"  {len(elements)} element, {len(routes)} route "
              f"({merged['stats']['seconds']}s)")
    return merged


def _merge(elements: list[dict], routes: set[str], root: str,
           stats: dict) -> dict:
    """Naya scan purane ke UPAR jodo -- mitao mat."""
    data = load()
    bucket = data.setdefault("elements", {})
    new = 0
    for el in elements:
        key = (el.get("id") or el.get("data_testid") or el.get("formcontrolname")
               or el.get("name") or f"{el['tag']}:{el.get('placeholder', '')}")
        if not key:
            continue
        old = bucket.get(key)
        if old:
            sels = list(dict.fromkeys(old.get("selectors", []) + el["selectors"]))
            old.update({**el, "selectors": sels[:8],
                        "seen": old.get("seen", 0) + 1})
        else:
            bucket[key] = {**el, "seen": 1}
            new += 1

    data["routes"] = sorted(set(data.get("routes", [])) | routes)
    data["source"] = root
    data["scanned_at"] = time.strftime("%Y-%m-%d %H:%M")
    data["stats"] = {**stats, "elements_total": len(bucket), "new": new}
    save(data)
    return data


# ---------------------------------------------------------------- store

def _blank() -> dict:
    return {"version": 1, "source": "", "scanned_at": None,
            "routes": [], "elements": {}, "stats": {}}


def load() -> dict:
    if not FILE.exists():
        return _blank()
    try:
        d = json.loads(FILE.read_text(encoding="utf-8"))
        return d if "elements" in d else _blank()
    except Exception:  # noqa: BLE001
        return _blank()


def save(data: dict):
    FILE.parent.mkdir(parents=True, exist_ok=True)
    FILE.write_text(json.dumps(data, indent=1, ensure_ascii=False),
                    encoding="utf-8")


# ---------------------------------------------------------------- use

def _tokens(text: str) -> list[str]:
    t = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", str(text or ""))
    return [w for w in re.findall(r"[a-z0-9]+", t.lower())
            if w not in ("txt", "btn", "input", "field", "ng")]


def resolve(phrase: str, kind: str = "any", min_score: int = 60) -> dict | None:
    """
    Naam se element dhoondho -- source se nikaale hue metadata me.

    Bharosa kam ho to None. Source me hazaron element hote hain; unme se
    galat utha lena chupchaap galat test bana dega.
    """
    want = _tokens(phrase)
    if not want:
        return None
    rows = load().get("elements", {})
    best = None

    for key, el in rows.items():
        if kind != "any" and el.get("kind") not in (kind, "select"):
            continue
        if re.search(r"del(ete)?|remove|trash", key, re.I):
            continue
        score = 0
        for field, weight in (("label", 100), ("placeholder", 90),
                              ("aria", 90), ("data_testid", 80),
                              ("formcontrolname", 70), ("id", 65), ("name", 60)):
            toks = _tokens(el.get(field, ""))
            if not toks:
                continue
            if toks == want:
                score = max(score, weight)
            elif set(want) <= set(toks):
                score = max(score, weight - 12)
            else:
                hit = len(set(want) & set(toks))
                if hit:
                    score = max(score,
                                int(weight * hit / max(len(want), len(toks))) - 5)
        if score and (best is None or score > best[0]):
            best = (score, key, el)

    if not best or best[0] < min_score:
        return None
    score, key, el = best
    return {"key": key, "score": score, "selectors": el.get("selectors", []),
            "label": el.get("label", ""), "file": el.get("file", ""),
            "kind": el.get("kind")}


def stats() -> dict:
    d = load()
    return {"scanned_at": d.get("scanned_at"), "source": d.get("source", ""),
            "elements": len(d.get("elements", {})),
            "routes": len(d.get("routes", [])),
            **(d.get("stats") or {})}
