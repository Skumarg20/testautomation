"""
Alag-alag kaam ke alag log -- aur run ka itihaas jo disk par rehta hai.

KYUN
----
Ab tak sab kuch ek hi jagah tha: live tape aur artifacts folder. Do dikkat
thin:

  1. Server band karte hi run ka itihaas UD JATA tha. "Pichhle hafte ye test
     pass hua tha ya nahi" -- iska koi jawab nahi tha.
  2. Sab log ek saath mile hue the. Scanner ki dikkat dhoondhni ho to AI aur
     test ke log beech me aate the.

Ab char alag log hain, aur har test ka aakhri natija disk par likha rehta hai.
"""
from __future__ import annotations

import json
import threading
import time
from pathlib import Path

from config.settings import ROOT

LOG_DIR = ROOT / "logs"
HISTORY = LOG_DIR / "execution_history.json"
_lock = threading.Lock()

KINDS = ("scanner", "ai", "generator", "execution")


def _path(kind: str) -> Path:
    if kind not in KINDS:
        kind = "execution"
    return LOG_DIR / f"{kind}.log"


def write(kind: str, operation: str, status: str = "ok",
          test_id: str = "", duration: float | None = None,
          error: str = "", **extra):
    """
    Ek line likho.

    Har line me wahi cheezein hain jo baad me dhoondhte waqt chahiye hoti
    hain: kab, kya kaam, kis test ka, kya haal, kitni der, aur kya galti.
    """
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    row = {
        "at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "operation": operation,
        "status": status,
    }
    if test_id:
        row["test"] = test_id
    if duration is not None:
        row["seconds"] = round(float(duration), 2)
    if error:
        row["error"] = str(error)[:400]
    row.update({k: v for k, v in extra.items() if v is not None})

    line = json.dumps(row, ensure_ascii=False)
    with _lock:
        try:
            with _path(kind).open("a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception:  # noqa: BLE001
            pass          # log likhne me dikkat se kaam nahi rukna chahiye


def tail(kind: str, n: int = 100) -> list[dict]:
    p = _path(kind)
    if not p.exists():
        return []
    try:
        lines = p.read_text(encoding="utf-8").strip().split("\n")[-n:]
    except Exception:  # noqa: BLE001
        return []
    out = []
    for l in lines:
        try:
            out.append(json.loads(l))
        except Exception:  # noqa: BLE001
            out.append({"at": "", "operation": l[:120], "status": "?"})
    return out


# ---------------------------------------------------------------- itihaas

def load_history() -> dict:
    if not HISTORY.exists():
        return {"tests": {}, "runs": []}
    try:
        d = json.loads(HISTORY.read_text(encoding="utf-8"))
        return d if "tests" in d else {"tests": {}, "runs": []}
    except Exception:  # noqa: BLE001
        return {"tests": {}, "runs": []}


def _save_history(d: dict):
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    HISTORY.write_text(json.dumps(d, indent=1, ensure_ascii=False),
                       encoding="utf-8")


def record_result(test_id: str, outcome: str, seconds: float = 0,
                  error: str = "", run_id: str = ""):
    """
    Ek test ka natija disk par likh do.

    Har test ka AAKHRI natija rakhte hain, aur uski pichhli paanch koshishein.
    Poora itihaas rakhne se file badhti jayegi aur kaam kuch nahi aayega --
    paanch se hi pata chal jata hai ki test hamesha girta hai ya kabhi-kabhi.
    """
    with _lock:
        d = load_history()
        row = d["tests"].setdefault(test_id, {"runs": []})
        entry = {"at": time.strftime("%Y-%m-%d %H:%M"), "outcome": outcome,
                 "seconds": round(seconds, 1), "run": run_id}
        if error:
            entry["error"] = str(error)[:200]
        row["last"] = entry
        row["runs"] = ([entry] + row.get("runs", []))[:5]
        row["total"] = row.get("total", 0) + 1
        if outcome == "passed":
            row["passed"] = row.get("passed", 0) + 1
        _save_history(d)


def record_run(run_id: str, results: list[dict], who: str = "",
               env: str = ""):
    """Poore run ka saaransh."""
    n = lambda o: sum(1 for r in results if r.get("outcome") == o)  # noqa: E731
    with _lock:
        d = load_history()
        d["runs"] = ([{
            "id": run_id, "at": time.strftime("%Y-%m-%d %H:%M"),
            "who": who, "env": env, "tests": len(results),
            "passed": n("passed"), "failed": n("failed"),
            "skipped": n("skipped"), "known_issue": n("known_issue"),
        }] + d.get("runs", []))[:50]
        _save_history(d)


def last_result(test_id: str) -> dict | None:
    return (load_history()["tests"].get(test_id) or {}).get("last")


def summary() -> dict:
    d = load_history()
    return {"tests_with_history": len(d["tests"]), "runs": len(d.get("runs", [])),
            "recent": d.get("runs", [])[:20]}
