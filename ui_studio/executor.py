"""
Replay, AI auto-fix and Run for Test Studio.

The browser part is ONE function (_play). It uses the project's own login, safety
guards, netguard and StepRunner, exactly like ui/runner.py, and adds: per-step status,
per-step screenshots, video and trace. Everything around it (job state, fix loop,
database, reports) is plain Python and does not need a browser.
"""
from __future__ import annotations

import itertools
import re
import shutil
import threading
import time
import traceback
import uuid
from contextlib import contextmanager
from pathlib import Path

from config.settings import ROOT, settings
from ui_studio import memory, script, state, verify

JOBS: dict[str, dict] = {}
_browser_lock = threading.Lock()      # kept for callers/tests that used it; runs now take a slot (_slot)
RUNS_DIR = ROOT / "artifacts" / "studio"


# ================================================================== who may use a browser now

_slot_cv = threading.Condition()
_busy: dict = {"n": 0, "mb": {}, "co": set()}       # mb: MargBooks login -> Studio users running with it


class Stopped(Exception):
    """The run was stopped by its owner (or an admin)."""


class SignInFailed(RuntimeError):
    """MargBooks sign-in failed (str() is plain words for the QA)."""


class WorkerFailed(RuntimeError):
    """The run process ended with an error before it had a result (str() is that error, without a traceback)."""


def _plain_login_error(e: Exception | None) -> str:
    msg = str(e or "")
    first = msg.strip().splitlines()[0] if msg.strip() else "no reason given"
    company = str(getattr(settings, "COMPANY", "") or "").strip()
    if "Organisation List" in msg or "Organisation" in first:
        return (f"MargBooks login failed: the company {company or '(none set)'} did not open from the Organisation "
                "List (MargBooks was slow or the company is not in your list). Try again; if it keeps failing, "
                "check your MargBooks login in Settings.")
    if "PASS/PIN" in msg or "password" in msg.lower():
        return "MargBooks login failed: the password or PIN was not accepted. Check your MargBooks login in Settings."
    return f"MargBooks login failed: {first[:200]}. Try again; if it keeps failing, check your MargBooks login in Settings."


SIGN_IN_TRY_LIMIT = 150   # seconds one MargBooks sign-in try may take in all (its many waits are cut to this)


def _sign_in(ctx, on_log, tries: int = 2, stop: threading.Event | None = None):
    """Log in to MargBooks. A busy MargBooks sometimes does not open the company on the first try (the click on
    the Organisation List lands while the app is still loading), so one more try is made with a fresh page.
    Each try has a time limit (SIGN_IN_TRY_LIMIT) and ends at once when Stop is pressed: a hanging sign-in held
    the shared MargBooks login for 14 minutes, with other QAs' runs waiting behind it."""
    from framework.auth import login, LoginBlocked, LoginStopped, time_limit
    last = None
    for k in range(tries):
        if stop is not None and stop.is_set():
            raise Stopped("Stopped by the user while signing in.")
        if k:
            on_log(f"Signing in again, try {k + 1} of {tries}…")
        page = ctx.new_page()
        try:
            with time_limit(SIGN_IN_TRY_LIMIT, stop):
                return login(page)
        except LoginStopped as e:
            raise Stopped("Stopped by the user while signing in.") from e
        except LoginBlocked as e:
            last = e
            on_log(f"Sign-in try {k + 1} failed: {str(e).strip().splitlines()[0] if str(e).strip() else e!r}"
                   + (" Trying once more…" if k + 1 < tries else ""))
            try:
                page.close()
            except Exception:  # noqa: BLE001
                pass
    raise SignInFailed(_plain_login_error(last)) from last


def _session_alive(bp, app_ready) -> bool:
    """Is the app still open in this page? A busy server can take more than a few seconds to show the header
    again (the first check used 4 s and logged "Session ended" right after a good sign-in, and the needless
    second sign-in then landed on margbooks.com/login). Wait longer, and load the dashboard once before saying
    the session ended."""
    if app_ready(bp.page, 4000) or app_ready(bp.page, 20000):
        return True
    url = str(getattr(bp.page, "url", "") or "")
    if "/login" in url or "accounts." in url:
        return False
    try:
        bp.page.goto(f"{settings.BASE_URL.rstrip('/')}/dashboard", wait_until="domcontentloaded", timeout=60000)
    except Exception:  # noqa: BLE001
        return False
    return app_ready(bp.page, 30000)


def _case_company(case: dict) -> str:
    for st in case.get("steps") or []:
        if st.get("action") == "use_company" and st.get("value"):
            return str(st["value"]).strip().lower()
    return str(((case.get("ver") or {}).get("company")) or "").strip().lower()


_tickets = itertools.count()
_waiting: dict = {}          # ticket -> (MargBooks login, company) of runs waiting for a browser, oldest first


def _blocked(mb: str, co: str, me_: str) -> str:
    """Why a run with this login and company cannot have a browser now ('' = it can)."""
    from ui_studio import mode
    if _busy["n"] >= mode.MAX_BROWSERS:
        return "all browsers of the Studio are busy"
    if mb and _busy["mb"].get(mb):
        others = sorted({u for u in _busy["mb"][mb] if u and u != me_})
        return ("your other run is still using your MargBooks login" if not others
                else f"another run ({', '.join(others)}) is using the same MargBooks login")
    if co and co in _busy["co"]:
        return f"another run is using {co}"
    return ""


@contextmanager
def _slot(job: dict, case: dict):
    """A browser for this case. Waits while (a) all browsers of this machine are busy, (b) the same MargBooks
    login is in use (a second login of one user logs the first one out), (c) another run is in the same company
    (tests change that company's settings and data). Local mode: one browser at a time, as before."""
    from ui_studio import mode
    owner = job.get("_owner") or {}
    mb, me_ = owner.get("mb_user", ""), owner.get("username", "")
    co = _case_company(case)
    stop = job.get("_stop")
    t_wait = time.time()
    with _slot_cv:
        ticket = next(_tickets)
        _waiting[ticket] = (mb, co)
        try:
            while True:
                if stop is not None and stop.is_set():
                    job.pop("waiting", None)
                    raise Stopped("Stopped before it started.")
                why = _blocked(mb, co, me_)
                if not why:
                    # first come, first served: a run that started waiting earlier and could start now goes first
                    ahead = [w for t, w in _waiting.items() if t < ticket and not _blocked(*w, "")]
                    if (any((mb and w[0] == mb) or (co and w[1] == co) for w in ahead)
                            or _busy["n"] + len(ahead) >= mode.MAX_BROWSERS):
                        why = "runs started earlier go first"
                if not why:
                    break
                job["waiting"] = why
                job["title"] = "Waiting: " + why
                _slot_cv.wait(timeout=5)
        finally:
            _waiting.pop(ticket, None)
            _slot_cv.notify_all()
        _busy["n"] += 1
        if mb:
            _busy["mb"].setdefault(mb, []).append(me_)
        if co:
            _busy["co"].add(co)
        job.pop("waiting", None)
        # a run that waited, or one that never waited and still shows the "Queued" it was created with, now has a
        # browser: say so (a "Queued" title next to a running timer and REC mixes the two signals)
        if str(job.get("title", "")).startswith(("Waiting", "Queued")):
            job["title"] = job.get("next_title") or "Starting the browser…"
    job["waited"] = round(job.get("waited", 0) + time.time() - t_wait, 1)
    job["_t_start"] = time.time()                     # the run timer counts only time with a browser
    try:
        yield
    finally:
        job["_acc"] = job.get("_acc", 0.0) + time.time() - job.pop("_t_start", time.time())
        with _slot_cv:
            _busy["n"] -= 1
            if mb and mb in _busy["mb"]:
                try:
                    _busy["mb"][mb].remove(me_)
                except ValueError:
                    pass
                if not _busy["mb"][mb]:
                    del _busy["mb"][mb]
            _busy["co"].discard(co)
            _slot_cv.notify_all()


def run_seconds(job: dict) -> float:
    """Seconds this job has had a browser (time spent waiting in the queue is not counted)."""
    t = job.get("_acc", 0.0)
    if job.get("_t_start"):
        t += time.time() - job["_t_start"]
    return round(t, 1)


def _player(job: dict):
    """The browser runner for this job: in server mode a separate process with the owner's MargBooks login."""
    from ui_studio import mode
    owner = job.get("_owner")
    if not (mode.SERVER and owner):
        return _play
    return lambda cases, opts, on_step, on_log, stop=None: _play_isolated(cases, opts, on_step, on_log, owner, stop)


def _play_isolated(cases, opts, on_step, on_log, owner: dict, stop=None) -> list[dict]:
    import json
    import os
    import subprocess
    import sys
    from ui_studio import worker
    env = dict(os.environ, STUDIO_RUN_CREDS="1", MARGBOOKS_USER=owner.get("mb_user", ""),
               MARGBOOKS_PASS=owner.get("mb_password", ""), USE_SAVED_SESSION="false", HEADLESS="true",
               PYTHONIOENCODING="utf-8", PYTHONUNBUFFERED="1")
    # Stop is a signal, not a kill: the worker sees this file appear, stops at its next step and still runs the
    # test's clean-up steps and setting undo (the QA company is shared). The kill is only a fallback after
    # STOP_GRACE seconds, for a worker that does not finish.
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    stop_file = RUNS_DIR / f".stop-{uuid.uuid4().hex}"
    env["STUDIO_STOP_FILE"] = str(stop_file)
    proc = subprocess.Popen([sys.executable, "-m", "ui_studio.worker"], cwd=str(ROOT), env=env,
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, encoding="utf-8", errors="replace")
    proc.stdin.write(json.dumps({"cases": cases, "opts": opts}, default=str))
    proc.stdin.close()
    results = None
    done = threading.Lock()               # held by the reader once the run has ended: no stop file after that
    if stop is not None:
        def _watch():                     # Stop works even while the run prints nothing (a long wait in a step)
            while proc.poll() is None:
                if stop.wait(1):
                    if not done.acquire(blocking=False):
                        return
                    try:
                        if proc.poll() is None:
                            stop_file.write_text("stop", encoding="utf-8")
                    except Exception:  # noqa: BLE001
                        pass
                    finally:
                        done.release()
                    on_log("Stopping: the test stops at its next step; its clean-up steps still run.")
                    t_end = time.time() + STOP_GRACE
                    while proc.poll() is None and time.time() < t_end:
                        time.sleep(0.5)
                    if proc.poll() is None:
                        on_log(f"The run did not stop within {STOP_GRACE} s: ended it.")
                        try:
                            proc.kill()
                        except Exception:  # noqa: BLE001
                            pass
                    return
        threading.Thread(target=_watch, daemon=True).start()
    errs: list[dict] = []
    try:
        results = _read_worker(proc, worker.MARK, on_step, on_log, errs)
    finally:
        done.acquire()                    # waits for a stop file being written right now, blocks later writes
        for _ in range(20):           # Windows: a virus scanner may hold a just-written file for a moment
            try:
                stop_file.unlink(missing_ok=True)
                break
            except OSError:
                time.sleep(0.1)
    if results is None and stop is not None and stop.is_set():
        raise Stopped("Stopped while it was running.")
    if results is None and errs:                      # the worker said why (e.g. MargBooks sign-in failed)
        e = errs[-1]
        raise (SignInFailed if e.get("kind") == "SignInFailed" else WorkerFailed)(str(e.get("m") or "")[:600])
    if results is None:
        raise WorkerFailed(f"The run process stopped without a result (exit code {proc.returncode}).")
    return results


STOP_GRACE = 240         # seconds a stopped worker gets for its clean-up steps before it is ended


def _read_worker(proc, mark: str, on_step, on_log, errs: list | None = None):
    import json
    results = None
    for line in proc.stdout:
        if not line.startswith(mark):
            if line.strip():
                on_log(line.rstrip()[:400])
            continue
        try:
            ev = json.loads(line[len(mark):])
        except ValueError:
            continue
        if ev.get("ev") == "step":
            on_step(ev["ci"], ev["si"], ev["status"], ev.get("secs"), ev.get("shot"))
        elif ev.get("ev") == "log":
            on_log(ev.get("m", ""))
        elif ev.get("ev") == "result":
            results = ev.get("results")
        elif ev.get("ev") == "error" and errs is not None:
            errs.append(ev)
    proc.wait(timeout=60)
    return results


def _new_id(prefix: str) -> str:
    return f"{prefix}{uuid.uuid4().hex[:6]}"


def _log(job: dict, text: str):
    job["log"] = (job.get("log", "") + text + "\n")[-6000:]


def step_index(steps: list[dict], step: dict, default: int) -> int:
    """0-based place of `step` in the case. Clean-up steps run as a copy with always=False."""
    for k, s in enumerate(steps):
        if s is step:
            return k
    for k, s in enumerate(steps):
        if s.get("always") and {**s, "always": False} == step:
            return k
    for k, s in enumerate(steps):
        if s == step:
            return k
    return min(default, max(len(steps) - 1, 0))


_STEP_NO = re.compile(r"^\s*Step (\d+)\b")


def failed_index(err: str, st: dict, n: int) -> int:
    """The failing step: the number the StepRunner put in its error ("Step 3 failed: ...") when it has one, else
    the first step whose dispatch raised, else the last one that ran."""
    m = _STEP_NO.search(err or "")
    if m and 1 <= int(m.group(1)) <= n:
        return int(m.group(1)) - 1
    return st.get("fail", st.get("i", -1))


# ---------------------------------------------------------------- secrets never leave in a trace

_PW_JSON = re.compile(rb'("(?:password|passwd|pwd|pin|userpassword|mb_pass)"\s*:\s*")((?:[^"\\]|\\.)*)(")', re.I)
_PW_FORM = re.compile(rb'((?:^|[&?])(?:password|passwd|pwd|pin)=)([^&\s"]*)', re.I)


def trace_secrets(extra: list[str] | None = None) -> list[str]:
    """The MargBooks passwords this process knows: the run's own login and the shared environment's."""
    import os
    vals = [os.environ.get("MARGBOOKS_PASS", ""), getattr(settings, "PASSWORD", ""), getattr(settings, "PIN", "")]
    try:
        from ui import envs
        vals.append((envs.apply_active() or {}).get("password") or "")
    except Exception:  # noqa: BLE001
        pass
    vals += list(extra or [])
    return sorted({v for v in vals if isinstance(v, str) and len(v) >= 4}, key=len, reverse=True)


def scrub_bytes(data: bytes, secrets: list[str]) -> bytes:
    for s in secrets:
        for form in {s, json_escape(s)}:
            b = form.encode("utf-8")
            if b in data:
                data = data.replace(b, b"***")
    data = _PW_JSON.sub(lambda m: m.group(1) + (b"***" if m.group(2) else b"") + m.group(3), data)
    return _PW_FORM.sub(lambda m: m.group(1) + (b"***" if m.group(2) else b""), data)


def json_escape(s: str) -> str:
    import json
    return json.dumps(s)[1:-1]


_SKIP_EXT = (".jpeg", ".jpg", ".png", ".webm", ".woff", ".woff2")
_scrub_locks: dict[str, threading.Lock] = {}
_scrub_locks_guard = threading.Lock()
_clean: dict[str, tuple] = {}          # trace path -> (mtime_ns, size, secrets fingerprint) known to be clean
_FP_KEY = uuid.uuid4().bytes           # per process: the fingerprint of the secrets never leaves memory


def _secrets_fp(secrets: list[str]) -> str:
    import hashlib
    import hmac
    return hmac.new(_FP_KEY, repr(sorted(secrets)).encode("utf-8"), hashlib.sha256).hexdigest()


# A trace checked clean is marked on disk (trace.zip.clean), so the check survives a server restart and the run
# process, which scrubs the trace when it saves it, can tell the server "already clean". The marker holds the
# trace's size and mtime and, per password it was checked against, an HMAC of that password; the HMAC key is a
# random key kept sealed like the MargBooks passwords (DPAPI / Fernet), never a plain hash of a password.
_MARK_VERSION = 1
_FP_KEY_FILE = ROOT / "artifacts" / ".cache" / "trace_fp.key"
_fp_key_cache: dict = {}


def _disk_fp_key() -> bytes | None:
    """The shared HMAC key for clean markers (server and run processes use the same one); None: markers off."""
    if "k" in _fp_key_cache:
        return _fp_key_cache["k"]
    import base64
    import os
    key = None
    try:
        from ui_studio import accounts
        f = _FP_KEY_FILE
        if not f.exists():
            f.parent.mkdir(parents=True, exist_ok=True)
            sealed = accounts.seal(base64.b64encode(os.urandom(32)).decode())
            try:
                fd = os.open(str(f), os.O_WRONLY | os.O_CREAT | os.O_EXCL)
                with os.fdopen(fd, "w", encoding="utf-8") as fh:
                    fh.write(sealed)
            except FileExistsError:
                pass                                    # another process made it first: use theirs
        for _ in range(10):
            txt = f.read_text(encoding="utf-8").strip()
            if txt:
                key = base64.b64decode(accounts.unseal(txt))
                break
            time.sleep(0.1)
    except Exception:  # noqa: BLE001  (no DPAPI/Fernet here: keep the in-memory check only)
        key = None
    _fp_key_cache["k"] = key
    return key


def _secret_marks(secrets: list[str]) -> set[str] | None:
    import hashlib
    import hmac
    key = _disk_fp_key()
    if key is None:
        return None
    return {hmac.new(key, s.encode("utf-8"), hashlib.sha256).hexdigest()[:32] for s in secrets}


def _mark_file(p: Path) -> Path:
    return p.with_name(p.name + ".clean")


def _read_mark(p: Path, st) -> set[str] | None:
    """The passwords (as HMACs) this exact trace file was checked clean against, or None (no valid marker)."""
    import json
    try:
        m = json.loads(_mark_file(p).read_text(encoding="utf-8"))
        if m.get("v") == _MARK_VERSION and m.get("size") == st.st_size and m.get("mtime_ns") == st.st_mtime_ns:
            return set(m.get("checked") or [])
    except Exception:  # noqa: BLE001
        pass
    return None


def _write_mark(p: Path, marks: set[str] | None):
    import json
    import os
    if marks is None:
        return
    try:
        st = p.stat()
        tmp = _mark_file(p).with_name(f"{p.name}.clean.{os.getpid()}.{uuid.uuid4().hex[:6]}.tmp")
        tmp.write_text(json.dumps({"v": _MARK_VERSION, "size": st.st_size, "mtime_ns": st.st_mtime_ns,
                                   "checked": sorted(marks)}), encoding="utf-8")
        os.replace(tmp, _mark_file(p))
    except Exception:  # noqa: BLE001
        pass


def _has_any(p: Path, secrets: list[str]) -> bool:
    """Quick look for these passwords only (the password fields were already cleaned when the marker was written)."""
    import zipfile
    forms = [f.encode("utf-8") for s in secrets for f in {s, json_escape(s)}]
    if not forms:
        return False
    if not zipfile.is_zipfile(p):
        raw = p.read_bytes()
        return any(f in raw for f in forms)
    with zipfile.ZipFile(p) as zin:
        for info in zin.infolist():
            if info.filename.lower().endswith(_SKIP_EXT):
                continue
            data = zin.read(info.filename)
            if any(f in data for f in forms):
                return True
    return False


def _path_lock(p: Path) -> threading.Lock:
    with _scrub_locks_guard:
        return _scrub_locks.setdefault(str(p.resolve()).lower(), threading.Lock())


def scrub_trace(path, secrets: list[str] | None = None) -> bool:
    """Rewrite a Playwright trace.zip without any password: request bodies of the login calls, typed values and
    form fields. Returns True when something was removed. Images and video frames are copied as they are.

    The file is read first and rewritten only when it has something to remove (a clean trace is never rewritten),
    one call per file at a time, through a temp file with a unique name. A trace checked clean with the same
    secrets is not read again (downloads of an already-scrubbed trace start at once)."""
    import os
    import zipfile
    p = Path(path)
    if not p.exists():
        return False
    secrets = trace_secrets() if secrets is None else secrets
    fp = _secrets_fp(secrets)
    with _path_lock(p):
        st = p.stat()
        sig = (st.st_mtime_ns, st.st_size, fp)
        if _clean.get(str(p)) == sig:
            return False
        marks = _secret_marks(secrets)
        done = _read_mark(p, st) if marks is not None else None
        if done is not None:                           # checked before (this process, an earlier one or the run)
            missing = [x for x in secrets if not _secret_marks([x]) <= done]
            if not missing or not _has_any(p, missing):
                _clean[str(p)] = sig
                if missing:
                    _write_mark(p, done | marks)
                return False
        if not zipfile.is_zipfile(p):                 # not a trace Playwright wrote: clean the raw bytes
            raw = p.read_bytes()
            new = scrub_bytes(raw, secrets)
            if new != raw:
                p.write_bytes(new)
            st = p.stat()
            _clean[str(p)] = (st.st_mtime_ns, st.st_size, fp)
            _write_mark(p, marks)
            return new != raw
        with zipfile.ZipFile(p) as zin:                # pass 1: is there anything to remove at all?
            dirty = set()
            for info in zin.infolist():
                if info.filename.lower().endswith(_SKIP_EXT):
                    continue
                data = zin.read(info.filename)
                if scrub_bytes(data, secrets) != data:
                    dirty.add(info.filename)
        if dirty:
            tmp = p.with_name(f"{p.name}.{os.getpid()}.{uuid.uuid4().hex[:8]}.scrub.tmp")
            try:
                with zipfile.ZipFile(p) as zin, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
                    for info in zin.infolist():
                        data = zin.read(info.filename)
                        if info.filename in dirty:
                            data = scrub_bytes(data, secrets)
                        zout.writestr(info, data)
                for k in range(20):                    # a reader on Windows may hold the file a moment
                    try:
                        os.replace(tmp, p)
                        break
                    except PermissionError:
                        if k == 19:
                            raise
                        time.sleep(0.25)
            finally:
                try:
                    tmp.unlink()
                except FileNotFoundError:
                    pass
                except Exception:  # noqa: BLE001
                    pass
        st = p.stat()
        _clean[str(p)] = (st.st_mtime_ns, st.st_size, fp)
        _write_mark(p, marks)
        return bool(dirty)


# ================================================================== browser

SAVING_MSG = "Saving the trace and video"


def ffmpeg_ready() -> bool:
    """Video needs the ffmpeg that `python -m playwright install` downloads. Without it new_page() crashes."""
    import os
    roots = [os.environ.get("PLAYWRIGHT_BROWSERS_PATH"), os.path.join(os.environ.get("LOCALAPPDATA", ""), "ms-playwright"),
             os.path.expanduser("~/.cache/ms-playwright"), os.path.expanduser("~/Library/Caches/ms-playwright")]
    return any(r and Path(r).is_dir() and any(Path(r).glob("ffmpeg-*")) for r in roots)


def _play(cases: list[dict], opts: dict, on_step, on_log, stop: threading.Event | None = None) -> list[dict]:
    """
    Run cases in one browser. cases = [{"id","name","steps":[...],"destructive":bool}].
    on_step(case_index, step_index, status, secs, shot_path|None) is called live.
    Returns one result per case: {"outcome","error","failed_step","seconds","video","trace","shots":[]}.
    """
    from playwright.sync_api import sync_playwright
    from framework import safety, netguard
    from framework.auth import login, app_ready
    from framework.browser import launch
    from framework.test_env import EnvironmentNotReady
    from framework.step_runner import StepRunner, RunContext, StepFailed, TradeMismatch
    from framework.screens_check import ensure_neutral
    from framework.control_room import FeatureOff, SettingLocked
    from ui import envs

    envs.apply_active()
    if opts.get("video", True) and not ffmpeg_ready():
        opts = dict(opts, video=False)
        on_log("Video skipped: ffmpeg is not installed. Run: python -m playwright install chromium")
    out_dir = Path(opts["dir"])
    out_dir.mkdir(parents=True, exist_ok=True)
    settings.init_run(f"Studio {opts.get('label', '')}")
    safety.CLICK_LOG.clear()
    netguard.BLOCKED.clear()
    results: list[dict] = []
    with sync_playwright() as pw:
        browser, ctx = launch(pw, record_video=bool(opts.get("video", True)))
        try:
            on_log("Signing in...")
            bp = _sign_in(ctx, on_log, stop=stop)
            on_log("Signed in")
            # The trace starts AFTER the login: it keeps request bodies and typed values, and the login has the
            # MargBooks password in both. (A later re-login is scrubbed out of trace.zip below.)
            if opts.get("trace", True):
                ctx.tracing.start(screenshots=True, snapshots=True, sources=False)
            for ci, case in enumerate(cases):
                if stop is not None and stop.is_set():
                    break
                res = {"id": case["id"], "outcome": "passed", "error": None, "failed_step": -1,
                       "seconds": 0.0, "shots": []}
                results.append(res)
                steps = case["steps"]
                if case.get("destructive") and not settings.ALLOW_DESTRUCTIVE:
                    res.update(outcome="skipped", error="Not run: this test saves or changes data and “Allow tests that create or change data” is off in Settings. Turn it on to run it; writes are still allowed only inside the QA test companies (the safety guard stops any write in a real company).")
                    for i in range(len(steps)):
                        on_step(ci, i, "skip", 0, None)
                    continue
                if not _session_alive(bp, app_ready):
                    on_log("Session ended, signing in again")
                    try:
                        bp.page.close()             # the old page must not keep polling with the ended session
                    except Exception:  # noqa: BLE001
                        pass
                    bp = _sign_in(ctx, on_log, stop=stop)
                ensure_neutral(bp)
                runner = StepRunner(bp, RunContext())
                orig = runner._dispatch
                state_i = {"i": -1, "t0": 0.0, "depth": 0, "ran": set()}

                def dispatch(action, target, value, step, _ci=ci, _orig=orig, _st=state_i, _res=res, _bp=bp,
                             _steps=steps):
                    # Steps are numbered by their place in the case, not by how often _dispatch is called: an
                    # action may dispatch sub-steps, and clean-up steps run after a failure. Counting calls put
                    # the red mark on the wrong step ("Step 1 failed" shown at step 11).
                    if _st["depth"] > 0:
                        return _orig(action, target, value, step)
                    i = step_index(_steps, step, _st["i"] + 1)
                    _st["i"] = max(_st["i"], i)
                    _st["ran"].add(i)
                    if stop is not None and stop.is_set() and _st.get("stopped") is None:
                        if not step.get("optional"):
                            _st["stopped"] = i      # raised once: the clean-up steps that follow still run
                        raise Stopped("Stopped by the user.")
                    on_step(_ci, i, "doing", 0, None)
                    t0 = time.time()
                    _st["depth"] += 1
                    try:
                        r = _orig(action, target, value, step)
                    except BaseException:
                        _st["depth"] -= 1
                        if step.get("optional"):
                            on_step(_ci, i, "skip", round(time.time() - t0, 1), None)
                        else:
                            if "fail" not in _st:
                                # the screen AT the failure: the clean-up steps that follow close the bill
                                # (a screenshot taken after them only shows the dashboard)
                                try:
                                    fshot = out_dir / f"{case['id']}_FAIL.png"
                                    _bp.page.screenshot(path=str(fshot), timeout=4000)
                                    _res["fail_shot"] = fshot.name
                                except Exception:  # noqa: BLE001
                                    pass
                            _st.setdefault("fail", i)
                            on_step(_ci, i, "bad", round(time.time() - t0, 1), None)
                        raise
                    _st["depth"] -= 1
                    shot = None
                    if opts.get("shots", True):
                        try:
                            shot = out_dir / f"{case['id']}_step{i + 1:02d}.png"
                            _bp.page.screenshot(path=str(shot), timeout=4000)
                            _res["shots"].append(shot.name)
                        except Exception:  # noqa: BLE001
                            shot = None
                    on_step(_ci, i, "ok", round(time.time() - t0, 1), shot.name if shot else None)
                    return r
                runner._dispatch = dispatch

                def restart(_ci=ci, _st=state_i, _res=res, _n=len(steps)):
                    # shared test data was put back (framework.test_data): the test runs again from step 1
                    _st["i"] = -1
                    _st["ran"] = set()
                    _st.pop("fail", None)
                    _res.pop("fail_shot", None)
                    _res["data_repaired"] = True
                    on_log("Test data was used up: put it back, running the test again")
                    for j in range(_n):
                        on_step(_ci, j, "todo", None, None)
                runner.on_restart = restart
                t0 = time.time()
                try:
                    runner.run(steps)
                except (TradeMismatch, SettingLocked, FeatureOff) as e:
                    res.update(outcome="skipped", error=str(e)[:600])
                except EnvironmentNotReady as e:
                    res.update(outcome="blocked", error="Blocked - environment (not an app failure): " + str(e)[:900],
                               failed_step=failed_index(str(e), state_i, len(steps)))
                except StepFailed as e:
                    res.update(outcome="failed", error=str(e)[:1200], failed_step=failed_index(str(e), state_i, len(steps)))
                except BaseException as e:  # noqa: BLE001  (pytest.skip etc. raise Skipped)
                    if type(e).__name__ in ("Skipped", "Exit"):
                        res.update(outcome="skipped", error=str(e)[:600])
                    else:
                        res.update(outcome="failed", error=str(e)[:1200],
                                   failed_step=failed_index(str(e), state_i, len(steps)))
                if state_i.get("stopped") is not None:
                    res.update(outcome="skipped", failed_step=-1,
                               error=f"Stopped by the user at step {state_i['stopped'] + 1}; the rest was not run.")
                res["seconds"] = round(time.time() - t0, 1)
                if res["outcome"] == "failed":
                    fi = max(res["failed_step"], 0)
                    shot = out_dir / f"{case['id']}_FAIL.png"
                    try:
                        if not res.get("fail_shot"):          # no screenshot at the failing step itself
                            bp.page.screenshot(path=str(shot), timeout=4000)
                        res["shots"].append(shot.name)
                    except Exception:  # noqa: BLE001
                        pass
                    on_step(ci, fi, "bad", res["seconds"], shot.name)
                    for j in range(len(steps)):              # clean-up steps that ran keep their own result
                        if j != fi and j not in state_i["ran"]:
                            on_step(ci, j, "skip", 0, None)
                    if opts.get("stop_first"):
                        break
                else:
                    for j in range(len(steps)):
                        if j not in state_i["ran"]:
                            on_step(ci, j, "skip" if res["outcome"] in ("skipped", "blocked") else "ok", 0, None)
                ensure_neutral(bp)
                if state_i.get("stopped") is not None:
                    break
        finally:
            if opts.get("trace", True) or opts.get("video", True):
                on_log(SAVING_MSG)          # the Run screen says so (this can take a while on a busy machine)
            try:
                if opts.get("trace", True):
                    tz = out_dir / "trace.zip"
                    ctx.tracing.stop(path=str(tz))
                    scrub_trace(tz)
            except Exception:  # noqa: BLE001
                pass
            vpath = None
            try:
                vid = ctx.pages[0].video if ctx.pages else None
                ctx.close()
                if vid:
                    vpath = vid.path()
            except Exception:  # noqa: BLE001
                pass
            browser.close()
            if vpath and Path(vpath).exists():
                shutil.move(str(vpath), str(out_dir / "run.webm"))
    return results


# ================================================================= diagnose

def diagnose(err: str, step_text: str = "") -> dict:
    """Plain-words reason for a failure. A disabled field is a Control Room setting, not a code problem."""
    e = err or ""
    m = re.search(r"strict mode violation", e)
    if m:
        return {"plain": "More than one place on the screen matched, so the click was ambiguous.", "setting": ""}
    if re.search(r"disabled|not enabled|readonly", e, re.I):
        name = (re.search(r"(?:step \d+ failed: )?([\w .%]+?)(?: field)?\b", step_text or "").group(1)
                if step_text else "")
        setting = ""
        try:
            from framework import control_room
            key = control_room.find_by_phrase(name or "")
            if key:
                setting = key
        except Exception:  # noqa: BLE001
            pass
        txt = ("The field is disabled. " + (f"This depends on the Control Room setting “{setting}”, "
               "so it is a setting, not a code problem. Run “Learn the app” to turn trade settings on."
               if setting else "A Control Room setting may be switched off for this company."))
        return {"plain": txt, "setting": setting or "unknown"}
    if re.search(r"covered by|intercepts pointer", e, re.I):
        return {"plain": "Another window (for example the Batch window) opened and covered the next box.", "setting": ""}
    if re.search(r"Timeout|not found|nahi mila|waiting for", e, re.I):
        return {"plain": "The element was not found in time. Its locator may have changed.", "setting": ""}
    return {"plain": "The step failed. The exact message is below.", "setting": ""}


_LOC = re.compile(r"""locator\('((?:[^'\\]|\\.)*)'\)""")


def _memory_ok(line: str) -> bool:
    """An AI-written line may only use locators that exist in app memory (or none at all)."""
    sels = {f["sel"] for s in memory.build()["screens"].values() for f in s["fields"]}
    return all(script.unq(x) in sels for x in _LOC.findall(line))


def ai_fix(job: dict, fail_line: int, err: str) -> tuple[bool, str]:
    """Ask AI for a replacement of ONE line. Sends: the error, 3 lines around it, matching memory entries."""
    lines = job["code"].split("\n")
    if fail_line < 0 or fail_line >= len(lines):
        return False, "The failing line could not be located in the script."
    around = "\n".join(lines[max(0, fail_line - 3): fail_line + 4])
    words = set(re.findall(r"[A-Za-z]{3,}", lines[fail_line] + " " + err[:200]))
    fields = []
    for sname, s in memory.build()["screens"].items():
        for f in s["fields"]:
            if any(w.lower() in f["name"].lower() or w.lower() in f["sel"].lower() for w in words):
                fields.append(f"{sname} / {f['name']}: {f['sel']}")
    fields = fields[:12]
    try:
        ans, tok, cached = state.ai_json(
            "replay.fix",
            "You fix ONE failing Playwright line. Use only locators from the given list. "
            "Never change expected values or assertions. Reply JSON {\"line\":\"<the full replacement line>\","
            "\"why\":\"<one short sentence>\"}.",
            f"error: {err[:500]}\ncode around the failing line (line {fail_line - max(0, fail_line - 3) + 1}):\n{around}\n"
            f"known fields:\n" + "\n".join(fields), 500, job.get("case_id", ""))
    except Exception as e:  # noqa: BLE001
        return False, str(e)
    new = str((ans or {}).get("line", "")).rstrip()
    if not new.strip().startswith("await") or "expect(" in lines[fail_line] != ("expect(" in new):
        return False, "AI did not return a usable line, or it tried to change a check."
    if not new.startswith(" "):
        new = "  " + new
    if not _memory_ok(new):
        return False, "AI used a locator that is not in app memory, so the answer was rejected."
    job["tokens"]["ai"] += tok
    job["fixText"] = (ans or {}).get("why", "")
    job["fixedLines"].append(new.strip())
    lines[fail_line] = new
    job["code"] = "\n".join(lines)
    return True, new


# ==================================================================== replay

def start_replay(code: str, name: str, module: str, author: str, owner: dict | None = None) -> str:
    jid = _new_id("r")
    s = state.load_settings()
    JOBS[jid] = {"id": jid, "kind": "replay", "state": "queued", "attempt": 0, "max": s["fix_attempts"],
                 "aiFixes": 0, "steps": [], "err": None, "code": code, "fixedLines": [], "giveUp": False,
                 "tokens": {"local": 0, "ai": 0}, "log": "", "name": name, "module": module, "author": author,
                 "case_id": "", "fixText": "", "dir": str(RUNS_DIR / f"replay_{jid}"), "_owner": owner,
                 "created": time.time()}
    _prune_jobs()
    threading.Thread(target=_replay_thread, args=(jid,), daemon=True).start()
    return jid


def retry(jid: str) -> str:
    j = JOBS.get(jid)
    if not j:
        raise KeyError("replay not found")
    j.update(state="queued", giveUp=False, err=None, attempt=0, aiFixes=0)
    threading.Thread(target=_replay_thread, args=(jid,), daemon=True).start()
    return jid


def _step_text(st: dict) -> str:
    return st.get("note") or f"{st.get('action')} {st.get('target') or ''} {st.get('value') or ''}".strip()


def _replay_thread(jid: str, play=None):
    job = JOBS[jid]
    play = play or _player(job)
    try:
        while True:
            job["attempt"] += 1
            job["state"] = "running"
            conv = script.to_steps(job["code"])
            steps = conv["steps"]
            job["steps"] = [{"text": _step_text(s), "status": "todo", "secs": 0} for s in steps]
            if conv["unknown"] or not steps:
                u = conv["unknown"]
                job.update(state="failed", giveUp=True, err={
                    "plain": (f"{len(u)} line(s) in the script cannot be replayed." if u else "The script has no actions."),
                    "err": "\n".join(f"line {x['line']}: {x['text']}  → {x['why']}" for x in u),
                    "lineText": u[0]["text"] if u else "", "fixText": ""})
                return
            lines = job["code"].split("\n")

            def on_step(ci, si, status, secs, shot, _j=job):
                if 0 <= si < len(_j["steps"]):
                    _j["steps"][si].update(status=status, secs=secs)

            case = {"id": "REPLAY", "name": job["name"], "steps": steps,
                    "destructive": any(s.get("destructive") for s in steps) or _writes(steps)}
            with _slot(job, case):
                res = play([case],
                           {"dir": job["dir"], "label": "replay " + jid, "video": False, "shots": False, "trace": False},
                           on_step, lambda m: _log(job, m))[0]
            if res["outcome"] == "passed":
                job.update(state="passed", err=None)
                return
            if res["outcome"] == "skipped":
                job.update(state="failed", giveUp=True, err={"plain": res["error"] or "The test was skipped.",
                                                              "err": res["error"] or "", "lineText": "", "fixText": ""})
                return
            fi = res["failed_step"]
            st = steps[fi] if 0 <= fi < len(steps) else {}
            line_no = _locate(lines, st, conv)
            dg = diagnose(res["error"] or "", _step_text(st))
            from ui_studio.explain import explain
            job["err"] = {"plain": dg["plain"], "err": res["error"] or "", "lineText": lines[line_no].strip() if 0 <= line_no < len(lines) else "",
                          "fixText": "", "explain": explain(res["error"] or "", _step_text(st))}
            job["tokens"]["local"] += 1
            if dg["setting"]:
                job.update(state="failed", giveUp=True)       # a setting, not code: AI cannot fix it
                return
            if job["aiFixes"] >= job["max"]:
                job.update(state="failed", giveUp=True)
                return
            job["state"] = "fixing"
            ok, msg = ai_fix(job, line_no, res["error"] or "")
            if not ok:
                job["err"]["fixText"] = msg
                job.update(state="failed", giveUp=True)
                return
            job["aiFixes"] += 1
            job["err"]["fixText"] = job.get("fixText") or msg.strip()
    except Exception as e:  # noqa: BLE001
        tb = traceback.format_exc()[-900:]
        _log(job, tb)                    # for developers: the job log, not the QA's panel
        job.update(state="failed", giveUp=True, err={"plain": start_error(e, tb), "err": log_tail(job),
                                                      "lineText": "", "fixText": ""})


def log_tail(job: dict, n: int = 12) -> str:
    """The last lines of a job's run log, without Python tracebacks (what the QA sees under a failed replay)."""
    out, in_tb = [], False
    for ln in (job.get("log") or "").splitlines():
        if ln.startswith("Traceback (most recent call last)"):
            in_tb = True
            continue
        if in_tb:
            if ln.startswith((" ", "\t")) or not ln.strip():
                continue
            in_tb = False
            continue                     # the exception line itself: the heading already says it in plain words
        if ln.strip():
            out.append(ln)
    return "\n".join(out[-n:])


def start_error(e: Exception, tb: str = "") -> str:
    """Plain words for 'the browser part could not even start'."""
    if isinstance(e, (SignInFailed, WorkerFailed)) and str(e):
        return str(e)
    low = (str(e) + tb).lower()
    if "executable doesn't exist" in low or "playwright install" in low:
        return "The Playwright browser is not installed on this PC. Run: python -m playwright install chromium"
    if "no module named" in low and "playwright" in low:
        return "Playwright is not installed. Run setup.bat first."
    if "login" in low or "sign" in low or "password" in low:
        return "Could not sign in. Check the URL, user and password in Settings, then press Test login."
    return "Could not start the browser run."


def _writes(steps: list[dict]) -> bool:
    return any(s.get("action") in ("save_form", "set_party", "add_item", "bulk_sale_bills", "retail_bill") for s in steps)


def _locate(lines: list[str], step: dict, conv: dict) -> int:
    """Script line number (0-based) of the action that produced this step."""
    ln = step.get("_line")
    if ln:
        return ln - 1
    return -1


def replay_status(jid: str) -> dict:
    j = JOBS.get(jid)
    if not j:
        raise KeyError("replay not found")
    keys = ("state", "attempt", "max", "aiFixes", "steps", "err", "code", "fixedLines", "tokens", "giveUp", "log")
    out = {k: j[k] for k in keys}
    out["waiting"] = j.get("waiting", "")          # why it is still in the queue (DEPLOY.md section 5)
    if out["waiting"] and out["state"] == "running":
        out["state"] = "queued"
    return out


# ====================================================================== run

def start_run(ids: list[str], opts: dict, who: str = "", owner: dict | None = None) -> str:
    rid = _new_id("R-")
    JOBS[rid] = {"id": rid, "kind": "run", "state": "queued", "title": "Queued", "total": 0, "done": 0, "steps": [],
                 "current": None, "results": [], "seconds": 0, "who": who, "ids": ids, "opts": opts,
                 "dir": str(RUNS_DIR / f"run_{rid}"), "log": "", "_owner": owner, "created": time.time(),
                 "_stop": threading.Event()}
    _prune_jobs()
    threading.Thread(target=_run_thread, args=(rid,), daemon=True).start()
    return rid


def stop_run(rid: str, by: str = "") -> dict:
    """Stop a run: tests still waiting are not started, the test that is running stops at its next step (its
    clean-up steps still run, so the company is left as it was)."""
    j = JOBS.get(rid)
    if not j or j.get("kind") != "run":
        raise KeyError("run not found")
    if j.get("state") not in ("queued", "running"):
        return {"ok": True, "state": j.get("state")}
    j["_stop"] = j.get("_stop") or threading.Event()
    j["_stop"].set()
    j["stopped_by"] = by
    j["title"] = "Stopping…"
    with _slot_cv:
        _slot_cv.notify_all()
    return {"ok": True, "state": "stopping"}


def live_runs(viewer: dict | None) -> list[dict]:
    """Runs still going that this viewer may follow (their own; every run in local mode). A run that has a browser
    comes before one still waiting in the queue (after F5 the Run screen follows the first one, and its Stop must
    stop the run that is really running), newest first within each group."""
    out = [j for j in JOBS.values() if j.get("kind") == "run" and j.get("state") in ("queued", "running")
           and can_see(j["id"], viewer)
           and (viewer is None or (j.get("_owner") or {}).get("username") in (None, "", viewer.get("username")))]

    def _waits(j):
        return j.get("state") == "queued" or bool(j.get("waiting"))
    out.sort(key=lambda j: (_waits(j), -j.get("created", 0)))
    return [{"id": j["id"], "title": j.get("title", ""), "video": bool((j.get("opts") or {}).get("video", True)),
             "state": "queued" if _waits(j) else "running"} for j in out]


def _run_thread(rid: str, play=None):
    from ui_studio import tests
    job = JOBS[rid]
    play = play or _player(job)
    stop = job.setdefault("_stop", threading.Event())
    try:
        cases = tests.load_cases(job["ids"])
        job.update(state="running", total=len(cases))
        shown = {"ci": -1}

        def on_step(ci, si, status, secs, shot):
            if shown["ci"] != ci:
                shown["ci"] = ci
                c = cases[ci]
                job["current"] = {"id": c["id"], "name": c["name"]}
                job["title"] = f"{c['display_id']} · {c['name']}"
                job["steps"] = [{"text": _step_text(s), "status": "todo", "secs": 0} for s in c["steps"]]
                job.pop("phase", None)
            job.pop("note", None)                     # the steps now say what is happening
            if 0 <= si < len(job["steps"]):
                job["steps"][si].update(status=status, secs=secs)
            if shot:                                  # live view on the Run screen: the newest step screenshot
                job["shot"] = str(Path(job["dir"]) / cases[ci]["id"] / shot)
                job["shot_n"] = job.get("shot_n", 0) + 1
            job["seconds"] = run_seconds(job)
        o = {"dir": job["dir"], "label": rid, "video": job["opts"].get("video", True),
             "shots": job["opts"].get("shots", True), "trace": job["opts"].get("bugpack", True),
             "stop_first": job["opts"].get("stop_first", False)}
        # one browser run per test keeps each test's steps, video and trace separate
        all_res = []
        for ci, c in enumerate(cases):
            if stop.is_set():
                break
            sub = dict(o, dir=str(Path(job["dir"]) / c["id"]))
            job["next_title"] = f"{c['display_id']} · {c['name']} (starting the browser…)"
            job["current"] = None                     # no step of this case runs yet (the screen shows the note)
            job["steps"] = []
            if not str(job.get("title", "")).startswith(("Waiting", "Queued")):
                job["title"] = job["next_title"]
            try:
                with _slot(job, c):
                    shown["ci"] = -1
                    r = _call_play(play, [c], sub, lambda _ci, si, st, sc, sh, _real=ci: on_step(_real, si, st, sc, sh),
                                   lambda m: _run_log(job, m), stop)
            except Stopped:
                break
            finally:
                job.pop("phase", None)
                job.pop("note", None)
            res = r[0] if r else {"outcome": "failed", "error": "No result", "failed_step": 0, "shots": [], "seconds": 0}
            n = len(c["steps"])
            passed = sum(1 for s in job["steps"] if s["status"] == "ok") if shown["ci"] == ci else (n if res["outcome"] == "passed" else 0)
            record = _save_run(job, c, res, [dict(s) for s in job["steps"]], passed)
            job["results"].append(record)
            job["done"] += 1
            all_res.append(res)
            if res["outcome"] == "failed" and o["stop_first"]:
                break
        if stop.is_set():
            left = len(cases) - job["done"]
            job.update(state="stopped", title=f"Run stopped{' by ' + job['stopped_by'] if job.get('stopped_by') else ''}"
                       + (f" · {left} test{'s' if left != 1 else ''} not run" if left else ""), seconds=run_seconds(job))
        else:
            job.update(state="done", title="Run finished", seconds=run_seconds(job))
    except Exception as e:  # noqa: BLE001
        tb = traceback.format_exc()[-900:]
        job.update(state="error", title="Run stopped: " + start_error(e, tb), seconds=run_seconds(job))
        _log(job, tb)
    finally:
        job.pop("waiting", None)


def _run_log(job: dict, m: str):
    """The run log, plus what the Run screen shows after the last step (saving the trace and video)."""
    _log(job, m)
    if str(m).startswith(SAVING_MSG):
        job["phase"] = "saving"
    elif str(m).startswith(_NOTE_PREFIXES):
        job["note"] = str(m)[:300]


# Run-log lines the Run screen shows while no step runs (signing in, stopping): without them a run hanging in the
# sign-in only showed "(starting the browser…)" with a running timer for 14 minutes.
_NOTE_PREFIXES = ("Signing in", "Signed in", "Session ended", "Sign-in try", "Stopping", "The run did not stop",
                  "Video skipped")


def _call_play(play, cases, opts, on_step, on_log, stop):
    """Players take an optional stop event (test doubles may not)."""
    import inspect
    try:
        params = inspect.signature(play).parameters.values()
        takes = any(p.kind == p.VAR_POSITIONAL for p in params) or len(list(params)) >= 5
    except (TypeError, ValueError):
        takes = False
    return play(cases, opts, on_step, on_log, stop) if takes else play(cases, opts, on_step, on_log)


def _save_run(job: dict, c: dict, res: dict, steps: list[dict], passed: int) -> dict:
    import json
    seq = _next_run_seq()
    rid = f"R-{seq:04d}"
    result = {"passed": "Pass", "failed": "Fail", "skipped": "Skip", "blocked": "Blocked"}[res["outcome"]]
    fa = res.get("failed_step", -1)
    for k, s in enumerate(steps):             # only finished statuses are stored ("doing" is the live screen's)
        if s["status"] == "doing":
            s["status"] = "bad" if res["outcome"] == "failed" and k == fa else "skip"
        if s["status"] == "todo":
            s["status"] = "skip"
    row = {"id": rid, "test_id": c["display_id"], "name": c["name"], "module": c["module"], "author": c["author"],
           "at": time.strftime("%d-%b-%Y %H:%M"), "passed": passed if res["outcome"] != "passed" else len(steps),
           "total": len(steps), "result": result,
           "err": res.get("error") or ("Note: test data this test needs had been used up by other tests; Studio put "
                                       "it back and ran the test again." if res.get("data_repaired") else ""),
           "fail_at": res.get("failed_step", -1), "steps": json.dumps(steps),
           "dir": str(Path(job["dir"]) / c["id"]), "ai_fixes": 0, "ts": time.time(),
           "run_by": (job.get("_owner") or {}).get("username") or job.get("who") or ""}
    # the failure in simple words is stored with the run's real error, so every report shows the same summary
    from ui_studio.explain import explain
    fa = row["fail_at"] if isinstance(row["fail_at"], int) else -1
    summary = explain(row["err"], steps[fa].get("text", "") if 0 <= fa < len(steps) else "", result)
    row["explain"] = json.dumps(summary, ensure_ascii=False) if summary else ""
    with state.db() as con:
        con.execute("INSERT OR REPLACE INTO runs(id,test_id,name,module,author,at,passed,total,result,err,fail_at,steps,"
                    "dir,ai_fixes,ts,run_by,explain) VALUES(:id,:test_id,:name,:module,:author,:at,:passed,:total,"
                    ":result,:err,:fail_at,:steps,:dir,:ai_fixes,:ts,:run_by,:explain)", row)
    return {"run_id": rid, "test": c["display_id"], "result": result, "passed": row["passed"], "total": row["total"],
            "err": row["err"], "failAt": row["fail_at"], "explain": summary}


def _next_run_seq() -> int:
    with state.db() as con:
        r = con.execute("SELECT COALESCE(MAX(CAST(SUBSTR(id,3) AS INTEGER)),0)+1 n FROM runs").fetchone()
    return int(r["n"])


def _prune_jobs(keep_hours: float = 12):
    """Finished jobs stay in memory for the Run screen; drop the ones older than keep_hours."""
    now = time.time()
    for k in [k for k, j in list(JOBS.items())
              if j.get("state") in ("done", "error", "passed", "failed", "stopped") and now - j.get("created", now) > keep_hours * 3600]:
        JOBS.pop(k, None)


def can_see(job_id: str, viewer: dict | None) -> bool:
    """Server mode: a run or replay belongs to who started it (admins see all)."""
    j = JOBS.get(job_id)
    if not j or viewer is None:
        return bool(j)
    owner = (j.get("_owner") or {}).get("username")
    return not owner or owner == viewer.get("username") or viewer.get("role") == "admin"


def queue() -> dict:
    """What the browsers are doing now (Run screen / admin)."""
    from ui_studio import mode
    running = [{"id": j["id"], "kind": j.get("kind"), "by": (j.get("_owner") or {}).get("username", ""),
                "title": j.get("title", ""), "waiting": j.get("waiting", "")}
               for j in JOBS.values() if j.get("state") in ("queued", "running", "fixing")]
    return {"max_browsers": mode.MAX_BROWSERS, "busy": _busy["n"], "jobs": running}


def run_status(rid: str) -> dict:
    j = JOBS.get(rid)
    if not j:
        raise KeyError("run not found")
    out = {k: j[k] for k in ("state", "title", "total", "done", "steps", "current", "results", "seconds", "log")}
    out["shot_n"] = j.get("shot_n", 0)
    out["waiting"] = j.get("waiting", "")          # why it waits (the Run screen shows it; DEPLOY.md section 5)
    out["waited"] = j.get("waited", 0)
    out["phase"] = j.get("phase", "") if j.get("state") == "running" else ""    # "saving": after the last step
    if j.get("state") in ("queued", "running"):
        out["seconds"] = run_seconds(j)            # live, and without the time spent waiting
    if out["waiting"] and out["state"] == "running":
        out["state"] = "queued"
    out["stopping"] = bool(j.get("_stop") and j["_stop"].is_set() and j.get("state") in ("queued", "running"))
    out["note"] = j.get("note", "") if j.get("state") == "running" else ""   # what happens while no step runs
    return out


def run_shot(rid: str) -> Path:
    """The newest step screenshot of a run (Run screen live view)."""
    j = JOBS.get(rid)
    p = Path(j["shot"]) if j and j.get("shot") else None
    if not p or not p.exists() or p.suffix.lower() != ".png":
        raise KeyError("no screenshot yet")
    root = Path(j["dir"]).resolve()
    if root not in p.resolve().parents:
        raise KeyError("no screenshot yet")
    return p
