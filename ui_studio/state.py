"""
Everything Test Studio remembers apart from the YAML tests themselves:
Studio settings, saved-test details (author, description, spec file), AI usage log and AI answer cache.
One small SQLite file (config/studio.db) + one JSON file (config/studio_settings.json). Never a password.
"""
from __future__ import annotations

import hashlib
import json
import re
import os
import sqlite3
import threading
import time
from contextlib import contextmanager
from pathlib import Path

from config.settings import ROOT

DB = Path(os.environ["STUDIO_DB"]) if os.environ.get("STUDIO_DB") else ROOT / "config" / "studio.db"
SETTINGS = ROOT / "config" / "studio_settings.json"

MODULES = ["Sale", "Purchase", "Inventory", "Accounts", "Masters", "Control Room", "Reports", "CRM"]
TRADES = ["Pharma Distributor", "Pharma Agent", "Pharma Retail", "FMCG", "Garment"]
DEFAULTS = {
    "trade_mode": "auto", "bulk": {"party": True, "item": True, "batch": True, "qty": True, "shot": False},
    "codegen_cmd": "python -m playwright codegen --target=playwright-test -o recorded.spec.ts",
    "out_dir": str(ROOT / "tests_ts"), "ai_mode": "local_first", "token_limit": 200000,
    "fix_attempts": 3, "test_company": False, "web_dir": "", "api_dir": "",
}


# ----------------------------------------------------------------- settings

def load_settings() -> dict:
    d = dict(DEFAULTS)
    try:
        d.update(json.loads(SETTINGS.read_text(encoding="utf-8")))
    except Exception:  # noqa: BLE001
        pass
    return d


def save_settings(new: dict) -> dict:
    d = load_settings()
    for k in DEFAULTS:
        if k in new:
            d[k] = new[k]
    d["token_limit"] = max(0, int(str(d["token_limit"]).replace(",", "") or 0))
    d["fix_attempts"] = max(0, min(3, int(d["fix_attempts"])))
    if d["ai_mode"] not in ("local_first", "always", "never"):
        raise ValueError("ai_mode must be local_first, always or never")
    SETTINGS.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS.write_text(json.dumps(d, indent=1), encoding="utf-8")
    return d


# ----------------------------------------------------------------------- db

def _migrate(con):
    """Columns added after the first release (old databases get them on first open)."""
    cols = {r[1] for r in con.execute("PRAGMA table_info(runs)")}
    if "run_by" not in cols:
        con.execute("ALTER TABLE runs ADD COLUMN run_by TEXT DEFAULT ''")
    # The failure in simple words, kept with the run's own error: the rules' summary when the run is saved, and the
    # AI's when a QA asks for it (JSON {"what", "why", "next", "side", "side_text"}; '' = not made yet).
    if "explain" not in cols:
        con.execute("ALTER TABLE runs ADD COLUMN explain TEXT DEFAULT ''")
    if "explain_ai" not in cols:
        con.execute("ALTER TABLE runs ADD COLUMN explain_ai TEXT DEFAULT ''")


_SCHEMA = """
CREATE TABLE IF NOT EXISTS ai_usage(ts REAL, month TEXT, feature TEXT, model TEXT, tin INT, tout INT, case_id TEXT);
CREATE TABLE IF NOT EXISTS ai_cache(k TEXT PRIMARY KEY, v TEXT, ts REAL);
CREATE TABLE IF NOT EXISTS tests(id TEXT PRIMARY KEY, name TEXT, module TEXT, author TEXT, priority TEXT,
    description TEXT, kind TEXT, created TEXT, lines TEXT, code TEXT, spec_file TEXT, seq INT);
CREATE TABLE IF NOT EXISTS runs(id TEXT PRIMARY KEY, test_id TEXT, name TEXT, module TEXT, author TEXT,
    at TEXT, passed INT, total INT, result TEXT, err TEXT, fail_at INT, steps TEXT, dir TEXT, ai_fixes INT,
    ts REAL);
"""
_ready: set[str] = set()          # database files whose tables were created/migrated by this process
_init_lock = threading.Lock()     # only the one-time schema set-up is serialised, never normal queries
_extra_schema: list = []          # other modules' table set-up (accounts), run once per database file


def add_schema(fn):
    """Register fn(con) to create more tables; it runs once per database file per process."""
    _extra_schema.append(fn)
    _ready.clear()


def _connect():
    con = sqlite3.connect(DB, timeout=30)          # run processes and the server share the file
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA busy_timeout=30000")
    return con


def _init(key: str):
    with _init_lock:
        if key in _ready and DB.exists():
            return
        DB.parent.mkdir(parents=True, exist_ok=True)
        con = _connect()
        try:
            try:   # WAL: readers (login, session checks) never wait for a run process that is writing
                con.execute("PRAGMA journal_mode=WAL")
            except sqlite3.Error:
                pass
            con.executescript(_SCHEMA)
            _migrate(con)
            for fn in _extra_schema:
                fn(con)
            con.commit()
        finally:
            con.close()
        _ready.add(key)


@contextmanager
def db():
    """One short-lived connection per use. No process-wide lock: SQLite (WAL, busy timeout) handles concurrency,
    so one request waiting for a write lock no longer makes every other request (login, session check) queue."""
    key = str(DB)
    if key not in _ready or not DB.exists():
        _init(key)
    con = _connect()
    try:
        yield con
        con.commit()
    finally:
        con.close()


# ------------------------------------------------------------------- tokens

def month() -> str:
    return time.strftime("%Y-%m")


def tokens_used() -> int:
    with db() as c:
        r = c.execute("SELECT COALESCE(SUM(tin+tout),0) n FROM ai_usage WHERE month=?", (month(),)).fetchone()
    return int(r["n"])


def tokens_report() -> dict:
    with db() as c:
        rows = c.execute("SELECT feature, SUM(tin+tout) n, COUNT(*) calls FROM ai_usage WHERE month=? GROUP BY feature",
                         (month(),)).fetchall()
    return {"month": tokens_used(), "limit": load_settings()["token_limit"],
            "by_feature": {r["feature"]: {"tokens": r["n"], "calls": r["calls"]} for r in rows}}


def tokens_for_case(case_id: str) -> int:
    with db() as c:
        r = c.execute("SELECT COALESCE(SUM(tin+tout),0) n FROM ai_usage WHERE case_id=?", (case_id,)).fetchone()
    return int(r["n"])


class AIBlocked(RuntimeError):
    """AI is off (mode "never"), has no key, or the monthly limit is reached. Local features keep working."""


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", str(s).lower()).strip()


def ai_json(feature: str, system: str, user: str, max_tokens: int = 1200, case_id: str = "") -> tuple[dict, int, bool]:
    """
    One AI call that obeys the token rules:
      cache by normalised input -> block on mode/limit/no key -> call -> log tokens.
    Returns (answer, tokens_used_now, from_cache). Tokens are estimated at 4 characters each because
    framework/ai.py does not return the provider's own count; the UI says so.
    """
    s = load_settings()
    key = hashlib.sha256(f"{feature}|{_norm(system)}|{_norm(user)}".encode()).hexdigest()
    with db() as c:
        hit = c.execute("SELECT v FROM ai_cache WHERE k=?", (key,)).fetchone()
    if hit:
        return json.loads(hit["v"]), 0, True
    if s["ai_mode"] == "never":
        raise AIBlocked("AI is switched off in Settings.")
    if s["token_limit"] and tokens_used() >= s["token_limit"]:
        raise AIBlocked("Monthly AI token limit reached. Local checks still work.")
    from framework import ai
    if not ai.available().get("active"):
        raise AIBlocked("No AI key is set. Add one in the old UI's Settings or in .env (GEMINI_API_KEY).")
    out = ai.ask_json(system, user, max_tokens)
    tin, tout = (len(system) + len(user)) // 4, len(json.dumps(out)) // 4
    with db() as c:
        c.execute("INSERT INTO ai_usage VALUES(?,?,?,?,?,?,?)",
                  (time.time(), month(), feature, ai.available().get("model", "") or ai.available().get("active", ""),
                   tin, tout, case_id))
        c.execute("INSERT OR REPLACE INTO ai_cache VALUES(?,?,?)", (key, json.dumps(out), time.time()))
    return out, tin + tout, False


# ------------------------------------------------------------ saved tests

def next_seq() -> int:
    with db() as c:
        r = c.execute("SELECT COALESCE(MAX(seq),0)+1 n FROM tests").fetchone()
    return int(r["n"])


def tc_id(seq: int) -> str:
    return f"TC-{seq:03d}"
