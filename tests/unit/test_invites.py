"""One-time "set your password" links: an admin adds a person or resets a password and sends the link."""
import time

import pytest

from ui_studio import accounts, state
from tests.unit.test_studio_server_mode import _call, _client, srv  # noqa: F401  (fixture)


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(state, "DB", tmp_path / "studio.db")
    monkeypatch.setattr(state, "SETTINGS", tmp_path / "s.json")
    accounts._fails.clear()


def test_link_sets_the_password_once_and_old_links_stop():
    accounts.create_user("asha@qa.test", "", "qa", "Asha")                 # no password: she sets it
    first = accounts.create_invite("asha@qa.test")
    second = accounts.create_invite("asha@qa.test")                         # a new link replaces the old one
    assert accounts.invite_user(first) is None and accounts.invite_user(second) == "asha@qa.test"
    assert "asha@qa.test" in accounts.pending_invites()
    with pytest.raises(accounts.AuthError):
        accounts.use_invite(second, "short")
    accounts.use_invite(second, "MyOwnPass#1")
    accounts.login("asha@qa.test", "MyOwnPass#1")
    assert accounts.invite_user(second) is None and "asha@qa.test" not in accounts.pending_invites()
    with pytest.raises(accounts.AuthError):
        accounts.use_invite(second, "AnotherPass#2")                        # used: works once


def test_expired_link_does_not_work(monkeypatch):
    accounts.create_user("ravi@qa.test", "Temp#Pass12")
    tok = accounts.create_invite("ravi@qa.test", hours=1)
    real = time.time
    monkeypatch.setattr(time, "time", lambda: real() + 2 * 3600)
    assert accounts.invite_user(tok) is None
    with pytest.raises(accounts.AuthError):
        accounts.use_invite(tok, "NewPass#123")


def test_admin_adds_a_person_and_sends_the_link(srv):  # noqa: F811
    base, _ = srv
    boss = _client()
    _call(boss, base, "/api/auth/login", {"username": "boss@qa.test", "password": "password123"})
    code, r, _ = _call(boss, base, "/api/users", {"create": True, "username": "Neha@QA.test", "name": "Neha",
                                                  "role": "qa"})
    assert code == 200 and r["invite_url"].startswith(base + "/#setpw=") and r["login_url"] == base + "/"
    assert r["user"]["username"] == "neha@qa.test" and r["password_set"] is False
    users = _call(boss, base, "/api/users")[1]["users"]
    assert next(u for u in users if u["username"] == "neha@qa.test")["invite_open"] is True
    token = r["invite_url"].split("#setpw=")[1]
    anon = _client()                                                         # Neha, not logged in
    assert _call(anon, base, "/api/auth/invite", {"token": token})[1]["email"] == "neha@qa.test"
    assert _call(anon, base, "/api/auth/setpw", {"token": token, "password": "NehaPass#9"})[0] == 200
    assert _call(anon, base, "/api/auth/login", {"username": "neha@qa.test", "password": "NehaPass#9"})[0] == 200
    assert _call(_client(), base, "/api/auth/setpw", {"token": token, "password": "Again#Pass1"})[0] == 400
    code, again, _ = _call(boss, base, "/api/users", {"username": "neha@qa.test", "invite": True})   # Reset
    assert code == 200 and again["invite_url"] != r["invite_url"]
    qa = _client()
    _call(qa, base, "/api/auth/login", {"username": "qa1@qa.test", "password": "password123"})
    assert _call(qa, base, "/api/users", {"username": "neha@qa.test", "invite": True})[0] == 403        # admin only
