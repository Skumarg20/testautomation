"""
Test Studio's browser part (executor._play) against a local fake page -- NOT MargBooks.

Proves: raw-selector targets work in the project's StepRunner, per-step status and screenshots,
failing step is the right one and the rest are skipped, video and trace files are written.
Login, the ready-check and the neutral-state reset are replaced because they belong to MargBooks.
Skipped when no browser can be started.
"""
import pytest

from ui_studio import executor

PAGE = """<!doctype html><meta charset=utf-8><title>fake</title>
<input id="ledger" placeholder="Party"><button id="save" onclick="document.getElementById('msg').textContent='Bill saved'">Save</button>
<div id="msg"></div>"""


@pytest.fixture
def fake_app(tmp_path, monkeypatch):
    from playwright.sync_api import sync_playwright
    html = tmp_path / "fake.html"
    html.write_text(PAGE, encoding="utf-8")
    url = html.as_uri()

    def launch(pw, slow_mo=None, record_video=False):
        last = None
        for kw in ({}, {"channel": "msedge"}, {"channel": "chrome"}):
            try:
                b = pw.chromium.launch(headless=True, **kw)
                break
            except Exception as e:  # noqa: BLE001
                last = e
        else:
            pytest.skip(f"no browser available: {str(last)[:80]}")
        extra = {"record_video_dir": str(tmp_path / "vid")} if record_video else {}
        return b, b.new_context(viewport={"width": 900, "height": 500}, **extra)

    def login(page):
        from framework.base_page import BasePage
        page.goto(url)
        return BasePage(page)

    from ui import envs
    monkeypatch.setattr(envs, "apply_active", lambda: {})      # keep the settings the test sets
    import framework.auth as auth
    import framework.browser as browser
    import framework.screens_check as sc
    monkeypatch.setattr(browser, "launch", launch)
    monkeypatch.setattr(auth, "login", login)
    monkeypatch.setattr(auth, "app_ready", lambda page, t=0: True)
    monkeypatch.setattr(sc, "ensure_neutral", lambda bp, verbose=False: True)
    from config.settings import settings
    monkeypatch.setattr(settings, "ALLOW_DESTRUCTIVE", True, raising=False)
    return tmp_path


def _case(cid, steps, destructive=False):
    return {"id": cid, "name": cid, "steps": steps, "destructive": destructive}


def test_play_passes_fails_and_writes_artifacts(fake_app):
    events = []
    ok = [{"action": "note", "value": "Log in"},
          {"action": "fill", "target": "#ledger", "value": "Ajay"},
          {"action": "click", "target": "#save"},
          {"action": "assert_text", "value": "Bill saved"}]
    bad = ok[:3] + [{"action": "assert_text", "value": "Never shown"}, {"action": "sleep", "value": "0"}]
    out = fake_app / "run"
    res = executor._play([_case("A", ok), _case("B", bad)],
                         {"dir": str(out), "video": True, "shots": True, "trace": True},
                         lambda ci, si, st, secs, shot: events.append((ci, si, st)), lambda m: None)
    assert [r["outcome"] for r in res] == ["passed", "failed"]
    assert res[1]["failed_step"] == 3 and "Never shown" in res[1]["error"]
    assert (0, 3, "ok") in events and (1, 3, "bad") in events and (1, 4, "skip") in events
    assert len(res[0]["shots"]) == 4 and all((out / s).exists() for s in res[0]["shots"])
    assert (out / "B_FAIL.png").exists() and (out / "trace.zip").exists()
    if executor.ffmpeg_ready():
        assert (out / "run.webm").exists()


def test_play_skips_a_write_test_when_writes_are_off(fake_app, monkeypatch):
    from config.settings import settings
    monkeypatch.setattr(settings, "ALLOW_DESTRUCTIVE", False, raising=False)
    res = executor._play([_case("W", [{"action": "note", "value": "x"}], destructive=True)],
                         {"dir": str(fake_app / "r2"), "video": False, "shots": False, "trace": False},
                         lambda *a: None, lambda m: None)
    assert res[0]["outcome"] == "skipped" and "Allow writes" in res[0]["error"]
