"""
Test Studio accounts (server mode: one Studio for the whole QA team, opened in the browser).

* Studio users: username + password (PBKDF2-SHA256, 260k rounds, per-user salt), role "admin" or "qa".
* Sessions: random token in an HttpOnly cookie; only its SHA-256 is stored; 12 h sliding expiry.
* Each user's own MargBooks login (user id + password) for the runs they start. The password is encrypted at rest:
  Windows DPAPI (bound to the Windows account the server runs as), or Fernet from the `cryptography` package
  with the key in STUDIO_SECRET_KEY on other systems. It never goes back to the browser.
* Brute force: 5 wrong passwords lock the username for 5 minutes.

Admin from the command line (the first admin is made this way):
    python -m ui_studio.accounts add <email> --admin [--name "Full Name"]   # asks for the password
    python -m ui_studio.accounts add <email>                                # a QA user
    python -m ui_studio.accounts reset <email>
    python -m ui_studio.accounts role <email> admin|qa
    python -m ui_studio.accounts name <email> "Full Name"
    python -m ui_studio.accounts disable <email> | enable <email>
    python -m ui_studio.accounts list
    python -m ui_studio.accounts email <old login> <new email>                 # change a login e-mail

  From a script (service setup, remote shell): add --password-stdin and pipe the password in (one line):
    echo MyPassw0rd| python -m ui_studio.accounts add ops@example.com --admin --password-stdin
  Spaces and tabs at the end of the piped line are dropped (cmd.exe's "echo pw | ..." sends "pw ").
  Without a console (stdin is not a terminal) the password is read from stdin too, never from a hidden prompt.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
import re
import secrets
import sys
import threading
import time
from contextlib import contextmanager

from ui_studio import state

ROUNDS = 260_000
SESSION_HOURS = 12
MAX_FAILS, LOCK_SECONDS = 5, 300
ROLES = ("admin", "qa")
_USERNAME = re.compile(r"^[a-z0-9][a-z0-9._-]{1,39}$")      # accounts made before logins were e-mail addresses
# A person logs in with their e-mail address (the Studio "username" is that address, lower case).
EMAIL = re.compile(r"^[a-z0-9][a-z0-9._%+-]{0,63}@[a-z0-9-]+(\.[a-z0-9-]+)+$")
_fails: dict[str, list[float]] = {}
_fail_lock = threading.Lock()


class AuthError(ValueError):
    pass


# ------------------------------------------------------------------ storage

def _tables(con):
    con.executescript("""
    CREATE TABLE IF NOT EXISTS users(username TEXT PRIMARY KEY, name TEXT, role TEXT, pw TEXT, disabled INT DEFAULT 0,
        mb_user TEXT DEFAULT '', mb_secret TEXT DEFAULT '', created REAL, last_login REAL);
    CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY, username TEXT, expires REAL, created REAL);
    """)


state.add_schema(_tables)     # created once per database file, not on every query


@contextmanager
def _Con():
    with state.db() as con:
        yield con


# ------------------------------------------------------------------ passwords

def hash_password(pw: str, rounds: int = ROUNDS) -> str:
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", pw.encode("utf-8"), salt, rounds)
    return f"pbkdf2_sha256${rounds}${base64.b64encode(salt).decode()}${base64.b64encode(dk).decode()}"


def check_password(pw: str, stored: str) -> bool:
    try:
        algo, rounds, salt, dk = stored.split("$")
        if algo != "pbkdf2_sha256":
            return False
        got = hashlib.pbkdf2_hmac("sha256", pw.encode("utf-8"), base64.b64decode(salt), int(rounds))
        return hmac.compare_digest(got, base64.b64decode(dk))
    except Exception:  # noqa: BLE001
        return False


def _text(v, what: str) -> str:
    """A value from a JSON body: must be text (or missing)."""
    if v is None:
        return ""
    if not isinstance(v, str):
        raise AuthError(f"{what} must be text.")
    return v


def _uname(username) -> str:
    return _text(username, "Username").strip().lower()


def _check_strength(pw: str):
    if not isinstance(pw, str) or len(pw) < 8:
        raise AuthError("Password must have at least 8 characters.")


# ------------------------------------------------------------------ secrets at rest (MargBooks passwords)

def _dpapi(data: bytes, protect: bool) -> bytes:
    import ctypes
    from ctypes import wintypes

    class BLOB(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

    buf = ctypes.create_string_buffer(data, len(data))
    src, out = BLOB(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char))), BLOB()
    fn = ctypes.windll.crypt32.CryptProtectData if protect else ctypes.windll.crypt32.CryptUnprotectData
    ok = fn(ctypes.byref(src), None, None, None, None, 0x1, ctypes.byref(out))    # 0x1: no UI
    if not ok:
        raise OSError("Windows could not encrypt/decrypt the saved MargBooks password (DPAPI).")
    try:
        return ctypes.string_at(out.pbData, out.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(out.pbData)


def _fernet():
    key = os.environ.get("STUDIO_SECRET_KEY", "").strip()
    if not key:
        raise OSError("Set STUDIO_SECRET_KEY (a Fernet key) to store MargBooks passwords on this system.")
    from cryptography.fernet import Fernet   # only needed off Windows
    return Fernet(key.encode())


def seal(text: str) -> str:
    if not text:
        return ""
    if os.name == "nt":
        return "dpapi:" + base64.b64encode(_dpapi(text.encode("utf-8"), True)).decode()
    return "fernet:" + _fernet().encrypt(text.encode("utf-8")).decode()


def unseal(blob: str) -> str:
    if not blob:
        return ""
    kind, _, body = blob.partition(":")
    if kind == "dpapi":
        return _dpapi(base64.b64decode(body), False).decode("utf-8")
    if kind == "fernet":
        return _fernet().decrypt(body.encode()).decode("utf-8")
    raise OSError("Unknown secret format")


# ------------------------------------------------------------------ users

def _public(r) -> dict:
    return {"username": r["username"], "name": r["name"] or r["username"], "role": r["role"],
            "disabled": bool(r["disabled"]), "mb_user": r["mb_user"] or "", "has_mb_password": bool(r["mb_secret"]),
            "last_login": r["last_login"]}


def count_users() -> int:
    with _Con() as c:
        return c.execute("SELECT COUNT(*) n FROM users").fetchone()["n"]


def list_users() -> list[dict]:
    with _Con() as c:
        return [_public(r) for r in c.execute("SELECT * FROM users ORDER BY username")]


def get_user(username: str) -> dict | None:
    username = username.strip().lower() if isinstance(username, str) else ""
    with _Con() as c:
        r = c.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
    return _public(r) if r else None


def create_user(username: str, password: str, role: str = "qa", name: str = "") -> dict:
    username = _uname(username)
    name = _text(name, "Name")
    if not EMAIL.match(username) or len(username) > 120:
        raise AuthError("Use the person's e-mail address (for example name@margerp.net): it is their login.")
    if not isinstance(role, str) or role not in ROLES:
        raise AuthError(f"Role must be one of {ROLES}.")
    if password in (None, ""):          # set later by the person from their "set your password" link
        password = secrets.token_urlsafe(24)
    _check_strength(password)
    with _Con() as c:
        if c.execute("SELECT 1 FROM users WHERE username=?", (username,)).fetchone():
            raise AuthError(f"User {username!r} already exists.")
        c.execute("INSERT INTO users(username,name,role,pw,disabled,created) VALUES(?,?,?,?,0,?)",
                  (username, (name or username).strip()[:80], role, hash_password(password), time.time()))
    return get_user(username)


def update_user(username: str, *, role: str | None = None, name: str | None = None,
                disabled: bool | None = None, password: str | None = None) -> dict:
    username = _uname(username)
    u = get_user(username)
    if not u:
        raise AuthError("No such user.")
    if role is not None and (not isinstance(role, str) or role not in ROLES):
        raise AuthError(f"Role must be one of {ROLES}.")
    if name is not None:
        name = _text(name, "Name")
    if disabled is not None and not isinstance(disabled, (bool, int)):
        raise AuthError("Disabled must be true or false.")
    if password is not None:
        _check_strength(password)
    # Only an ENABLED admin is an admin the Studio still has: a disabled admin is never "the last admin".
    active_admin = u["role"] == "admin" and not u["disabled"]
    with _Con() as c:
        if role is not None:
            if active_admin and role != "admin" and _admins(c) <= 1:
                raise AuthError("The last admin cannot lose the admin role.")
            c.execute("UPDATE users SET role=? WHERE username=?", (role, username))
        if name is not None:
            c.execute("UPDATE users SET name=? WHERE username=?", (name.strip()[:80] or username, username))
        if disabled is not None:
            if disabled and active_admin and _admins(c) <= 1:
                raise AuthError("The last admin cannot be disabled.")
            c.execute("UPDATE users SET disabled=? WHERE username=?", (1 if disabled else 0, username))
            if disabled:
                c.execute("DELETE FROM sessions WHERE username=?", (username,))
        if password is not None:
            _check_strength(password)
            c.execute("UPDATE users SET pw=? WHERE username=?", (hash_password(password), username))
            c.execute("DELETE FROM sessions WHERE username=?", (username,))
    return get_user(username)


def change_email(username: str, new_email: str) -> dict:
    """Give an account a new login e-mail (also an old username-style account). Their sessions end; what they did
    (runs, feedback, activity) moves with them."""
    old, new = _uname(username), _uname(new_email)
    if not EMAIL.match(new) or len(new) > 120:
        raise AuthError("Use a valid e-mail address (for example name@margerp.net).")
    with _Con() as c:
        if not c.execute("SELECT 1 FROM users WHERE username=?", (old,)).fetchone():
            raise AuthError("No such user.")
        if old != new and c.execute("SELECT 1 FROM users WHERE username=?", (new,)).fetchone():
            raise AuthError(f"{new} already has an account.")
        c.execute("UPDATE users SET username=? WHERE username=?", (new, old))
        c.execute("DELETE FROM sessions WHERE username=?", (old,))
        for table, col in (("runs", "run_by"), ("feedback", "by_user"), ("activity", "who")):
            try:
                c.execute(f"UPDATE {table} SET {col}=? WHERE {col}=?", (new, old))
            except Exception:  # noqa: BLE001  (a table this database does not have yet)
                pass
    return get_user(new)


# ------------------------------------------------------------------ "set your password" links (invites, resets)
INVITE_HOURS = 72


def _invite_table(c):
    c.execute("CREATE TABLE IF NOT EXISTS invites(token TEXT PRIMARY KEY, username TEXT, expires REAL, created REAL)")


def create_invite(username: str, hours: float = INVITE_HOURS) -> str:
    """A one-time link token for this person to set their own password (a new account, or a forgotten password).
    Only its SHA-256 is stored; an older open link of the same person stops working."""
    username = _uname(username)
    if not get_user(username):
        raise AuthError("No such user.")
    token = secrets.token_urlsafe(24)
    with _Con() as c:
        _invite_table(c)
        c.execute("DELETE FROM invites WHERE username=?", (username,))
        c.execute("INSERT INTO invites VALUES(?,?,?,?)", (_th(token), username, time.time() + hours * 3600, time.time()))
    return token


def invite_user(token: str) -> str | None:
    """The person an open link is for (None for an unknown, used or expired link)."""
    if not isinstance(token, str) or not token:
        return None
    with _Con() as c:
        _invite_table(c)
        r = c.execute("SELECT username, expires FROM invites WHERE token=?", (_th(token),)).fetchone()
    return r["username"] if r and r["expires"] > time.time() else None


def use_invite(token: str, password: str) -> dict:
    """Set the password from a link. The link works once; the person's other sessions end."""
    username = invite_user(token)
    if not username:
        raise AuthError("This link is not valid any more (it was used or it expired). Ask your Studio admin for a "
                        "new one.")
    _check_strength(password)
    with _Con() as c:
        c.execute("UPDATE users SET pw=?, disabled=0 WHERE username=?", (hash_password(password), username))
        c.execute("DELETE FROM sessions WHERE username=?", (username,))
        c.execute("DELETE FROM invites WHERE username=?", (username,))
    return get_user(username)


def pending_invites() -> dict[str, float]:
    """username -> expiry of the open "set your password" link."""
    with _Con() as c:
        _invite_table(c)
        return {r["username"]: r["expires"] for r in c.execute("SELECT username, expires FROM invites")
                if r["expires"] > time.time()}


def _admins(c) -> int:
    return c.execute("SELECT COUNT(*) n FROM users WHERE role='admin' AND disabled=0").fetchone()["n"]


def change_own_password(username: str, old: str, new: str):
    """Wrong current passwords count toward the same lockout as wrong logins (5 in 5 minutes)."""
    username = _uname(username)
    if _locked(username):
        raise AuthError("Too many wrong passwords. Try again in a few minutes.")
    with _Con() as c:
        r = c.execute("SELECT pw FROM users WHERE username=?", (username,)).fetchone()
    if not r or not check_password(old if isinstance(old, str) else "", r["pw"]):
        _fail(username)
        raise AuthError("The current password is not right.")
    with _fail_lock:
        _fails.pop(username, None)
    update_user(username, password=new)


# ------------------------------------------------------------------ login / sessions

def _locked(username: str) -> bool:
    now = time.time()
    with _fail_lock:
        f = [t for t in _fails.get(username, []) if now - t < LOCK_SECONDS]
        _fails[username] = f
        return len(f) >= MAX_FAILS


def _fail(username: str):
    with _fail_lock:
        _fails.setdefault(username, []).append(time.time())


def login(username: str, password: str) -> tuple[str, dict]:
    """(session token, user). One message for every kind of failure, so a username cannot be probed.
    The password hash is computed for an unknown username too, so the reply time does not tell either."""
    username = username.strip().lower() if isinstance(username, str) else ""
    password = password if isinstance(password, str) else ""
    if _locked(username):
        raise AuthError("Too many wrong passwords. Try again in a few minutes.")
    with _Con() as c:
        r = c.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone() if username else None
    ok = check_password(password, r["pw"] if r else _dummy_hash())
    if not r or r["disabled"] or not ok:
        _fail(username)
        raise AuthError("Wrong username or password.")
    with _fail_lock:
        _fails.pop(username, None)
    token = secrets.token_urlsafe(32)
    now = time.time()
    with _Con() as c:
        c.execute("DELETE FROM sessions WHERE expires<?", (now,))
        c.execute("INSERT INTO sessions VALUES(?,?,?,?)", (_th(token), username, now + SESSION_HOURS * 3600, now))
        c.execute("UPDATE users SET last_login=? WHERE username=?", (now, username))
    return token, _public(r)


_DUMMY: list[str] = []


def _dummy_hash() -> str:
    """A hash no password matches, as costly to check as a real one (an unknown username takes as long)."""
    if not _DUMMY:
        _DUMMY.append(hash_password(secrets.token_urlsafe(16)))
    return _DUMMY[0]


def _th(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def session_user(token: str | None, info: dict | None = None) -> dict | None:
    """The user of a session. info["slid"] = True when the expiry moved on (the server re-sends the cookie)."""
    if not token:
        return None
    now = time.time()
    with _Con() as c:
        s = c.execute("SELECT * FROM sessions WHERE token=?", (_th(token),)).fetchone()
        if not s or s["expires"] < now:
            return None
        r = c.execute("SELECT * FROM users WHERE username=?", (s["username"],)).fetchone()
        if not r or r["disabled"]:
            return None
        if s["expires"] - now < SESSION_HOURS * 3600 - 600:          # slide, at most every 10 minutes
            c.execute("UPDATE sessions SET expires=? WHERE token=?", (now + SESSION_HOURS * 3600, _th(token)))
            if info is not None:
                info["slid"] = True
    return _public(r)


def logout(token: str | None):
    if token:
        with _Con() as c:
            c.execute("DELETE FROM sessions WHERE token=?", (_th(token),))


# ------------------------------------------------------------------ the user's own MargBooks login

def set_margbooks_login(username: str, mb_user: str, mb_password: str | None):
    """mb_password None/'' keeps the saved one (the form never shows it back)."""
    mb_user = (mb_user or "").strip()
    if not mb_user:
        raise AuthError("MargBooks user id is required.")
    with _Con() as c:
        if mb_password:
            c.execute("UPDATE users SET mb_user=?, mb_secret=? WHERE username=?", (mb_user, seal(mb_password), username))
        else:
            c.execute("UPDATE users SET mb_user=? WHERE username=?", (mb_user, username))


def margbooks_login(username: str) -> tuple[str, str] | None:
    with _Con() as c:
        r = c.execute("SELECT mb_user, mb_secret FROM users WHERE username=?", (username,)).fetchone()
    if not r or not r["mb_user"] or not r["mb_secret"]:
        return None
    return r["mb_user"], unseal(r["mb_secret"])


# ------------------------------------------------------------------ CLI

def _console_stdin() -> bool:
    """True only for a real interactive console. On Windows isatty() is also True for NUL (a service, a scheduled
    task, `< /dev/null`), where a hidden prompt would wait for ever: ask the console itself."""
    if sys.stdin is None:
        return False
    try:
        if not sys.stdin.isatty():
            return False
    except (ValueError, OSError):
        return False
    if os.name != "nt":
        return True
    try:
        import ctypes
        import msvcrt
        from ctypes import wintypes
        h = msvcrt.get_osfhandle(sys.stdin.fileno())
        mode = wintypes.DWORD()
        return bool(ctypes.windll.kernel32.GetConsoleMode(wintypes.HANDLE(h), ctypes.byref(mode)))
    except Exception:  # noqa: BLE001
        return False


def _read_password(name: str, from_stdin: bool) -> str | None:
    """--password-stdin, or no console (stdin is not a terminal): one line from stdin. Else a hidden prompt, twice."""
    import getpass
    if from_stdin or not _console_stdin():
        line = sys.stdin.readline() if sys.stdin is not None else ""
        # trailing blanks too: cmd.exe "echo pw | ..." sends "pw " (the space before the pipe), and the admin
        # could then not log in with the password they typed
        return line.rstrip(" \t\r\n")
    pw = getpass.getpass(f"Password for {name}: ")
    if pw != getpass.getpass("Again: "):
        print("The two passwords differ.")
        return None
    return pw


def _opt(argv: list[str], flag: str) -> str:
    if flag in argv:
        k = argv.index(flag)
        if k + 1 < len(argv):
            return argv[k + 1]
    return ""


def _cli(argv: list[str]) -> int:
    if not argv or argv[0] not in ("add", "reset", "disable", "enable", "list", "role", "name", "email"):
        print(__doc__)
        return 2
    cmd = argv[0]
    if cmd == "list":
        for u in list_users():
            print(f"{u['username']:<20} {u['role']:<6} {'DISABLED' if u['disabled'] else 'active':<8} "
                  f"margbooks={u['mb_user'] or '-'}  name={u['name']}")
        return 0
    if len(argv) < 2 or argv[1].startswith("--"):
        print("e-mail address (login) missing")
        return 2
    name = argv[1]
    try:
        if cmd in ("add", "reset"):
            if cmd == "reset" and not get_user(name):        # before asking for a password
                raise AuthError("No such user.")
            pw = _read_password(name, "--password-stdin" in argv)
            if pw is None:
                return 1
            if cmd == "add":
                create_user(name, pw, "admin" if "--admin" in argv else "qa", _opt(argv, "--name"))
            else:
                update_user(name, password=pw)
        elif cmd in ("role", "name"):
            if len(argv) < 3:
                print("admin or qa missing" if cmd == "role" else "the name is missing")
                return 2
            update_user(name, **{cmd: argv[2]})
        elif cmd == "email":
            if len(argv) < 3:
                print("the new e-mail address is missing")
                return 2
            change_email(name, argv[2])
        else:
            update_user(name, disabled=(cmd == "disable"))
    except AuthError as e:
        print(e)
        return 1
    print("done")
    return 0


if __name__ == "__main__":
    sys.exit(_cli(sys.argv[1:]))
