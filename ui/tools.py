"""
Jitne kaam abhi batch file se hote the -- wahi UI se.

KYUN
----
Tester ko folder khol kar 20 bat file me se sahi wali dhoondhni padti thi,
aur output ek kaali khidki me aata tha jo band hote hi ud jata tha. Ab sab
kuch UI se chalta hai aur output wahin dikhta hai -- chalte hue.

HAR KAAM KE SAATH TEEN BAATEIN
------------------------------
  kya karta hai   -- saadhi bhasha me, taaki tester ko andaza na lagana pade
  kitni der       -- taaki wo intezaar kar sake ya chhod kar ja sake
  kya badalta hai -- data chhuta hai ya sirf padhta hai

Aakhri baat sabse zaroori hai. "Settings ON karo" wala kaam kisi ki asli
company ki settings badalta hai. Wo baat button ke saath likhi honi chahiye,
kisi dastavez me chhupi nahi.
"""
from __future__ import annotations

import os
import queue
import subprocess
import sys
import threading
import time
import uuid

from config.settings import ROOT

# ---------------------------------------------------------------- kaam

# safe   -- kuch nahi badalta, sirf padhta hai
# writes -- data ya settings badal sakta hai ("Allow writes" chahiye)
TOOLS = [
    {
        "id": "doctor", "order": 11, "name": "Health check",
        "cmd": ["-m", "framework.doctor"],
        "what": "Checks that everything is in place — Python, libraries, "
                "files, sign-in details, safety guards. No browser opens.",
        "mins": "10 sec", "risk": "safe", "group": "Checks", "order": 20,
    },
    {
        "id": "login", "order": 10, "name": "Login test",
        "cmd": ["-m", "framework.auth"],
        "what": "Signs in and stops there. Worth running before anything "
                "long — a bad password wastes 40 minutes otherwise.",
        "mins": "30 sec", "risk": "safe", "group": "Checks",
    },
    {
        "id": "crawler", "order": 1, "name": "Full UI crawl",
        "cmd": ["-m", "framework.run_crawler"],
        "what": "Opens every menu, submenu and page, and records every field "
                "on it — ids, labels, dropdown options. This is what makes "
                "writing tests possible without guessing field names.",
        "mins": "35–45 min", "risk": "safe", "group": "Mapping",
        "options": [
            {"flag": "--enable", "label": "Turn every setting on first",
             "risk": "writes",
             "note": "Many fields stay hidden until their setting is on. This "
                     "turns them on so the map comes out complete. The old "
                     "values are saved — run Restore settings afterwards."},
            {"flag": "--resume", "label": "Continue where it stopped",
             "note": "Use this if the last crawl was interrupted."},
        ],
        "args": [{"flag": "--minutes", "label": "Time limit (minutes)",
                  "default": "90", "note": "It stops on its own at this point."}],
    },
    {
        "id": "restore", "order": 2, "name": "Restore settings",
        "cmd": ["-m", "framework.restore_settings"],
        "what": "Puts back the settings the crawl turned on. Always run this "
                "afterwards — otherwise the company is left changed.",
        "mins": "2–3 min", "risk": "writes", "group": "Mapping",
    },
    {
        "id": "control_room", "order": 3, "name": "Read Control Room",
        "cmd": ["-m", "framework.control_room_check"],
        "what": "Reads all of the company's settings. This is how the agent "
                "knows which tests cannot run here, so it skips them "
                "instead of failing them.",
        "mins": "1–2 min", "risk": "safe", "group": "Mapping",
    },
    {
        "id": "scan_code", "order": 4, "name": "Source code scan",
        "cmd": ["-m", "framework.scan_code"],
        "what": "Reads field names and routes straight from the MargBooks "
                "source folder — no browser needed. Covers screens the "
                "crawler can never reach, like ones behind permissions.",
        "mins": "1–2 min", "risk": "safe", "group": "Mapping",
        "args": [{"flag": "", "label": "Full path to the folder",
                  "default": "", "required": True,
                  "note": r"for example D:\margbooks-frontend"}],
    },
    {
        "id": "screens", "order": 20, "name": "Screen check",
        "cmd": ["-m", "framework.screens_check"],
        "what": "Opens each screen one by one and reports which ones came "
                "up and which did not.",
        "mins": "5–8 min", "risk": "safe", "group": "Checks",
    },
    {
        "id": "pom", "order": 21, "name": "POM check",
        "cmd": ["-m", "framework.pom_check"],
        "what": "Exercises the read-only parts of the Item and Ledger lists "
                "— search, counts, rows. Changes nothing.",
        "mins": "3–4 min", "risk": "safe", "group": "Checks",
    },
    {
        "id": "dump_forms", "order": 22, "name": "Form dump",
        "cmd": ["-m", "framework.dump_forms"],
        "what": "Dumps the full HTML of each major form. Useful when a field "
                "cannot be found and you need to see what is actually "
                "on the page.",
        "mins": "4–6 min", "risk": "safe", "group": "Checks",
    },
    {
        "id": "window", "order": 23, "name": "Window fit check",
        "cmd": ["-m", "framework.window_check"],
        "what": "Checks the browser window fits the screen properly.",
        "mins": "20 sec", "risk": "safe", "group": "Checks",
    },
    {
        "id": "unit_tests", "order": 12, "name": "Agent self-test",
        "cmd": ["-m", "pytest", "tests/unit", "-q", "--no-header"],
        "what": "Runs the agent's own tests — no browser, about 15 seconds. "
                "Worth running after replacing any files.",
        "mins": "15 sec", "risk": "safe", "group": "Checks",
    },
]

BY_ID = {t["id"]: t for t in TOOLS}


def listing() -> dict:
    """
    UI ke liye -- bina cmd ke (wo andar ki baat hai).

    Kram jaan-boojh kar 'order' se hai, list ke kram se nahi. Crawler
    sabse upar hona chahiye -- wahi sabse zyada chalega. Health check
    zaroori hai par roz nahi chalta.
    """
    rows = sorted(TOOLS, key=lambda t: t.get("order", 99))
    return {"tools": [{k: v for k, v in t.items() if k != "cmd"}
                      for t in rows]}


# ---------------------------------------------------------------- chalana

JOBS: dict[str, dict] = {}
_lock = threading.Lock()


def start(tool_id: str, flags: list[str] | None = None,
          args: list[str] | None = None) -> dict:
    """
    Ek kaam shuru karo -- alag process me, taaki UI atke na.

    Ek waqt me ek hi kaam. Do browser ek saath kholna ya do baar login
    karna dono ko gira deta hai.
    """
    tool = BY_ID.get(tool_id)
    if not tool:
        return {"error": f"No job called '{tool_id}'"}

    with _lock:
        running = [j for j in JOBS.values() if j["status"] == "running"]
        if running:
            return {"error": f"'{running[0]['name']}' is still running. Let it finish, "
                             f"or stop it first."}

    cmd = [sys.executable] + tool["cmd"] + list(flags or []) + list(args or [])
    job_id = uuid.uuid4().hex[:8]
    job = {
        "id": job_id, "tool": tool_id, "name": tool["name"],
        "status": "running", "started": time.strftime("%H:%M:%S"),
        "t0": time.time(), "lines": [], "code": None, "proc": None,
    }
    with _lock:
        JOBS[job_id] = job

    threading.Thread(target=_run, args=(job, cmd), daemon=True).start()
    return {"job": job_id, "name": tool["name"]}


def _run(job: dict, cmd: list[str]):
    env = dict(os.environ)
    env["PYTHONUNBUFFERED"] = "1"      # warna output aakhir me ek saath aata hai
    env["PYTHONIOENCODING"] = "utf-8"
    try:
        p = subprocess.Popen(
            cmd, cwd=str(ROOT), env=env,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace", bufsize=1)
        job["proc"] = p
        for line in p.stdout:
            line = line.rstrip("\n")
            job["lines"].append(line)
            # Bahut lambi output me purani lines hata dete hain, warna
            # browser dheema ho jata hai
            if len(job["lines"]) > 4000:
                del job["lines"][:1000]
        p.wait()
        job["code"] = p.returncode
        # Tester ne KHUD roka ho to use "fail" mat kaho.
        #
        # stop() status 'stopped' kar deta hai, par process marte hi
        # returncode non-zero aata hai aur ye line use 'failed' se dhak
        # deti thi. UI par tester ko dikhta ki uska rokna 'fail' ho gaya --
        # jo jhooth hai.
        if job["status"] != "stopped":
            job["status"] = "done" if p.returncode == 0 else "failed"
    except Exception as e:  # noqa: BLE001
        job["lines"].append(f"!! could not start: {e}")
        if job["status"] != "stopped":
            job["status"] = "failed"
        job["code"] = -1
    finally:
        job["seconds"] = round(time.time() - job["t0"], 1)
        job["proc"] = None


def status(job_id: str, since: int = 0) -> dict:
    job = JOBS.get(job_id)
    if not job:
        return {"error": "job not found"}
    lines = job["lines"][since:]
    return {"id": job["id"], "name": job["name"], "status": job["status"],
            "code": job["code"], "started": job["started"],
            "seconds": job.get("seconds", round(time.time() - job["t0"], 1)),
            "lines": lines, "total": len(job["lines"])}


def stop(job_id: str) -> dict:
    """
    Chalta hua kaam rok do.

    Crawl 45 minute ka hota hai. Beech me galti dikhe to tester ko use
    rokne ka raasta milna chahiye -- warna wo browser hi band kar dega,
    aur adhoora data bach jayega.
    """
    job = JOBS.get(job_id)
    if not job:
        return {"error": "job not found"}
    p = job.get("proc")
    if not p:
        return {"status": job["status"], "note": "already finished"}
    try:
        p.terminate()
        job["lines"].append("-- stopped --")
        job["status"] = "stopped"
        return {"status": "stopped"}
    except Exception as e:  # noqa: BLE001
        return {"error": str(e)[:120]}


def recent(n: int = 10) -> dict:
    rows = sorted(JOBS.values(), key=lambda j: -j["t0"])[:n]
    return {"jobs": [{"id": j["id"], "name": j["name"], "status": j["status"],
                      "started": j["started"],
                      "seconds": j.get("seconds", 0),
                      "lines": len(j["lines"])} for j in rows]}
