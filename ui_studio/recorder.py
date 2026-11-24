"""
Record: start Playwright codegen on the tester's PC, watch its output file, stream the actions to the UI.

The command comes from Settings (default `python -m playwright codegen --target=playwright-test -o recorded.spec.ts`).
It is split into an argument list and started WITHOUT a shell, so no free text ever reaches a shell.
"""
from __future__ import annotations

import os
import re
import shlex
import shutil
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path

from config.settings import ROOT, settings
from ui_studio import state

SESSIONS: dict[str, dict] = {}
ALLOWED = {"python", "python.exe", "py", "py.exe", "npx", "npx.cmd", "playwright", "playwright.exe"}
TMP = ROOT / "artifacts" / "studio" / "recordings"


def build_command(url: str, out: Path, reuse_login: bool) -> list[str]:
    if not re.match(r"^https?://[^\s]+$", url or ""):
        raise ValueError("Start URL must start with http:// or https://")
    argv = shlex.split(state.load_settings()["codegen_cmd"], posix=(os.name != "nt"))
    if not argv or Path(argv[0]).name.lower() not in ALLOWED:
        raise ValueError("Codegen command must start with python, py, npx or playwright (see Settings > Recorder).")
    if "codegen" not in argv:
        raise ValueError("Codegen command must contain the word codegen.")
    if Path(argv[0]).name.lower() in ("python", "python.exe", "py", "py.exe"):
        argv[0] = sys.executable
    elif shutil.which(argv[0]):
        argv[0] = shutil.which(argv[0])
    i = argv.index("codegen")
    for flag in ("-o", "--output"):
        if flag in argv:
            j = argv.index(flag)
            del argv[j:j + 2]
    argv[i + 1:i + 1] = [url]
    argv += ["-o", str(out)]
    if reuse_login:
        if not settings.STORAGE_STATE.exists():
            raise ValueError("No saved login yet. Put USE_SAVED_SESSION=true in .env, press Test login in Settings "
                             "once, then tick this again. Or untick it and record the login too.")
        argv += [f"--load-storage={settings.STORAGE_STATE}"]
    return argv


def friendly(msg: str) -> str:
    low = msg.lower()
    if "executable doesn't exist" in low or "playwright install" in low:
        return "The Playwright browser is not installed. Run: python -m playwright install chromium"
    if "no module named" in low and "playwright" in low:
        return "Playwright is not installed in this Python. Run setup.bat first."
    return msg


def start(url: str, reuse_login: bool = False, login_test: bool = False) -> dict:
    if login_test and reuse_login:
        raise ValueError("A login test starts signed out: untick “reuse the saved login session”.")
    sid = uuid.uuid4().hex[:8]
    TMP.mkdir(parents=True, exist_ok=True)
    out = TMP / f"rec_{sid}.spec.ts"
    argv = build_command(url, out, reuse_login)
    proc = subprocess.Popen(argv, cwd=str(ROOT), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    s = {"id": sid, "proc": proc, "file": out, "url": url, "t0": time.time(), "msg": "", "stopped": False,
         "login_test": bool(login_test)}
    SESSIONS[sid] = s
    threading.Thread(target=_drain, args=(s,), daemon=True).start()
    return {"session": sid, "command": " ".join(shlex.quote(a) if " " in a else a for a in argv)}


def _drain(s: dict):
    tail = []
    for line in s["proc"].stdout:
        tail.append(line.decode("utf-8", "replace").rstrip())
        s["msg"] = "\n".join(tail[-6:])


def _secrets() -> list[str]:
    vals = [settings.PASSWORD, settings.PIN]
    try:
        from ui import envs
        vals.append((envs.apply_active() or {}).get("password"))
    except Exception:  # noqa: BLE001
        pass
    return [v for v in vals if v and len(v) > 3]


def redact(code: str) -> str:
    """Codegen writes whatever the tester typed. A password never stays in the script.

    The recorded login is swapped for login(page) first. MargBooks' password box is a
    bare getByRole('textbox') with no name, so looking for the word "password" alone
    let the real password through.
    """
    from ui_studio import script
    code = script.single_quotes(code)       # a re-formatted script ("...") reads like codegen's own ('...')
    if script.is_login_test(code):
        return redact_login_test(code)
    code = script.replace_login(code)
    secrets = _secrets()
    out = []
    for ln in code.split("\n"):
        if re.search(r"password", ln, re.I) and re.search(r"\.fill\(", ln):
            ln = re.sub(r"\.fill\((['\"]).*?\1\)", ".fill(process.env.MB_PASS!)", ln)
        for s in secrets:
            ln = ln.replace(s, "***")
        out.append(ln)
    return "\n".join(out)


def _users() -> list[str]:
    vals = [settings.USER]
    try:
        from ui import envs
        vals.append((envs.apply_active() or {}).get("user"))
    except Exception:  # noqa: BLE001
        pass
    return [v for v in vals if v and len(v) > 3]


def redact_login_test(code: str, extra_secrets: list[str] | None = None, extra_users: list[str] | None = None) -> str:
    """A login test keeps its login steps, so the values typed there stay too (a wrong password is the test's
    data). A known MargBooks password or user id never stays: it becomes process.env.MB_PASS! / MB_USER!, which
    the runner fills with its own login when the test runs (so it also works with every QA's own login)."""
    secrets = sorted({x for x in _secrets() + list(extra_secrets or []) if isinstance(x, str) and len(x) > 3},
                     key=len, reverse=True)
    users = sorted({x for x in _users() + list(extra_users or []) if isinstance(x, str) and len(x) > 3},
                   key=len, reverse=True)
    out = []
    for ln in code.split("\n"):
        for s in secrets:
            for qv in (f"'{s}'", f'"{s}"'):
                ln = ln.replace(qv, "process.env.MB_PASS!")
            ln = ln.replace(s, "***")                    # anywhere else (a URL, a comment): never kept
        for u in users:
            for qv in (f"'{u}'", f'"{u}"'):
                ln = ln.replace(qv, "process.env.MB_USER!")
        out.append(ln)
    return "\n".join(out)


_PY_CODE = re.compile(r"^\s*(from playwright|import playwright|def run\(|with sync_playwright|"
                      r"(?:page|browser|context)\.\w+\(.*\)\s*$)", re.M)


def paste(code, extra_secrets: list[str] | None = None, login_test: bool = False,
          extra_users: list[str] | None = None) -> dict:
    """Team mode Record: code the QA recorded on their own PC and pasted in. Checked and cleaned like a local
    recording: it must be Playwright TypeScript, and the login (with its password) becomes login(page)."""
    if not isinstance(code, str) or not code.strip():
        raise ValueError("Paste the code that codegen wrote first.")
    if not any(ln.strip().startswith("await ") for ln in code.split("\n")):
        if _PY_CODE.search(code):
            raise ValueError("This is Python code. Record with the TypeScript target: record.bat, or "
                             "python -m playwright codegen --target=playwright-test <MargBooks URL>. Then copy ALL the "
                             "code from the Playwright Inspector and paste it here.")
        raise ValueError("This is not Playwright TypeScript code: it has no lines that start with "
                         "'await page.'. Copy ALL the code from the Playwright Inspector (record.bat) and paste it here.")
    from ui_studio import script
    code = code.replace("\r\n", "\n")
    if login_test:
        code = script.mark_login_test(code)
    code = redact(code)
    if script.is_login_test(code):            # the QA's own login (team mode) becomes MB_PASS / MB_USER too
        code = redact_login_test(code, extra_secrets, extra_users)
    for sec in sorted({x for x in (extra_secrets or []) if isinstance(x, str) and len(x) > 3}, key=len, reverse=True):
        code = code.replace(sec, "***")
    return {"code": code, "actions": len(_actions(code)), "login_test": script.is_login_test(code)}


def describe(line: str) -> str:
    """One recorded line in words a tester understands."""
    ln = line.strip().rstrip(";")
    name = (re.search(r"name: '([^']+)'", ln) or re.search(r"(?:Placeholder|Label|Text)\('([^']+)'", ln)
            or re.search(r"locator\('([^']+)'", ln))
    what = name.group(1) if name else ""
    if ".goto(" in ln:
        return "Opened " + (re.search(r"goto\('([^']+)'", ln).group(1) if re.search(r"goto\('([^']+)'", ln) else "a page")
    if ".fill(" in ln:
        if re.search(r"password|'\(login\)'", ln, re.I):
            return "Typed password"
        v = re.search(r"\.fill\('([^']*)'", ln)
        return f"Typed “{v.group(1)}”" + (f" in {what}" if what else "") if v else "Typed a value"
    if ".click(" in ln:
        return "Clicked " + (what or "an element")
    if ".press(" in ln:
        return "Pressed " + (re.search(r"press\('([^']+)'", ln).group(1) if re.search(r"press\('([^']+)'", ln) else "a key")
    if "expect(" in ln:
        return "Checked " + (what or "something is visible")
    if "waitForTimeout" in ln:
        return "Waited"
    return ln[:60]


def _read(s: dict) -> str:
    try:
        return s["file"].read_text(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        return ""


def _actions(code: str) -> list[str]:
    return [ln for ln in code.split("\n") if ln.strip().startswith("await")]


def feed(sid: str, since: int = 0) -> dict:
    s = SESSIONS.get(sid)
    if not s:
        raise KeyError("recording session not found")
    code = _read(s)
    from ui_studio import script
    login = script.login_block(code)
    secrets = _secrets()
    acts = []
    for i, ln in enumerate(code.split("\n")):
        if not ln.strip().startswith("await"):
            continue
        if ".fill(" in ln and (i in login or any(x in ln for x in secrets)):
            ln = "await page.fill('(login)', '');"     # never show what was typed at login
        acts.append(ln)
    rc = s["proc"].poll()
    st = "recording" if rc is None and not s["stopped"] else ("failed" if rc not in (0, None) and not acts and not s["stopped"] else "stopped")
    return {"state": st, "actions": [{"n": i + 1, "text": describe(a)} for i, a in enumerate(acts) if i >= since],
            "next": len(acts), "message": friendly(s["msg"]) if st == "failed" else ""}


def stop(sid: str) -> dict:
    s = SESSIONS.get(sid)
    if not s:
        raise KeyError("recording session not found")
    s["stopped"] = True
    p = s["proc"]
    if p.poll() is None:
        time.sleep(0.6)             # let codegen flush its last action
        p.terminate()
        try:
            p.wait(5)
        except subprocess.TimeoutExpired:
            p.kill()
    code = _read(s)
    try:
        s["file"].unlink()
    except Exception:  # noqa: BLE001
        pass
    if not code.strip():
        raise ValueError("Nothing was recorded. " + (friendly(s["msg"]) or "Did the browser window open?"))
    if s.get("login_test"):
        from ui_studio import script
        code = script.mark_login_test(code)
    code = redact(code)
    return {"code": code, "actions": len(_actions(code)), "login_test": bool(s.get("login_test"))}
