"""
Alag-alag environment -- production, UAT, staging, jo bhi.

Tester UI me hi URL aur login daal sake, taaki UAT test karne ke liye .env
file kholni na pade. Har environment ek record hai; ek waqt me ek "active"
rehta hai aur runner wahi use karta hai.

Password file me plain text me jaata hai (jaise .env me jata tha). Isliye ye
file .gitignore me hai. Isse behtar intezaam (OS keychain) baad me ho sakta
hai, par abhi jhooth nahi bolna: ye plain text hai.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from config.settings import ROOT, settings

FILE = ROOT / "config" / "environments.json"


def _blank() -> dict:
    return {"active": "default", "envs": {"default": {
        "name": "default",
        "login_url": settings.LOGIN_URL,
        "app_url": settings.BASE_URL,
        "user": settings.USER,
        "password": settings.PASSWORD,
        "company": settings.COMPANY,
        # Pehla environment banate waqt writes ON.
        #
        # Ye QA ka tool hai aur demo/UAT company par chalta hai -- writes
        # band rakhne se aadhe test SKIP ho jate the aur suite adhoori
        # lagti thi. .env me jo likha hai wo bhi maanate hain, par kuch na
        # likha ho to ON hi theek hai.
        "allow_writes": True if settings.ALLOW_DESTRUCTIVE is None
                        else bool(settings.ALLOW_DESTRUCTIVE) or True,
    }}}


def load() -> dict:
    if not FILE.exists():
        save(_blank())
    try:
        d = json.loads(FILE.read_text(encoding="utf-8"))
        if "envs" not in d:
            raise ValueError
        return _fill_gaps(d)
    except Exception:  # noqa: BLE001
        return _blank()


def _fill_gaps(d: dict) -> dict:
    """
    Khali khaane .env se bhar do.

    ASLI BUG: environments.json purane version me bana tha, jab usme user aur
    company likhe hi nahi jate the. Uske baad UI me hamesha "user —" aur
    "company —" dikhta raha, jabki .env me dono bhare the. File ek baar ban
    jaye to wo purani haalat me atki reh jati thi.

    Ab har baar dekh lete hain: jo khaana khali hai, use .env se bhar do.
    Bhari hui value kabhi nahi badalte -- wo user ne jaan-boojh kar daali hai.
    """
    seed = {
        "login_url": settings.LOGIN_URL, "app_url": settings.BASE_URL,
        "user": settings.USER, "password": settings.PASSWORD,
        "company": settings.COMPANY,
    }
    changed = False
    for env in d.get("envs", {}).values():
        for k, v in seed.items():
            if not env.get(k) and v:
                env[k] = v
                changed = True
    if changed:
        save(d)
    return d


def save(data: dict):
    FILE.parent.mkdir(parents=True, exist_ok=True)
    FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def listing() -> dict:
    """UI ke liye -- password NAHI bhejte, sirf "set hai ya nahi"."""
    d = load()
    out = []
    for k, e in d["envs"].items():
        out.append({
            "name": k, "login_url": e.get("login_url", ""),
            "app_url": e.get("app_url", ""), "user": e.get("user", ""),
            "company": e.get("company", ""),
            "has_password": bool(e.get("password")),
            "allow_writes": bool(e.get("allow_writes")),
            "active": k == d.get("active"),
        })
    return {"active": d.get("active"), "envs": sorted(out, key=lambda x: x["name"])}


def upsert(env: dict) -> dict:
    name = (env.get("name") or "").strip()
    if not name:
        raise ValueError("Environment name is required")
    for f in ("login_url", "app_url"):
        u = (env.get(f) or "").strip()
        if not u.startswith(("http://", "https://")):
            raise ValueError(f"{f} must start with http:// or https://")
    d = load()
    old = d["envs"].get(name, {})
    d["envs"][name] = {
        "name": name,
        "login_url": env["login_url"].strip().rstrip("/"),
        "app_url": env["app_url"].strip().rstrip("/"),
        "user": (env.get("user") or "").strip(),
        # password khali chhoda to purana rakho -- UI use kabhi wapas nahi bhejta
        "password": env.get("password") or old.get("password", ""),
        "company": (env.get("company") or "").strip(),
        "allow_writes": bool(env.get("allow_writes")),
        "saved": time.strftime("%Y-%m-%d %H:%M"),
    }
    save(d)
    return {"name": name}


def remove(name: str) -> bool:
    d = load()
    if name in d["envs"] and len(d["envs"]) > 1:
        d["envs"].pop(name)
        if d.get("active") == name:
            d["active"] = sorted(d["envs"])[0]
        save(d)
        return True
    return False


def activate(name: str) -> bool:
    d = load()
    if name not in d["envs"]:
        return False
    d["active"] = name
    save(d)
    return True


def apply_active():
    """
    Chune hue environment ko settings me daal do.

    Asli kaam config/settings.py karta hai -- wahan rakha hai taaki HAR
    command ko apne aap mile, sirf UI ko nahi. Pehle ye sirf UI me tha aur
    control-room.bat galat company khol deta tha.
    """
    from config.settings import _apply_active_environment
    # FILE pass karte hain (default path nahi) -- warna test ki temp file
    # nazarandaz ho jaati hai aur asli config padh li jaati hai.
    _apply_active_environment(FILE)
    d = load()
    return d["envs"].get(d.get("active")) or {}
