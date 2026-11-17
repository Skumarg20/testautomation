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


def start(url: str, reuse_login: bool = False) -> dict:
    sid = uuid.uuid4().hex[:8]
    TMP.mkdir(parents=True, exist_ok=True)
    out = TMP / f"rec_{sid}.spec.ts"
    argv = build_command(url, out, reuse_login)
    proc = subprocess.Popen(argv, cwd=str(ROOT), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    s = {"id": sid, "proc": proc, "file": out, "url": url, "t0": time.time(), "msg": "", "stopped": False}
    SESSIONS[sid] = s
    threading.Thread(target=_drain, args=(s,), daemon=True).start()
    return {"session": sid, "command": " ".join(shlex.quote(a) if " " in a else a for a in argv)}


def _drain(s: dict):
    tail = []
    for line in s["proc"].stdout:
        tail.append(line.decode("utf-8", "replace").rstrip())
        s["msg"] = "\n".join(tail[-6:])


def redact(code: str) -> str:
    """Codegen writes whatever the tester typed. A password never stays in the script."""
    out = []
    for ln in code.split("\n"):
        if re.search(r"password", ln, re.I) and re.search(r"\.fill\(", ln):
            ln = re.sub(r"\.fill\((['\"]).*?\1\)", ".fill(process.env.MB_PASS!)", ln)
        out.append(ln)
    return "\n".join(out)


def describe(line: str) -> str:
    """One recorded line in words a tester understands."""
    ln = line.strip().rstrip(";")
    name = (re.search(r"name: '([^']+)'", ln) or re.search(r"(?:Placeholder|Label|Text)\('([^']+)'", ln)
            or re.search(r"locator\('([^']+)'", ln))
    what = name.group(1) if name else ""
    if ".goto(" in ln:
        return "Opened " + (re.search(r"goto\('([^']+)'", ln).group(1) if re.search(r"goto\('([^']+)'", ln) else "a page")
    if ".fill(" in ln:
        if re.search(r"password", ln, re.I):
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
    acts = _actions(code)
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
    code = redact(code)
    return {"code": code, "actions": len(_actions(code))}
