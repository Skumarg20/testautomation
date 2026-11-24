"""Pre-flight check before going live: each check reports PASS / WARN / FAIL, and a FAIL makes the exit code 1."""
from ui_studio import preflight


def test_every_check_reports_and_a_crash_is_a_fail(monkeypatch, capsys):
    monkeypatch.setattr(preflight, "browser", lambda: ("PASS", "Chromium starts"))          # no real browser here
    monkeypatch.setattr(preflight, "CHECKS", preflight.CHECKS + [("Broken", lambda: 1 / 0)])
    res = preflight.run()
    assert {r["check"] for r in res} >= {"Python", "Libraries", "Admin account", "Database", "Broken"}
    assert all(r["status"] in ("PASS", "WARN", "FAIL") for r in res)
    broken = next(r for r in res if r["check"] == "Broken")
    assert broken["status"] == "FAIL" and "ZeroDivisionError" in broken["detail"]
    assert preflight.main([]) == 1 and "NOT READY" in capsys.readouterr().out


def test_ready_when_nothing_fails(monkeypatch, capsys):
    monkeypatch.setattr(preflight, "CHECKS", [("A", lambda: ("PASS", "ok")), ("B", lambda: ("WARN", "soon"))])
    assert preflight.main([]) == 0 and "READY: 0 fail, 1 warning" in capsys.readouterr().out
