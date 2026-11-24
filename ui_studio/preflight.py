"""
Before going live (and after every update): is this machine ready to run the team Test Studio?

    .venv\\Scripts\\python -m ui_studio.preflight            # checks only, changes nothing
    .venv\\Scripts\\python -m ui_studio.preflight --json     # the same for scripts

Each line is PASS, WARN (works, but fix it soon) or FAIL (the Studio will not work for the team). Exit code 1 when
anything FAILs. Nothing here logs in to MargBooks or changes data.
"""
from __future__ import annotations

import json
import os
import shutil
import socket
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _check(results: list, name: str, fn):
    try:
        status, detail = fn()
    except Exception as e:  # noqa: BLE001  (a check that crashes is itself a failure)
        status, detail = "FAIL", f"{type(e).__name__}: {str(e)[:200]}"
    results.append({"check": name, "status": status, "detail": detail})


def python_version():
    v = sys.version_info
    return ("PASS" if (v.major, v.minor) >= (3, 11) else "FAIL"), f"Python {v.major}.{v.minor}.{v.micro}"


def libraries():
    missing = []
    for mod in ("playwright", "yaml", "dotenv", "pytest", "anthropic"):
        try:
            __import__(mod)
        except ImportError:
            missing.append(mod)
    if missing:
        return "FAIL", "missing: " + ", ".join(missing) + " (run deploy\\install.bat or setup.bat)"
    lock = ROOT / "deploy" / "requirements-lock.txt"
    if lock.exists():
        from importlib import metadata
        want = dict(ln.strip().split("==", 1) for ln in lock.read_text(encoding="utf-8").splitlines() if "==" in ln)
        off = []
        for pkg in ("playwright", "pytest", "PyYAML", "anthropic"):
            try:
                have = metadata.version(pkg)
            except metadata.PackageNotFoundError:
                have = "-"
            if pkg in want and have != want[pkg]:
                off.append(f"{pkg} {have} (tested {want[pkg]})")
        if off:
            return "WARN", "versions differ from the tested ones: " + "; ".join(off)
    return "PASS", "all libraries present, tested versions"


def browser():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        b = pw.chromium.launch(headless=True)
        b.close()
    return "PASS", "Chromium starts"


def environment():
    from ui import envs
    e = envs.apply_active() or {}
    missing = [k for k in ("app_url", "user", "password", "company") if not e.get(k)]
    if missing:
        return "FAIL", "Settings > App under test is missing: " + ", ".join(missing)
    host = str(e["app_url"]).split("//")[-1]
    return "PASS", f"{host} | {e['company']} | writes {'on' if e.get('allow_writes') else 'off'}"


def admin_account():
    from ui_studio import accounts
    users = accounts.list_users()
    admins = [u for u in users if u["role"] == "admin" and not u["disabled"]]
    if not admins:
        return "FAIL", "no admin: .venv\\Scripts\\python -m ui_studio.accounts add you@margerp.net --admin"
    no_mb = [u["username"] for u in users if not u["mb_user"] and not u["disabled"]]
    detail = f"{len(users)} account(s), {len(admins)} admin(s)"
    if no_mb:
        return "WARN", detail + f"; without their own MargBooks login (they cannot run tests): {', '.join(no_mb[:5])}"
    return "PASS", detail


def password_encryption():
    from ui_studio import accounts
    sealed = accounts.seal("preflight-check")
    if accounts.unseal(sealed) != "preflight-check":
        return "FAIL", "MargBooks passwords cannot be encrypted / read back"
    how = "Windows DPAPI" if sealed.startswith("dpapi:") else "Fernet (STUDIO_SECRET_KEY)"
    return "PASS", f"{how}; keep the service on ONE Windows account (passwords are tied to it)"


def database():
    from ui_studio import state
    with state.db() as c:
        c.execute("SELECT COUNT(*) FROM runs").fetchone()
    return "PASS", f"{state.DB} (back it up daily: deploy\\backup.bat)"


def port():
    from ui_studio import mode
    s = socket.socket()
    try:
        s.bind((mode.HOST if mode.HOST not in ("0.0.0.0", "") else "", mode.PORT))
    except OSError:
        try:
            import urllib.request
            urllib.request.urlopen(f"http://127.0.0.1:{mode.PORT}/healthz", timeout=3)
            return "PASS", f"port {mode.PORT} is in use by a running Test Studio"
        except Exception:  # noqa: BLE001
            return "FAIL", f"port {mode.PORT} is used by another program (set STUDIO_PORT)"
    finally:
        s.close()
    return "PASS", f"port {mode.PORT} is free (host {mode.HOST})"


def disk():
    free = shutil.disk_usage(ROOT).free / 1e9
    return ("PASS" if free > 10 else "WARN" if free > 3 else "FAIL"), f"{free:.0f} GB free (runs keep screenshots / videos)"


def https():
    from ui_studio import mode
    if not mode.SERVER:
        return "WARN", "STUDIO_MODE is not server: this is the one-PC Studio (no logins)"
    if not mode.SECURE_COOKIE:
        return "WARN", "no HTTPS (STUDIO_SECURE_COOKIE off): passwords cross the network in clear text; fine only on a trusted LAN"
    return "PASS", "HTTPS cookies on"


def scripts_env():
    py = ROOT / "e2e_scripts" / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if not py.exists():
        return "WARN", "Python scripts (e2e_scripts) have no environment: they cannot run (Studio tests still work)"
    return "PASS", "Python scripts environment present"


def ai_key():
    from framework import ai
    return ("PASS", f"AI: {ai.available().get('active')}") if ai.available().get("active") else \
        ("WARN", "no AI key: replay AI fixes, 'Explain with AI' and 'Write as a script' are off")


CHECKS = [("Python", python_version), ("Libraries", libraries), ("Browser", browser),
          ("App under test (Settings)", environment), ("Admin account", admin_account),
          ("Password encryption", password_encryption), ("Database", database), ("Port", port),
          ("Disk space", disk), ("HTTPS", https), ("Python scripts", scripts_env), ("AI", ai_key)]


def run() -> list[dict]:
    out: list[dict] = []
    for name, fn in CHECKS:
        _check(out, name, fn)
    return out


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    res = run()
    if "--json" in argv:
        print(json.dumps(res, indent=1))
    else:
        mark = {"PASS": "[ OK ]", "WARN": "[WARN]", "FAIL": "[FAIL]"}
        print("\nTest Studio pre-flight check\n")
        for r in res:
            print(f"  {mark[r['status']]}  {r['check']:<28} {r['detail']}")
        fails = sum(r["status"] == "FAIL" for r in res)
        warns = sum(r["status"] == "WARN" for r in res)
        print(f"\n  {'READY' if not fails else 'NOT READY'}: {fails} fail, {warns} warning(s)\n")
    return 1 if any(r["status"] == "FAIL" for r in res) else 0


if __name__ == "__main__":
    sys.exit(main())
