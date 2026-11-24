"""
The company id (MargBooks `linkid`, sent by the app as the `complinkid` header) of every QA test company, per
environment host. The Python scripts' QA guard (e2e_scripts/fixtures/studio_guard.py) lets a write through only
when its complinkid is one of these, so the ids must be the real ones of the environment chosen in Settings.

Read once from the app's own company list (/v4.2/Company/List, loaded by the Organisation List screen) with the
Settings login, and cached in config/qa_company_ids.json. Only names in framework.qa_company.TEST_COMPANIES count.
"""
from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from urllib.parse import urlparse

CACHE = Path(__file__).resolve().parents[1] / "config" / "qa_company_ids.json"
_lock = threading.Lock()


def _host(url: str) -> str:
    return (urlparse(url or "").hostname or "").lower()


def _load() -> dict:
    try:
        return json.loads(CACHE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def cached(app_url: str) -> dict[str, str]:
    return dict((_load().get(_host(app_url)) or {}).get("ids") or {})


def login_page(app_url: str) -> str:
    """The page the login URL really ends on (books6.margbooks.com/login moves to margbooks.com/login/ in the
    browser); '' until discover() has run for this environment."""
    return str((_load().get(_host(app_url)) or {}).get("login_page") or "")


def ids_from_company_list(payload) -> dict[str, str]:
    """{QA company name: linkid} from a /Company/List reply ({"Data": [{"compname", "linkid", ...}]})."""
    from framework.qa_company import TEST_COMPANIES
    rows = (payload or {}).get("Data") if isinstance(payload, dict) else None
    if isinstance(rows, dict):                       # {"Data": {"<list name>": [...]}} on some app versions
        rows = next((v for v in rows.values() if isinstance(v, list)), [])
    out: dict[str, str] = {}
    for r in rows if isinstance(rows, list) else []:
        name = str((r or {}).get("compname") or "").strip()
        lid = str((r or {}).get("linkid") or "").strip()
        if name in TEST_COMPANIES and lid.isdigit() and lid != "0":
            out[name] = lid
    return out


def discover(app_url: str) -> dict[str, str]:
    """Log in with the Settings login, open the Organisation List and read the QA companies' ids. Cached."""
    from playwright.sync_api import sync_playwright
    from config.settings import settings
    from framework.auth import login
    from framework.browser import launch
    found: dict[str, str] = {}
    landed = ""

    def on_response(r):
        if r.url.split("?", 1)[0].rstrip("/").endswith("/Company/List"):
            try:
                found.update(ids_from_company_list(r.json()))
            except Exception:  # noqa: BLE001
                pass

    with _lock, sync_playwright() as pw:
        browser, ctx = launch(pw, record_video=False)
        try:
            probe = ctx.new_page()
            probe.goto(settings.LOGIN_URL, wait_until="domcontentloaded")
            probe.wait_for_timeout(4000)                      # the login app moves itself to its own host
            landed = probe.url.split("?", 1)[0].split("#", 1)[0]
            probe.close()
            bp = login(ctx.new_page())
            bp.page.on("response", on_response)
            bp.page.goto(settings.BASE_URL.rstrip("/") + "/user-company", wait_until="domcontentloaded")
            for _ in range(40):
                if found:
                    break
                bp.page.wait_for_timeout(500)
        finally:
            browser.close()
    if not found:
        raise RuntimeError("Could not read the QA test companies' ids from the company list. Check the login in "
                           "Settings > App under test (Test login), then run the script again.")
    data = _load()
    data[_host(app_url)] = {"ids": found, "login_page": landed, "updated": time.strftime("%d-%b-%Y %H:%M")}
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(data, indent=1) + "\n", encoding="utf-8")
    return found


def get(app_url: str) -> dict[str, str]:
    return cached(app_url) if cached(app_url) and login_page(app_url) else discover(app_url)
