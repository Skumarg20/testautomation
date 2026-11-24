"""
Feedback from the QA team: a problem with a test case, a failed run, a replay, a Verify suggestion, a line the Write
screen does not understand, a login problem, or any idea. Each entry keeps where it came from (test, run, failed
step, error) so the admin can open it and fix it, then sets a status and a reply the QA sees.

Stored in the Studio database (state.db), table `feedback`. Passwords never stay in it: known MargBooks passwords
in the text, error or context are replaced by *** when it is saved.
"""
from __future__ import annotations

import json
import time

from ui_studio import state

KINDS = {
    "app_bug": "App bug (MargBooks itself is wrong)",
    "test_wrong": "Test case is wrong (steps or expected result)",
    "studio": "Studio / runner problem (the test is right, the tool failed)",
    "data": "Test data or company setup (stock, setting, party...)",
    "login": "Login or access problem",
    "idea": "Suggestion or new feature",
}
PLACES = {
    "general": "Feedback button", "run": "Run screen", "report": "Reports", "case": "Test cases",
    "replay": "Record / replay", "verify": "Verify suggestion", "write": "Write screen", "login": "My MargBooks login",
}
STATUSES = {"open": "Open", "in_progress": "In progress", "fixed": "Fixed", "wont_fix": "Won't fix"}
LIVE = ("open", "in_progress")                 # still being looked at: shown as a known issue on the test
MAX_TEXT, MAX_FIELD, MAX_CTX = 5000, 2000, 30


def _schema(con):
    con.execute("""CREATE TABLE IF NOT EXISTS feedback(
        id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL, at TEXT, by_user TEXT, by_name TEXT, kind TEXT, place TEXT,
        test TEXT, run TEXT, step TEXT, error TEXT, text TEXT, context TEXT, env TEXT,
        status TEXT DEFAULT 'open', reply TEXT DEFAULT '', replied_by TEXT DEFAULT '', updated TEXT DEFAULT '')""")
    con.execute("CREATE INDEX IF NOT EXISTS feedback_test ON feedback(test)")


state.add_schema(_schema)


class FeedbackError(ValueError):
    """Something the QA can fix in the form (sent back as 400)."""


def _secrets(extra: list[str] | None = None) -> list[str]:
    try:
        from ui_studio import recorder
        vals = recorder._secrets()
    except Exception:  # noqa: BLE001
        vals = []
    return sorted({v for v in vals + list(extra or []) if isinstance(v, str) and len(v) > 3}, key=len, reverse=True)


def _clean(v, limit: int, secrets: list[str]) -> str:
    if v is None:
        return ""
    if not isinstance(v, (str, int, float)):
        raise FeedbackError("Feedback fields must be text.")
    s = str(v).replace("\r\n", "\n").strip()[:limit]
    for sec in secrets:
        s = s.replace(sec, "***")
    return s


def _env() -> str:
    try:
        from ui import envs
        e = envs.apply_active() or {}
        return f"{str(e.get('app_url') or '').replace('https://', '')} · {e.get('company') or ''}".strip(" ·")
    except Exception:  # noqa: BLE001
        return ""


def add(b: dict, by_user: str = "", by_name: str = "", extra_secrets: list[str] | None = None) -> dict:
    """Save one feedback. b: kind, place, text, and optional test, run, step, error, context ({name: text})."""
    if not isinstance(b, dict):
        raise FeedbackError("Send the feedback as a JSON object.")
    kind = b.get("kind") or ""
    if kind not in KINDS:
        raise FeedbackError("Choose what kind of problem it is.")
    place = b.get("place") or "general"
    if place not in PLACES:
        place = "general"
    sec = _secrets(extra_secrets)
    text = _clean(b.get("text"), MAX_TEXT, sec)
    if len(text) < 5:
        raise FeedbackError("Write a few words about the problem (what you did, what you saw).")
    ctx = b.get("context") or {}
    if not isinstance(ctx, dict):
        raise FeedbackError("“context” must be an object.")
    ctx = {str(k)[:40]: _clean(v, MAX_FIELD, sec) for k, v in list(ctx.items())[:MAX_CTX]
           if isinstance(v, (str, int, float)) and str(v).strip()}
    row = (time.time(), time.strftime("%d-%b-%Y %H:%M"), (by_user or "")[:80], (by_name or by_user or "Tester")[:80],
           kind, place, _clean(b.get("test"), 80, sec), _clean(b.get("run"), 80, sec), _clean(b.get("step"), 400, sec),
           _clean(b.get("error"), MAX_FIELD, sec), text, json.dumps(ctx, ensure_ascii=False), _env()[:200])
    with state.db() as c:
        cur = c.execute("""INSERT INTO feedback(ts, at, by_user, by_name, kind, place, test, run, step, error, text,
                           context, env) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""", row)
        fid = cur.lastrowid
    return {"id": fid, "ref": ref(fid)}


def ref(fid: int) -> str:
    return f"FB-{int(fid):04d}"


def _row(r) -> dict:
    try:
        ctx = json.loads(r["context"] or "{}")
    except ValueError:
        ctx = {}
    return {"id": r["id"], "ref": ref(r["id"]), "at": r["at"], "ts": r["ts"], "by": r["by_name"],
            "byUser": r["by_user"], "kind": r["kind"], "kindName": KINDS.get(r["kind"], r["kind"]),
            "place": r["place"], "placeName": PLACES.get(r["place"], r["place"]), "test": r["test"], "run": r["run"],
            "step": r["step"], "error": r["error"], "text": r["text"], "context": ctx, "env": r["env"],
            "status": r["status"], "statusName": STATUSES.get(r["status"], r["status"]), "reply": r["reply"],
            "repliedBy": r["replied_by"], "updated": r["updated"]}


def list_feedback(viewer_user: str | None = None, status: str = "", kind: str = "", q: str = "",
                  limit: int = 500) -> dict:
    """viewer_user: only this user's own feedback (a QA in team mode); None = all (an admin, or the local Studio)."""
    sql, args = "SELECT * FROM feedback WHERE 1=1", []
    if viewer_user is not None:
        sql += " AND by_user=?"
        args.append(viewer_user)
    if status == "live":
        sql += " AND status IN ('open','in_progress')"
    elif status in STATUSES:
        sql += " AND status=?"
        args.append(status)
    if kind in KINDS:
        sql += " AND kind=?"
        args.append(kind)
    if q:
        like = f"%{q.strip()[:80]}%"
        sql += " AND (text LIKE ? OR test LIKE ? OR run LIKE ? OR error LIKE ? OR by_name LIKE ?)"
        args += [like] * 5
    sql += " ORDER BY id DESC LIMIT ?"
    args.append(max(1, min(int(limit or 500), 2000)))
    with state.db() as c:
        rows = [_row(r) for r in c.execute(sql, args)]
        counts = {s: 0 for s in STATUSES}
        cs = "SELECT status, COUNT(*) n FROM feedback" + (" WHERE by_user=?" if viewer_user is not None else "") \
            + " GROUP BY status"
        for r in c.execute(cs, [viewer_user] if viewer_user is not None else []):
            counts[r["status"]] = r["n"]
    return {"items": rows, "counts": counts, "kinds": KINDS, "statuses": STATUSES, "places": PLACES}


def update(fid, status: str = "", reply=None, by_name: str = "") -> dict:
    """Admin: change the status and/or write a reply the QA sees."""
    try:
        fid = int(fid)
    except (TypeError, ValueError):
        raise FeedbackError("Which feedback? The id is missing.") from None
    if status and status not in STATUSES:
        raise FeedbackError("Unknown status.")
    if reply is not None and not isinstance(reply, str):
        raise FeedbackError("“reply” must be text.")
    with state.db() as c:
        r = c.execute("SELECT * FROM feedback WHERE id=?", (fid,)).fetchone()
        if not r:
            raise KeyError("feedback not found")
        new_status = status or r["status"]
        new_reply = r["reply"] if reply is None else _clean(reply, MAX_TEXT, _secrets())
        c.execute("UPDATE feedback SET status=?, reply=?, replied_by=?, updated=? WHERE id=?",
                  (new_status, new_reply, (by_name or "")[:80] if (reply is not None or status) else r["replied_by"],
                   time.strftime("%d-%b-%Y %H:%M"), fid))
        r = c.execute("SELECT * FROM feedback WHERE id=?", (fid,)).fetchone()
    return _row(r)


def known_issues() -> dict:
    """{test id: {"n": open feedback, "kinds": [...], "last": short text}} for every test with live feedback, so the
    Run and Test cases screens can show it is known (the team sees it before they report it again)."""
    out: dict = {}
    with state.db() as c:
        for r in c.execute("SELECT test, kind, text FROM feedback WHERE test<>'' AND status IN ('open','in_progress') "
                           "ORDER BY id DESC"):
            k = out.setdefault(r["test"], {"n": 0, "kinds": [], "last": r["text"][:140]})
            k["n"] += 1
            if r["kind"] not in k["kinds"]:
                k["kinds"].append(r["kind"])
    return out


def open_count() -> int:
    with state.db() as c:
        return c.execute("SELECT COUNT(*) FROM feedback WHERE status='open'").fetchone()[0]
